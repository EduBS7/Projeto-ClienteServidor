Relatório do Projeto 01 - Chat Cliente/Servidor
Aluno: Eduardo Batista
Professor: Ygor Amaral

O sistema foi desenvolvido seguindo a arquitetura cliente-servidor, com uma separação clara de responsabilidades para facilitar a manutenção e o entendimento do código.
1.1. Servidor

O servidor é o cérebro da aplicação e foi dividido em dois módulos principais para uma melhor organização:

    servidor.py: Este é o módulo principal que lida com a lógica de rede. Ele usa a biblioteca socket para criar um servidor TCP/IP que escuta por novas conexões de clientes. Para cada cliente que se conecta, uma nova thread é criada, permitindo o atendimento simultâneo de múltiplos utilizadores. Este módulo é responsável por receber, processar e encaminhar todas as mensagens do nosso protocolo.

    banco_de_dados.py: Este módulo abstrai toda a interação com a base de dados. Foi utilizado o SQLite, uma base de dados leve e baseada em ficheiro. A classe BancoDeDados centraliza todas as operações necessárias, como registar utilizadores, autenticá-los e, o mais importante, guardar o histórico de todas as mensagens.

1.2. Cliente

O cliente é uma aplicação desktop com interface gráfica (GUI), implementado num único ficheiro cliente.py.

    Interface Gráfica (GUI): Foi utilizada a biblioteca tkinter, que é padrão do Python, para criar uma interface funcional com um tema escuro. A GUI inclui uma janela de login/registo e, após a autenticação, a janela principal do chat com a lista de contactos e a área de conversa.

    Comunicação e Concorrência: O cliente usa um socket TCP para comunicar com o servidor. Para que a interface não congele enquanto espera por mensagens, a comunicação é gerida de forma inteligente:

        Uma thread de rede (escutar_servidor) fica em segundo plano, exclusivamente a receber dados do servidor.

        Para evitar erros de concorrência com o tkinter, esta thread não atualiza a interface diretamente. Em vez disso, ela coloca as mensagens recebidas numa Queue (uma fila segura).

        A thread principal (que gere a GUI) verifica essa fila a cada 100 milissegundos (after(100, ...)) e processa as mensagens, atualizando a interface de forma segura.

2. Protocolo de Comunicação

Para a comunicação entre cliente e servidor, foi criado um protocolo simples baseado em JSON. Todas as mensagens trocadas são objetos JSON enviados com um delimitador especial (\n\n) para garantir que as mensagens completas sejam lidas, mesmo que cheguem "coladas" ou em pedaços.

O formato geral de uma mensagem é:
{'comando': 'NOME_DO_COMANDO', 'chave': 'valor', ...}

Principais Comandos do Protocolo:

    registar / login: Enviado pelo cliente para se registar ou autenticar.

        Ex: {'comando': 'login', 'utilizador': 'eduardo', 'senha': '123'}

    login_sucesso: Enviado pelo servidor para confirmar o login e abrir a janela de chat no cliente.

    lista_utilizadores: Enviado pelo servidor para todos os clientes sempre que alguém entra ou sai. Contém o status (online/offline) de todos os utilizadores.

        Ex: {'comando': 'lista_utilizadores', 'utilizadores': {'ana': 'online', 'beto': 'offline'}}

    enviar_mensagem: Enviado pelo cliente para mandar uma mensagem a outro utilizador.

        Ex: {'comando': 'enviar_mensagem', 'destinatario': 'ana', 'conteudo': 'Olá!'}

    nova_mensagem: Enviado pelo servidor para entregar uma mensagem (seja em tempo real ou do histórico offline) a um cliente.

    buscar_historico: Enviado pelo cliente quando clica num contacto para pedir o histórico da conversa.

    historico_conversa: Enviado pelo servidor em resposta, contendo todas as mensagens trocadas entre os dois utilizadores.

    typing: Enviado pelo cliente para notificar que está a digitar.

        Ex: {'comando': 'typing', 'destinatario': 'ana', 'status': 'start' / 'stop'}

    aviso_leitura: Enviado pelo cliente ao abrir uma conversa para notificar o outro utilizador que as suas mensagens foram vistas.

    confirmacao_leitura: Enviado pelo servidor para o remetente original, para que o cliente possa exibir o aviso "Fulano visualizou...".

3. Implementação dos Requisitos Funcionais

    Registo e Autenticação: O servidor recebe os pedidos e usa as funções registar_utilizador e autenticar_utilizador da classe BancoDeDados para interagir com a base de dados SQLite.

    Lista de Contactos e Status: O servidor mantém um dicionário clientes_online. Sempre que alguém entra ou sai, a função broadcast_status_update é chamada, enviando uma lista atualizada com o status de todos para todos os clientes online. O cliente, ao receber, redesenha a sua lista de contactos com as cores apropriadas.

    Envio de Mensagens: O cliente envia a mensagem para o servidor. O servidor sempre guarda a mensagem no histórico da base de dados. Depois, verifica se o destinatário está online. Se estiver, encaminha a mensagem em tempo real. Se não, a mensagem fica guardada e será entregue na próxima vez que o utilizador fizer login (esta funcionalidade foi implementada no código final, onde o histórico serve como base para as mensagens offline).

    Indicador "Digitando...": O cliente usa um temporizador (after(2000, ...)). Ao premir uma tecla, envia um evento de start e inicia o temporizador. Se outra tecla for premida, o temporizador é reiniciado. Se o tempo esgotar, envia um evento de stop. O servidor apenas reencaminha estes eventos para o destinatário.

    Confirmação de Leitura: Ao clicar num contacto, o cliente pede o histórico da conversa. O servidor envia o histórico. Assim que o cliente o carrega, ele envia um comando aviso_leitura para o servidor, que o reencaminha para o outro utilizador, que então exibe a notificação.

4. Gerenciamento de Conexões e Concorrência

    Múltiplos Clientes: O servidor é multithread. A thread principal fica num loop infinito a aceitar novas conexões (socket.accept()). Para cada nova conexão, ela cria e inicia uma nova thread (gerir_cliente), isolando a comunicação de cada cliente e permitindo que o servidor atenda a vários simultaneamente.

    Segurança de Threads: Para evitar que múltiplas threads tentem modificar o dicionário clientes_online ao mesmo tempo (o que causaria erros), foi utilizado um threading.Lock. Qualquer operação de adição ou remoção neste dicionário é protegida por este "cadeado".

    Falhas de Conexão: Todo o bloco de comunicação principal no servidor e no cliente está dentro de um try...except. Se a conexão for encerrada abruptamente, uma exceção como ConnectionResetError é capturada. No servidor, o bloco finally garante que o utilizador seja removido da lista de online e que o seu novo status "offline" seja comunicado aos outros.

5. Desafios e Aprendizados

    Principal Desafio: O maior desafio foi, sem dúvida, a gestão de concorrência entre a thread de rede e a thread da interface gráfica (GUI) no cliente. O erro TclError: can't invoke "winfo" command era um sintoma constante deste problema. A solução final e robusta foi parar de tentar atualizar a GUI diretamente da thread de rede. Em vez disso, implementei uma queue.Queue, uma estrutura de dados segura para threads, que funciona como uma "caixa de entrada". A thread de rede apenas coloca as mensagens recebidas na fila, e a thread principal da GUI verifica essa fila periodicamente (after(100, ...)), processando as mensagens de forma segura.

    Principais Aprendizados:

        Sockets e Buffers: Aprendi na prática que os dados TCP não chegam em pacotes organizados. A implementação de um delimitador (\n\n) e de um buffer foi crucial para garantir que as mensagens JSON completas fossem lidas corretamente.

        Concorrência é Essencial: Ficou claro que um programa de rede responsivo é impossível sem concorrência. O uso de threading no servidor para múltiplos clientes e no cliente para uma GUI não-bloqueante foi o conceito mais importante do projeto.

        Design de Protocolo: Percebi que planear um protocolo claro (com o campo "comando") desde o início torna o desenvolvimento muito mais fácil, pois o servidor e o cliente sabem exatamente como interpretar cada mensagem.

6. Limitações

Apesar de funcional, o sistema atual possui algumas limitações conhecidas:

    Segurança: A comunicação não é criptografada. As senhas e as mensagens de chat trafegam como texto puro na rede, o que é inseguro. Uma melhoria futura seria implementar TLS/SSL.

    Persistência de Mensagens Offline: Embora todas as mensagens fiquem no histórico, a implementação atual não envia automaticamente as mensagens perdidas quando um utilizador fica online. O utilizador precisa de clicar no contacto para ver o histórico atualizado. (Nota: A sua versão final do código implementa isto, pode ajustar esta frase se quiser).

    Interface: A GUI é funcional mas simples. Não há suporte para envio de ficheiros, emojis, ou formatação de texto.

    Escalabilidade: O modelo de uma thread por cliente não é ideal para milhares de utilizadores. Para uma aplicação em larga escala, seria necessário usar I/O assíncrono (como asyncio).
