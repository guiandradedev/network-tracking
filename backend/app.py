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

def scanner_fn():
    print("Iniciando scanner...")
    scanner.scan(
        hosts='192.168.1.0/24',
        arguments='-sn'
    )

    print("Hosts encontrados:")

    print(scanner.all_hosts())

    for host in scanner.all_hosts():

        print(f'Host: {host}')
        print(f'Status: {scanner[host].state()}')

        for protocolo in scanner[host].all_protocols():

            print(f'\nProtocolo: {protocolo}')

            portas = scanner[host][protocolo].keys()

            for porta in portas:

                servico = scanner[host][protocolo][porta]

                print(
                    f'Porta: {porta} | '
                    f'Estado: {servico["state"]} | '
                    f'Serviço: {servico["name"]}'
                    )
    print("Scanner finalizado!")

def callback(interface, debug=False):
    print("Executando callback...")
    print(interface)

    host = str(interface[0].address) + '/' + str(interface[0].netmask)
    
    print(f"Host a ser escaneado: {host}")
    scanner.scan(
        hosts=host,
        arguments='-sS -sV'
    )

    print("Hosts encontrados na callback:")

    for host in scanner.all_hosts():

        print(f'\nHost: {host}')
        print(f'Status: {scanner[host].state()}')

        for proto in scanner[host].all_protocols():

            print(f'\nProtocolo: {proto}')

            portas = scanner[host][proto].keys()

            for porta in portas:

                dados = scanner[host][proto][porta]

                print(
                    f'Porta: {porta}\n'
                    f'Estado: {dados.get("state")}\n'
                    f'Serviço: {dados.get("name")}\n'
                    f'Produto: {dados.get("product")}\n'
                    f'Versão: {dados.get("version")}\n'
                    f'Extra: {dados.get("extrainfo")}\n'
                )
                
    print("Callback executado!")


def check_root_privileges():
    if os.geteuid() != 0:
        logger.error("Este script requer privilégios de root. Por favor, execute com sudo.")
        sys.exit(1)


def scheduler_thread(interface, debug=False):
    """Thread que executa o scheduler"""
    schedule.every(2).seconds.do(callback, interface, debug)
    #schedule.every(2).minutes.do(remove_expired_uploads)

    print("Scheduler iniciado, aguardando tarefas...")
    
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Erro na thread do scheduler: {e}", exc_info=True)


def choose_network_interface():
    logger.info("Escolha a interface da rede a ser analisada")
    logger.info("Escreva a interface")
    # logger.info("Escreva a interface ou o endereço de rede no formato xxx.xxx.xxx.xxx/xx")
    interfaces = []
    
    for interface, addrs in psutil.net_if_addrs().items():
        interfaces.append(interface)
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                mask = addr.netmask

                network = ipaddress.IPv4Network(
                    f"{ip}/{mask}",
                    strict=False
                )

                print(f"[{interface}]: {ip}, {network}")

    choosen_interface = input("")
    if choosen_interface.lower() not in interfaces:
        raise ValueError(f"Interface '{choosen_interface}' não encontrada.")

    return psutil.net_if_addrs().get(choosen_interface)


def main():
    """Initialize the application and start the scheduler thread."""

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

    # Disable Flask reloader to prevent multiple MQTT client instances
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)