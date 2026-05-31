from socket import socket
import sys

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from flask import Flask, render_template, Response, request
from flask_cors import CORS
import threading
import json
import queue
import threading
import os
import schedule
import logging
import nmap
from utils.colors import Colors
import psutil
import ipaddress
import socket
import argparse
import pymongo


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

scanner = nmap.PortScanner()


@app.route('/')
def index():
    """Serve the main dashboard page"""
    return "hello"

    
def get_network():
    try:
        #Nessa parte abrimos uma conexao temporaria, para pegar o ip da maquina automaticamente
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80))
        my_ip = s.getsockname()[0]
        s.close()

        logger.info(f'Ip da maquina: {my_ip}')

        address_netmask = None

        #Agora pegamos a interface que corresponde ao ip adquirido anteriormente
        for interface, addresses in psutil.net_if_addrs().items():
            for address in addresses:
                if address.family == socket.AF_INET and address.address == my_ip:
                    address_netmask = address.netmask
                    break  
            
            if address_netmask:
                break      
        
        logger.info(f'Netmask da rede: {address_netmask}')
        
        #fazemos o ip da maquina AND ip da rede
        complete_interface = ipaddress.IPv4Interface(f"{my_ip}/{address_netmask}")


        return str(complete_interface.network)
                
    except Exception as e:
        logger.error(f"Erro ao tentar descobrir a rede ativa: {e}")
        return None


def scanner_fn():
    logger.info(f'Iniciando scanner...')

    network = get_network()

    scanner.scan(
        hosts= network,
        arguments='-sT --open'
    )

    print("Hosts encontrados:")

    print(scanner.all_hosts())

    for host in scanner.all_hosts():

        print(f'Host: {host}')

        mac_address = scanner[host]['addresses'].get('mac', None)
        
        if mac_address:
            fabricante = scanner[host]['vendor'].get(mac_address, 'Fabricante Desconhecido')
            print(f'MAC Address: {mac_address}')
            print(f'Fabricante:  {fabricante}')
        else:
            print(f'MAC Address: Não detectado (Faltou executar com sudo?)')


        for protocolo in scanner[host].all_protocols():

            print(f'Protocolo: {protocolo}')

            portas = scanner[host][protocolo].keys()

            for porta in portas:

                servico = scanner[host][protocolo][porta]

                print(f'├──>Porta: {porta}')
                print(f'│   ├──>Estado: {servico["state"]}')
                print(f'│   └──>Serviço: {servico["name"]}')
                    
        print('\n')
    print("Scanner finalizado!")


def check_root_privileges():
    if os.geteuid() != 0:
        logger.error("Este script requer privilégios de root. Por favor, execute em modo de administrador.")
        sys.exit(1)


def scheduler_thread():
    """Thread que executa o scheduler"""
    schedule.every(10).seconds.do(scanner_fn)

    print("Scheduler iniciado, aguardando tarefas...")
    
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Erro na thread do scheduler: {e}", exc_info=True)



def main():
    """Initialize the application and start the scheduler thread."""

    try:
        logger.info("Starting application...")

        check_root_privileges()

        scheduler_worker = threading.Thread(
            target=scheduler_thread,
            args=(),
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
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ('1', 'true', 'yes')

    main()

    # Disable Flask reloader to prevent multiple MQTT client instances
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)