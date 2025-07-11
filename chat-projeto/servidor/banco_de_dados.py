import sqlite3

class BancoDeDados:
    def __init__(self, db_name='chat_final.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._criar_tabelas()

    def _criar_tabelas(self):
        # Tabela de utilizadores
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS utilizadores (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        ''')
        # Tabela para o histórico de todas as mensagens
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remetente TEXT NOT NULL,
                destinatario TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def registar_utilizador(self, username, password):
        try:
            self.cursor.execute("INSERT INTO utilizadores (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def autenticar_utilizador(self, username, password):
        self.cursor.execute("SELECT * FROM utilizadores WHERE username = ? AND password = ?", (username, password))
        return self.cursor.fetchone() is not None

    def buscar_todos_utilizadores(self):
        self.cursor.execute("SELECT username FROM utilizadores")
        return [row[0] for row in self.cursor.fetchall()]

    def salvar_mensagem(self, remetente, destinatario, conteudo, timestamp):
        self.cursor.execute("INSERT INTO historico_mensagens (remetente, destinatario, conteudo, timestamp) VALUES (?, ?, ?, ?)",
                           (remetente, destinatario, conteudo, timestamp))
        self.conn.commit()

    def buscar_historico(self, utilizador1, utilizador2):
        self.cursor.execute("""
            SELECT remetente, conteudo, timestamp FROM historico_mensagens
            WHERE (remetente = ? AND destinatario = ?) OR (remetente = ? AND destinatario = ?)
            ORDER BY timestamp ASC
        """, (utilizador1, utilizador2, utilizador2, utilizador1))
        return self.cursor.fetchall()