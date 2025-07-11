import socket
import threading
import json
from datetime import datetime
from banco_de_dados import BancoDeDados

class ServidorChat:
    def __init__(self, host='0.0.0.0', port=12345):
        self.servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servidor_socket.bind((host, port))
        self.clientes_online = {}
        self.db = BancoDeDados()
        self.lock = threading.Lock()
        self.DELIMITER = b'\n\n'
        print(f"[*] Servidor Final iniciado em {host}:{port}")

    def iniciar(self):
        self.servidor_socket.listen(5)
        while True:
            cliente_socket, addr = self.servidor_socket.accept()
            threading.Thread(target=self.gerir_cliente, args=(cliente_socket,)).start()

    def enviar_mensagem(self, sock, data):
        try:
            sock.sendall(json.dumps(data).encode('utf-8') + self.DELIMITER)
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass

    def broadcast_status_update(self):
        with self.lock:
            todos_utilizadores = self.db.buscar_todos_utilizadores()
            lista_status = {user: ('online' if user in self.clientes_online else 'offline') for user in todos_utilizadores}
            resposta = {'comando': 'lista_utilizadores', 'utilizadores': lista_status}
            for sock in self.clientes_online.values():
                self.enviar_mensagem(sock, resposta)
        print(f"[*] Status de utilizadores atualizado e enviado.")

    def gerir_cliente(self, cliente_socket):
        username_logado = None
        buffer = b""
        try:
            while True:
                dados_recebidos = cliente_socket.recv(4096)
                if not dados_recebidos: break
                buffer += dados_recebidos
                while self.DELIMITER in buffer:
                    mensagem_json, buffer = buffer.split(self.DELIMITER, 1)
                    request = json.loads(mensagem_json.decode('utf-8'))
                    comando = request.get('comando')

                    if comando == 'registar':
                        if self.db.registar_utilizador(request['utilizador'], request['senha']):
                            self.enviar_mensagem(cliente_socket, {'status': 'ok', 'mensagem': 'Registado com sucesso!'})
                        else:
                            self.enviar_mensagem(cliente_socket, {'status': 'erro', 'mensagem': 'Utilizador já existe.'})
                    
                    elif comando == 'login':
                        if self.db.autenticar_utilizador(request['utilizador'], request['senha']):
                            username_logado = request['utilizador']
                            with self.lock:
                                self.clientes_online[username_logado] = cliente_socket
                            
                            self.enviar_mensagem(cliente_socket, {'status': 'ok', 'comando': 'login_sucesso'})
                            print(f"[*] Utilizador '{username_logado}' logado.")
                            self.broadcast_status_update()
                        else:
                            self.enviar_mensagem(cliente_socket, {'status': 'erro', 'mensagem': 'Utilizador ou senha inválidos.'})
                    
                    elif comando == 'enviar_mensagem' and username_logado:
                        self.processar_envio_mensagem(username_logado, request)

                    elif comando == 'buscar_historico' and username_logado:
                        self.enviar_historico(cliente_socket, username_logado, request.get('com_utilizador'))

                    elif comando == 'aviso_leitura' and username_logado:
                        remetente = request.get('remetente')
                        with self.lock:
                            sock_remetente = self.clientes_online.get(remetente)
                        if sock_remetente:
                            self.enviar_mensagem(sock_remetente, {'comando': 'confirmacao_leitura', 'leitor': username_logado})
                    
                    # NOVO: Lógica para reencaminhar o aviso de "digitando"
                    elif comando == 'typing' and username_logado:
                        request['remetente'] = username_logado
                        with self.lock:
                            sock_destinatario = self.clientes_online.get(request.get('destinatario'))
                        if sock_destinatario:
                            self.enviar_mensagem(sock_destinatario, request)


        except (ConnectionResetError, json.JSONDecodeError, OSError):
            pass
        finally:
            if username_logado:
                with self.lock:
                    if username_logado in self.clientes_online:
                        del self.clientes_online[username_logado]
                print(f"[*] Utilizador '{username_logado}' desconectou.")
                self.broadcast_status_update()
            cliente_socket.close()
    
    def processar_envio_mensagem(self, remetente, request):
        destinatario = request.get('destinatario')
        conteudo = request.get('conteudo')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.db.salvar_mensagem(remetente, destinatario, conteudo, timestamp)
        
        resposta = {'comando': 'nova_mensagem', 'remetente': remetente, 'destinatario': destinatario, 'conteudo': conteudo, 'timestamp': timestamp}
        
        with self.lock:
            sock_destinatario = self.clientes_online.get(destinatario)
        if sock_destinatario:
            self.enviar_mensagem(sock_destinatario, resposta)
        else:
            print(f"[*] Mensagem de '{remetente}' para '{destinatario}' (offline) armazenada.")
        
        with self.lock:
            sock_remetente = self.clientes_online.get(remetente)
        if sock_remetente:
            self.enviar_mensagem(sock_remetente, resposta)

    def enviar_historico(self, sock, utilizador_requisitante, outro_utilizador):
        historico = self.db.buscar_historico(utilizador_requisitante, outro_utilizador)
        pacote_historico = {'comando': 'historico_conversa', 'com_utilizador': outro_utilizador, 'mensagens': historico}
        self.enviar_mensagem(sock, pacote_historico)

if __name__ == "__main__":
    ServidorChat().iniciar()
