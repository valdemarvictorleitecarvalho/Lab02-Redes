# -*- coding: utf-8 -*-

import csv
import json
import threading
import time
from argparse import ArgumentParser

import requests
from flask import Flask, jsonify, request

class Router:
    """
    Representa um roteador que executa o algoritmo de Vetor de Distância.
    """

    def __init__(self, my_address, neighbors, my_network, update_interval=1):
        """
        Inicializa o roteador.

        :param my_address: O endereço (ip:porta) deste roteador.
        :param neighbors: Um dicionário contendo os vizinhos diretos e o custo do link.
                          Ex: {'127.0.0.1:5001': 5, '127.0.0.1:5002': 10}
        :param my_network: A rede que este roteador administra diretamente.
                           Ex: '10.0.1.0/24'
        :param update_interval: O intervalo em segundos para enviar atualizações, o tempo que o roteador espera 
                                antes de enviar atualizações para os vizinhos.        """
        self.my_address = my_address
        self.neighbors = neighbors
        self.my_network = my_network
        self.update_interval = update_interval

        self.routing_table = {}

        self.routing_table[self.my_network] = {
            'cost': 0, 
            'next_hop': self.my_network
        }

        for neighbor_addr, cost in self.neighbors.items():
            self.routing_table[neighbor_addr] = {
                'cost': cost,
                'next_hop': neighbor_addr
            }

        print("Tabela de roteamento inicial:")
        print(json.dumps(self.routing_table, indent=4))

        # Inicia o processo de atualização periódica em uma thread separada
        self._start_periodic_updates()

    def _start_periodic_updates(self):
        """Inicia uma thread para enviar atualizações periodicamente."""
        thread = threading.Thread(target=self._periodic_update_loop)
        thread.daemon = True
        thread.start()

    def _periodic_update_loop(self):
        """Loop que envia atualizações de roteamento em intervalos regulares."""
        while True:
            time.sleep(self.update_interval)
            print(f"[{time.ctime()}] Enviando atualizações periódicas para os vizinhos...")
            try:
                self.send_updates_to_neighbors()
            except Exception as e:
                print(f"Erro durante a atualização periódica: {e}")

    def ip_to_int(self, ip_prefix):
        """Converte uma string de endereço IP em um número inteiro de 32 bits."""
        ip = ip_prefix.split('/')[0]
        parts = list(map(int, ip.split('.')))
        return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
    
    def summarize(self, table):
        """Agrega redes adjacentes com o mesmo next_hop."""
        if not table: return {}
        
        by_nh = {}
        final_table = {}

        for net, info in table.items():
            if ':' in net or net == self.my_network:
                final_table[net] = info
                continue
            
            nh = info['next_hop']
            if nh not in by_nh: by_nh[nh] = []
            by_nh[nh].append({'net': net, 'cost': info['cost']})
        
        for nh, routes in by_nh.items():
            if len(routes) < 2:
                for r in routes: final_table[r['net']] = {'cost': r['cost'], 'next_hop': nh}
                continue
            
            routes.sort(key=lambda x: self.ip_to_int(x['net']))
            
            i = 0
            while i < len(routes):
                r1 = routes[i]
                if i + 1 < len(routes):
                    r2 = routes[i+1]
                    p1 = int(r1['net'].split('/')[1])
                    p2 = int(r2['net'].split('/')[1])
                    int1 = self.ip_to_int(r1['net'])
                    int2 = self.ip_to_int(r2['net'])

                    bloco_size = 2**(32 - p1)
                    if p1 == p2 and (int2 - int1) == bloco_size and (int1 // bloco_size) % 2 == 0:
                        new_prefix = p1 - 1 
                        mascara = (0xFFFFFFFF << (32 - new_prefix)) & 0xFFFFFFFF
                        super_net_int = int1 & mascara
                        
                        sn = [str((super_net_int >> i) & 0xFF) for i in (24, 16, 8, 0)]
                        summary_net = ".".join(sn) + f"/{new_prefix}"
                        
                        max_cost = max(r1['cost'], r2['cost'])
                        final_table[summary_net] = {'cost': max_cost, 'next_hop': nh}
                        i += 2
                        continue
                
                final_table[r1['net']] = {'cost': r1['cost'], 'next_hop': nh}
                i += 1
        return final_table

    def send_updates_to_neighbors(self):
        """Envia a tabela sumarizada respeitando o Poison Reverse."""
        tabela_original = self.routing_table.copy()

        for neighbor_address in self.neighbors:
            tabela_para_enviar = {}

            for network, info in tabela_original.items():
                if info['next_hop'] == neighbor_address:
                    tabela_para_enviar[network] = {
                        'cost': 16, 
                        'next_hop': info['next_hop']
                    }
                else:
                    tabela_para_enviar[network] = info

            tabela_sumarizada = self.summarize(tabela_para_enviar)

            payload = {
                "sender_address": self.my_address,
                "routing_table": tabela_sumarizada
            }

            url = f'http://{neighbor_address}/receive_update'
            try:
                print(f"Enviando tabela com Poison Reverse para {neighbor_address}")
                requests.post(url, json=payload, timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"Não foi possível conectar ao vizinho {neighbor_address}. Erro: {e}")

# --- API Endpoints ---
# Instância do Flask e do Roteador (serão inicializadas no main)
app = Flask(__name__)
router_instance = None

@app.route('/routes', methods=['GET'])
def get_routes():
    if router_instance is not None:
        return jsonify({
            "message": "Tabela de Roteamento Atualizada!",
            "vizinhos": router_instance.neighbors,
            "my_network": router_instance.my_network,
            "my_address": router_instance.my_address,
            "update_interval": router_instance.update_interval,
            "routing_table": router_instance.routing_table # Exibe a tabela de roteamento atual
        })
    return jsonify({"error": "Roteador não inicializado"}), 500

@app.route('/receive_update', methods=['POST'])
def receive_update():
    """Endpoint que recebe atualizações de roteamento de um vizinho."""
    if router_instance is None or not request.json:
        return jsonify({"error": "Invalid request"}), 400

    update_data = request.json
    sender_address = update_data.get("sender_address")
    sender_table = update_data.get("routing_table")

    if not sender_address or not isinstance(sender_table, dict):
        return jsonify({"error": "Missing sender_address or routing_table"}), 400
    
    print(f"Recebida atualização de {sender_address}:")
    print(json.dumps(sender_table, indent=4))

    
    link_cost = router_instance.neighbors.get(sender_address)

    if link_cost is None:
        return jsonify({"error": "Sender is not a direct neighbor"}), 400

    for network, info in sender_table.items():
        if network == router_instance.my_network or network == router_instance.my_address:
            continue
        
        if '/' in network:
            ip_rec_int = router_instance.ip_to_int(network)
            mask_rec = int(network.split('/')[1])
            ip_my_int = router_instance.ip_to_int(router_instance.my_network)
            mask_my = int(router_instance.my_network.split('/')[1])

            if mask_rec <= mask_my:
                bit_mask = (0xFFFFFFFF << (32 - mask_rec)) & 0xFFFFFFFF
                if (ip_rec_int & bit_mask) == (ip_my_int & bit_mask):
                    continue

        new_cost = link_cost + info['cost']
        if new_cost > 16:
            new_cost = 16
       
        if network not in router_instance.routing_table:
            if new_cost < 16:
                router_instance.routing_table[network] = {'cost': new_cost, 'next_hop': sender_address}
        else:
            current = router_instance.routing_table[network]
            if new_cost < current['cost'] or current['next_hop'] == sender_address:
                if current['cost'] != new_cost or current['next_hop'] != sender_address:
                    router_instance.routing_table[network] = {'cost': new_cost, 'next_hop': sender_address}

    return jsonify({"status": "success", "message": "Update received"}), 200

if __name__ == '__main__':
    parser = ArgumentParser(description="Simulador de Roteador com Vetor de Distância")
    parser.add_argument('-p', '--port', type=int, default=5000, help="Porta para executar o roteador.")
    parser.add_argument('-f', '--file', type=str, required=True, help="Arquivo CSV de configuração de vizinhos.")
    parser.add_argument('--network', type=str, required=True, help="Rede administrada por este roteador (ex: 10.0.1.0/24).")
    parser.add_argument('--interval', type=int, default=10, help="Intervalo de atualização periódica em segundos.")
    parser.add_argument('--ip', required=True)
    args = parser.parse_args()

    # Leitura do arquivo de configuração de vizinhos
    neighbors_config = {}
    try:
        with open(args.file, mode='r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                neighbors_config[row['vizinho']] = int(row['custo'])
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração '{args.file}' não encontrado.")
        exit(1)
    except (KeyError, ValueError) as e:
        print(f"Erro no formato do arquivo CSV: {e}. Verifique as colunas 'vizinho' e 'custo'.")
        exit(1)

    my_full_address = f"{args.ip}:{args.port}"
    print("--- Iniciando Roteador ---")
    print(f"Endereço: {my_full_address}")
    print(f"Rede Local: {args.network}")
    print(f"Vizinhos Diretos: {neighbors_config}")
    print(f"Intervalo de Atualização: {args.interval}s")
    print("--------------------------")

    router_instance = Router(
        my_address=my_full_address,
        neighbors=neighbors_config,
        my_network=args.network,
        update_interval=args.interval
    )

    # Inicia o servidor Flask
    app.run(host=args.ip, port=args.port, debug=False)

# Comando para inicialização da rede: python roteador.py --ip 150.165.42.<valor> -p 5000 -f scenario_Grupo2/R<valor>.csv --network 10.0.<valor>.0/24