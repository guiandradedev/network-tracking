import sys
import os
import json
import queue
import threading
import socket
import argparse
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from flask import Flask, render_template, Response, request
from flask_cors import CORS
import schedule
import nmap
import psutil
import ipaddress
from pymongo import MongoClient

# Caso exista no seu projeto, mantive o import
try:
    from utils.colors import Colors
except ImportError:
    pass

app = Flask(__name__)
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--interface", type=str)
CORS(app)

# ⚙️ Setup de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

logging.getLogger('werkzeug').setLevel(logging.ERROR)

scanner = nmap.PortScanner()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")
client = MongoClient(MONGO_URI)

db = client['network_scanner']

# ++++++++++++++++++++++++++++++ COMEMTAR ESSAS LINHAS DEPOIS DE RODAR PELA PRIMEIRA VEZ!!!!+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
db.hosts.delete_many({})
db.network_history.delete_many({})
db.device_history.delete_many({})
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Definição das Coleções
hosts_collection = db['hosts']
network_history = db['network_history']
device_history = db['device_history']

# Criação dos Índices de Performance
network_history.create_index("timestamp")
device_history.create_index([("MAC", 1), ("timestamp", -1)])


@app.route('/')
def index():
    """Serve the main dashboard page"""
    all_hosts = list(hosts_collection.find({}, {'_id': 0}))
    return Response(json.dumps(all_hosts), mimetype='application/json')


@app.route('/api/health/database', methods=['GET'])
def health_database():
    """Verifica a conexão com o banco de dados"""
    try:
        client.admin.command('ping')
        return Response(json.dumps({
            "status": "connected",
            "message": "Banco de dados conectado com sucesso"
        }), mimetype='application/json', status=200)
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        return Response(json.dumps({
            "status": "disconnected",
            "message": f"Falha ao conectar ao banco de dados: {str(e)}"
        }), mimetype='application/json', status=503)

@app.route('/api/stats/active-by-time', methods=['GET'])
def active_by_time():
    yesterday = datetime.now() - timedelta(days=1)
    pipeline = [
        {"$match": {"timestamp": {"$gte": yesterday}}},
        {"$group": {
            "_id": {
                "year": {"$year": "$timestamp"},
                "month": {"$month": "$timestamp"},
                "day": {"$dayOfMonth": "$timestamp"},
                "hour": {"$hour": "$timestamp"}
            },
            "avg_active": {"$avg": "$total_active"}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1, "_id.hour": 1}}
    ]
    results = list(network_history.aggregate(pipeline))
    formatted_data = [
        {
            "time": f"{r['_id']['day']:02d}/{r['_id']['month']:02d} {r['_id']['hour']:02d}:00",
            "active_devices": round(r['avg_active'], 1)
        } for r in results
    ]
    return Response(json.dumps(formatted_data), mimetype='application/json')


@app.route('/api/stats/peak-activity', methods=['GET'])
def peak_activity():
    pipeline = [
        {"$sort": {"total_active": -1}},
        {"$limit": 5},
        {"$project": {"_id": 0, "timestamp": 1, "total_active": 1}}
    ]
    results = list(network_history.aggregate(pipeline))
    for r in results:
        r['timestamp'] = r['timestamp'].isoformat()
    return Response(json.dumps(results), mimetype='application/json')


@app.route('/api/stats/growth', methods=['GET'])
def host_growth():
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)
    
    current_hour_avg = network_history.aggregate([
        {"$match": {"timestamp": {"$gte": one_hour_ago, "$lte": now}}},
        {"$group": {"_id": None, "avg": {"$avg": "$total_active"}}}
    ])
    
    previous_hour_avg = network_history.aggregate([
        {"$match": {"timestamp": {"$gte": two_hours_ago, "$lt": one_hour_ago}}},
        {"$group": {"_id": None, "avg": {"$avg": "$total_active"}}}
    ])
    
    curr = list(current_hour_avg)
    prev = list(previous_hour_avg)
    curr_val = curr[0]['avg'] if curr else 0
    prev_val = prev[0]['avg'] if prev else 0
    
    growth = curr_val - prev_val
    percentage = ((growth / prev_val) * 100) if prev_val > 0 else 0
    
    return Response(json.dumps({
        "current_avg": round(curr_val, 1),
        "previous_avg": round(prev_val, 1),
        "growth_absolute": round(growth, 1),
        "growth_percentage": round(percentage, 2)
    }), mimetype='application/json')


@app.route('/api/device/<mac_address>/history', methods=['GET'])
def device_availability(mac_address):
    last_24h = datetime.now() - timedelta(days=1)
    appearances = list(device_history.find(
        {"MAC": mac_address, "timestamp": {"$gte": last_24h}},
        {"_id": 0, "timestamp": 1, "status": 1}
    ).sort("timestamp", 1))
    
    total_scans = network_history.count_documents({"timestamp": {"$gte": last_24h}})
    device_scans = len(appearances)
    frequency_percentage = (device_scans / total_scans * 100) if total_scans > 0 else 0

    for a in appearances:
        a['timestamp'] = a['timestamp'].isoformat()

    return Response(json.dumps({
        "mac_address": mac_address,
        "frequency_percentage": round(frequency_percentage, 2),
        "total_uptime_events": device_scans,
        "timeline": appearances
    }), mimetype='application/json')


def insert_data_to_db(data):
    hosts_collection.update_one(
        {"host": data["host"]},  
        {"$set": data},          
        upsert=True              
    )


def callback(interface, debug=False):
    print("\n" + "="*50)
    print("Executando callback")

    network = ipaddress.IPv4Network(
        f"{interface[0].address}/{interface[0].netmask}",
        strict=False
    )
    host = str(network)
    
    print(f"Host a ser escaneado: {host}")
    
    scanner.scan(hosts=host, arguments='-sn')

    print("\nResultados encontrados neste scan:")

    scan_time = datetime.now()
    active_macs = []
    total_active = 0
    
    current_scan_hosts = []

    for host in scanner.all_hosts():
        current_scan_hosts.append(host)
        
        status = scanner[host].state()
        if status == 'up':
            total_active += 1
            
        mac_address = scanner[host]['addresses'].get('mac', None)
        fabricante = scanner[host]['vendor'].get(mac_address, 'Fabricante Desconhecido') if mac_address else 'Desconhecido'

        if mac_address:
            active_macs.append(mac_address)
            device_history.insert_one({
                "MAC": mac_address,
                "host": host,
                "status": status,
                "timestamp": scan_time
            })

        # Estrutura limpa do dispositivo, sem protocolos ou portas
        host_data = {
            "host": host,
            "status": status,
            "MAC": mac_address,
            "fabricante": fabricante
        }

        insert_data_to_db(host_data)
        
        # Log limpo e direto no console
        print(f"[+] IP: {host_data['host']:<15} | Status: {host_data['status'].upper()} | MAC: {host_data['MAC'] or 'Não identificado'}")
                
    # Marca como 'down' quem não está na lista atual
    hosts_collection.update_many(
        {"host": {"$nin": current_scan_hosts}},
        {"$set": {"status": "down"}}
    )

    network_history.insert_one({
        "timestamp": scan_time,
        "total_active": total_active,
        "active_macs": active_macs
    })

    print(f"\nCallback executado com sucesso! Total ativos: {total_active}")
    print("="*50 + "\n")


def check_root_privileges():
    if os.geteuid() != 0:
        logger.error("Este script requer privilégios de root. Por favor, execute com sudo.")
        sys.exit(1)

def scheduler_thread(interface, debug=False):
    schedule.every(15).seconds.do(callback, interface, debug)
    print("Scheduler iniciado, aguardando tarefas...")
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Erro na thread do scheduler: {e}", exc_info=True)

def choose_network_interface():
    logger.info("Escolha a interface da rede a ser analisada")
    logger.info("Escreva a interface")
    interfaces = []
    for interface, addrs in psutil.net_if_addrs().items():
        interfaces.append(interface)
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                mask = addr.netmask
                network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                print(f"[{interface}]: {ip}, {network}")

    choosen_interface = input("")
    if choosen_interface.lower() not in interfaces:
        raise ValueError(f"Interface '{choosen_interface}' não encontrada.")
    return psutil.net_if_addrs().get(choosen_interface)

def main():
    try:
        logger.info("Starting application...")
        check_root_privileges()
        args = parser.parse_args()
        if not args.interface:
            interface = choose_network_interface()
        else:
            interface = psutil.net_if_addrs().get(args.interface)
            if not interface:
                logger.error(f"Interface '{args.interface}' não encontrada.")
                sys.exit(1)

        scheduler_worker = threading.Thread(
            target=scheduler_thread,
            args=(interface, True),
            daemon=True,
            name="SchedulerWorker"
        )
        scheduler_worker.start()
        
    except Exception as e:
        logger.error(f"Erro durante a inicialização: {e}", exc_info=True)
        raise
    except ValueError as ve:
        logger.error(f"{ve}")
        sys.exit(1)
    finally:
        logger.info("Inicialização da aplicação completa.")

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'True').lower() in ('1', 'true', 'yes')
    main()
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)