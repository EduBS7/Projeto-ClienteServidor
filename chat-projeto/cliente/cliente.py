import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime
from queue import Queue

class ChatClienteGUI:
    def __init__(self):
        self.HOST = 'localhost'
        self.PORT = 12345
        self.DELIMITER = b'\n\n'
        self.sock = None
        self.username = None
        self.conectado = False
        self.janela_chat = None
        self.contato_atual = None
        self.queue = Queue()
        self.timer_digitando = None

        self.BG_COLOR = "#2E2E2E"
        self.TEXT_COLOR = "#EAEAEA"
        self.INPUT_BG_COLOR = "#3C3C3C"
        self.BUTTON_COLOR = "#555555"
        self.ONLINE_COLOR = "#2ECC71"
        self.OFFLINE_COLOR = "#95A5A6"
        self.SYSTEM_MSG_COLOR = "#3498DB"

        self.janela_login = tk.Tk()
        self.setup_janela_login()
        self.janela_login.mainloop()

    def setup_janela_login(self):
        self.janela_login.title("Login do Chat")
        self.janela_login.geometry("300x180")
        self.janela_login.configure(bg=self.BG_COLOR)
        self.janela_login.protocol("WM_DELETE_WINDOW", self.fechar_app)

        tk.Label(self.janela_login, text="Utilizador:", bg=self.BG_COLOR, fg=self.TEXT_COLOR).pack(pady=(10, 0))
        self.entry_usuario = tk.Entry(self.janela_login, bg=self.INPUT_BG_COLOR, fg=self.TEXT_COLOR, insertbackground=self.TEXT_COLOR, borderwidth=0)
        self.entry_usuario.pack(pady=5, padx=20, fill=tk.X)
        
        tk.Label(self.janela_login, text="Senha:", bg=self.BG_COLOR, fg=self.TEXT_COLOR).pack(pady=(5, 0))
        self.entry_senha = tk.Entry(self.janela_login, show="*", bg=self.INPUT_BG_COLOR, fg=self.TEXT_COLOR, insertbackground=self.TEXT_COLOR, borderwidth=0)
        self.entry_senha.pack(pady=5, padx=20, fill=tk.X)
        
        frame_botoes = tk.Frame(self.janela_login, bg=self.BG_COLOR)
        frame_botoes.pack(pady=10, fill=tk.X, padx=20)

        tk.Button(frame_botoes, text="Login", command=self.tentar_login, bg=self.BUTTON_COLOR, fg=self.TEXT_COLOR).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        tk.Button(frame_botoes, text="Registar", command=self.tentar_registar, bg=self.BUTTON_COLOR, fg=self.TEXT_COLOR).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))

    def conectar_e_escutar(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.HOST, self.PORT))
            self.conectado = True
            threading.Thread(target=self.escutar_servidor, daemon=True).start()
            self.janela_login.after(100, self.processar_fila_gui)
            return True
        except ConnectionRefusedError:
            messagebox.showerror("Erro", "Não foi possível conectar ao servidor.")
            return False

    def tentar_login(self):
        self.username = self.entry_usuario.get()
        password = self.entry_senha.get()
        if not self.username or not password: return
        if self.conectar_e_escutar():
            self.enviar_requisicao({'comando': 'login', 'utilizador': self.username, 'senha': password})

    def tentar_registar(self):
        username = self.entry_usuario.get()
        password = self.entry_senha.get()
        if not username or not password: return
        if self.conectar_e_escutar():
            self.enviar_requisicao({'comando': 'registar', 'utilizador': username, 'senha': password})

    def enviar_requisicao(self, data):
        if self.sock and self.conectado:
            try:
                self.sock.sendall(json.dumps(data).encode('utf-8') + self.DELIMITER)
            except (ConnectionResetError, BrokenPipeError, OSError):
                self.queue.put({'comando': 'fechar_app'})

    def escutar_servidor(self):
        buffer = b""
        while self.conectado:
            try:
                dados = self.sock.recv(4096)
                if not dados: break
                buffer += dados
                while self.DELIMITER in buffer:
                    mensagem_json, buffer = buffer.split(self.DELIMITER, 1)
                    resposta = json.loads(mensagem_json.decode('utf-8'))
                    self.queue.put(resposta)
            except (ConnectionResetError, json.JSONDecodeError, OSError):
                break
        self.queue.put({'comando': 'fechar_app'})

    def processar_fila_gui(self):
        while not self.queue.empty():
            msg = self.queue.get()
            comando = msg.get('comando')

            if comando == 'fechar_app':
                self.fechar_app()
                return

            if comando == 'login_sucesso':
                self.janela_login.destroy()
                self.iniciar_chat()
            elif comando == 'lista_utilizadores':
                self.atualizar_lista_contatos(msg.get('utilizadores', {}))
            elif comando == 'nova_mensagem':
                self.processar_nova_mensagem(msg)
            elif comando == 'historico_conversa':
                self.carregar_historico(msg['com_utilizador'], msg['mensagens'])
            elif comando == 'confirmacao_leitura':
                if self.contato_atual == msg['leitor']:
                    self.exibir_mensagem_sistema(f"{msg['leitor']} visualizou as mensagens.")
            elif comando == 'typing':
                self.mostrar_status_digitando(msg['remetente'], msg['status'])
            else:
                status = msg.get('status')
                mensagem = msg.get('mensagem')
                if status == 'ok': messagebox.showinfo("Sucesso", mensagem)
                else: messagebox.showerror("Erro", mensagem)
                self.fechar_app()
        
        root = self.janela_chat or self.janela_login
        if self.conectado and root and root.winfo_exists():
            root.after(100, self.processar_fila_gui)

    def iniciar_chat(self):
        self.janela_chat = tk.Tk()
        self.janela_chat.title(f"Chat - Logado como {self.username}")
        self.janela_chat.geometry("700x500")
        self.janela_chat.configure(bg=self.BG_COLOR)
        self.janela_chat.protocol("WM_DELETE_WINDOW", self.fechar_app)

        frame_contatos = tk.Frame(self.janela_chat, bg=self.BG_COLOR, width=180)
        frame_contatos.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        frame_contatos.pack_propagate(False)

        tk.Label(frame_contatos, text="Contatos", bg=self.BG_COLOR, fg=self.TEXT_COLOR, font=("Helvetica", 12, "bold")).pack(pady=5)
        self.lista_contatos = tk.Listbox(self.janela_chat, bg=self.INPUT_BG_COLOR, fg=self.TEXT_COLOR, borderwidth=0, selectbackground="#007ACC", highlightthickness=0)
        self.lista_contatos.pack(in_=frame_contatos, fill=tk.BOTH, expand=True)
        self.lista_contatos.bind('<<ListboxSelect>>', self.selecionar_contato)
        
        frame_chat = tk.Frame(self.janela_chat, bg=self.BG_COLOR)
        frame_chat.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.label_status = tk.Label(frame_chat, text="Selecione um contato", bg=self.BG_COLOR, fg="#AAA", font=("Helvetica", 9))
        self.label_status.pack(fill=tk.X)

        self.area_chat = scrolledtext.ScrolledText(frame_chat, state='disabled', wrap=tk.WORD, bg=self.INPUT_BG_COLOR, fg=self.TEXT_COLOR, borderwidth=0, font=("Helvetica", 10))
        self.area_chat.pack(fill=tk.BOTH, expand=True, pady=5)
        self.area_chat.tag_config('system', foreground=self.SYSTEM_MSG_COLOR, justify='center', font=("Helvetica", 8, "italic"))

        frame_entrada = tk.Frame(frame_chat, bg=self.BG_COLOR)
        frame_entrada.pack(fill=tk.X, pady=(5,0))

        self.entry_msg = tk.Entry(frame_entrada, bg=self.INPUT_BG_COLOR, fg=self.TEXT_COLOR, insertbackground=self.TEXT_COLOR, borderwidth=0, font=("Helvetica", 10))
        self.entry_msg.pack(fill=tk.X, side=tk.LEFT, expand=True, ipady=5)
        self.entry_msg.bind("<Return>", self.enviar_mensagem_evento)
        self.entry_msg.bind("<KeyPress>", self.evento_digitando)

        btn_enviar = tk.Button(frame_entrada, text="Enviar", command=self.enviar_mensagem_evento, bg=self.BUTTON_COLOR, fg=self.TEXT_COLOR, borderwidth=0)
        btn_enviar.pack(side=tk.RIGHT, padx=(5,0), ipady=2)
        
        tk.Button(frame_contatos, text="Sair", command=self.fechar_app, bg=self.BUTTON_COLOR, fg=self.TEXT_COLOR).pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        self.janela_chat.after(100, self.processar_fila_gui)

    def selecionar_contato(self, event=None):
        selecao = self.lista_contatos.curselection()
        if not selecao: return
        
        self.contato_atual = self.lista_contatos.get(selecao[0]).split(' ')[0]
        self.label_status.config(text=f"Conversando com {self.contato_atual}")
        self.enviar_requisicao({'comando': 'buscar_historico', 'com_utilizador': self.contato_atual})

    def carregar_historico(self, com_utilizador, mensagens):
        if self.contato_atual != com_utilizador: return
        self.area_chat.config(state='normal')
        self.area_chat.delete(1.0, tk.END)
        for remetente, conteudo, timestamp in mensagens:
            autor = "Você" if remetente == self.username else remetente
            ts_formatado = datetime.fromisoformat(timestamp).strftime('%H:%M')
            self.area_chat.insert(tk.END, f"[{ts_formatado}] {autor}: {conteudo}\n")
        self.area_chat.yview(tk.END)
        self.area_chat.config(state='disabled')
        self.enviar_requisicao({'comando': 'aviso_leitura', 'remetente': self.contato_atual})

    def atualizar_lista_contatos(self, utilizadores):
        if not self.janela_chat or not self.lista_contatos.winfo_exists(): return
        
        selecionado_texto = None
        if self.lista_contatos.curselection():
            selecionado_texto = self.lista_contatos.get(self.lista_contatos.curselection()[0])

        self.lista_contatos.delete(0, tk.END)
        for user in sorted(utilizadores.keys()):
            if user == self.username: continue
            status = utilizadores[user]
            cor = self.ONLINE_COLOR if status == 'online' else self.OFFLINE_COLOR
            item_texto = f"{user} ({status})"
            self.lista_contatos.insert(tk.END, item_texto)
            self.lista_contatos.itemconfig(tk.END, {'fg': cor})
            if selecionado_texto and selecionado_texto == item_texto:
                self.lista_contatos.selection_set(tk.END)

    def enviar_mensagem_evento(self, event=None):
        conteudo = self.entry_msg.get()
        if conteudo and self.contato_atual:
            self.entry_msg.delete(0, tk.END)
            msg = {'comando': 'enviar_mensagem', 'destinatario': self.contato_atual, 'conteudo': conteudo}
            self.enviar_requisicao(msg)

    def processar_nova_mensagem(self, msg):
        remetente = msg['remetente']
        destinatario = msg['destinatario']
        outro_user = remetente if remetente != self.username else destinatario

        if self.contato_atual == outro_user:
            autor = "Você" if remetente == self.username else remetente
            ts_formatado = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M')
            self.area_chat.config(state='normal')
            self.area_chat.insert(tk.END, f"[{ts_formatado}] {autor}: {msg['conteudo']}\n")
            self.area_chat.yview(tk.END)
            self.area_chat.config(state='disabled')
            if remetente != self.username:
                self.enviar_requisicao({'comando': 'aviso_leitura', 'remetente': remetente})
    
    def exibir_mensagem_sistema(self, texto):
        if not self.janela_chat or not self.area_chat.winfo_exists(): return
        self.area_chat.config(state='normal')
        self.area_chat.insert(tk.END, f"\n--- {texto} ---\n", 'system')
        self.area_chat.yview(tk.END)
        self.area_chat.config(state='disabled')

    def evento_digitando(self, event=None):
        if self.contato_atual:
            if self.timer_digitando:
                self.janela_chat.after_cancel(self.timer_digitando)
            else:
                self.enviar_requisicao({'comando': 'typing', 'destinatario': self.contato_atual, 'status': 'start'})
            
            self.timer_digitando = self.janela_chat.after(2000, self.parou_de_digitar)

    def parou_de_digitar(self):
        if self.contato_atual:
            self.enviar_requisicao({'comando': 'typing', 'destinatario': self.contato_atual, 'status': 'stop'})
        self.timer_digitando = None

    def mostrar_status_digitando(self, remetente, status):
        if self.contato_atual == remetente:
            if status == 'start':
                self.label_status.config(text=f"{remetente} está a digitar...")
            else:
                self.label_status.config(text=f"Conversando com {self.contato_atual}")

    def fechar_app(self):
        if self.conectado:
            self.conectado = False
            if self.sock:
                try: self.sock.close()
                except OSError: pass
        
        root = self.janela_chat or self.janela_login
        if root and root.winfo_exists():
            root.destroy()

if __name__ == "__main__":
    ChatClienteGUI()
