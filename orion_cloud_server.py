"""
ORION General Agent - Cloud Server v2
======================================
Servidor simplificado para Railway.
HTML embutido no código - sem dependência de ficheiros externos.
"""

import json
import sys
import os
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get('PORT', 8080))
PROJECT_ROOT = Path(__file__).resolve().parent

# HTML embutido
HTML_PAGE = """<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#1a1a2e">
    <title>ORION General Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff; min-height: 100vh; display: flex; flex-direction: column;
        }
        .header { background: rgba(0,0,0,0.3); padding: 15px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .header h1 { font-size: 1.2rem; color: #4ade80; }
        .header .status { font-size: 0.8rem; color: #888; margin-top: 5px; }
        .chat-container { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }
        .message { max-width: 85%; padding: 12px 16px; border-radius: 18px; line-height: 1.4; font-size: 0.95rem; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message.user { align-self: flex-end; background: #4ade80; color: #000; border-bottom-right-radius: 4px; }
        .message.bot { align-self: flex-start; background: rgba(255,255,255,0.1); border-bottom-left-radius: 4px; }
        .message.bot.loading { color: #888; }
        .input-container { padding: 15px; background: rgba(0,0,0,0.3); border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 10px; }
        .input-container input { flex: 1; padding: 12px 16px; border: none; border-radius: 24px; background: rgba(255,255,255,0.1); color: #fff; font-size: 1rem; outline: none; }
        .input-container input::placeholder { color: #666; }
        .input-container button { padding: 12px 20px; border: none; border-radius: 24px; background: #4ade80; color: #000; font-weight: bold; cursor: pointer; }
        .input-container button:active { transform: scale(0.95); }
        .quick-actions { display: flex; gap: 8px; padding: 10px 15px; overflow-x: auto; }
        .quick-actions button { flex-shrink: 0; padding: 8px 14px; border: 1px solid rgba(255,255,255,0.2); border-radius: 16px; background: transparent; color: #4ade80; font-size: 0.8rem; cursor: pointer; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ORION GENERAL v5.0</h1>
        <div class="status" id="status">A conectar...</div>
    </div>
    <div class="chat-container" id="chat">
        <div class="message bot">
            General operacional. Versao 5.0.<br><br>
            Modos: [DEEP DIVE] [URGENTE] [ANALISAR] [COMPARAR] [RISCOS] [RESUMIR] [PESQUISAR] [MEMORIA]
        </div>
    </div>
    <div class="quick-actions">
        <button onclick="sendQuick('[DEEP DIVE] ')">DEEP DIVE</button>
        <button onclick="sendQuick('[URGENTE] ')">URGENTE</button>
        <button onclick="sendQuick('[ANALISAR] ')">ANALISAR</button>
        <button onclick="sendQuick('[RESUMIR] ')">RESUMIR</button>
        <button onclick="sendQuick('[MEMORIA] ')">MEMORIA</button>
    </div>
    <div class="input-container">
        <input type="text" id="userInput" placeholder="Escreva..." autocomplete="off">
        <button onclick="sendMessage()">Enviar</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('userInput');
        const status = document.getElementById('status');

        async function checkConnection() {
            try {
                const res = await fetch('/api/health');
                if (res.ok) { status.textContent = 'Online'; status.style.color = '#4ade80'; }
                else { status.textContent = 'Erro'; status.style.color = '#f87171'; }
            } catch (e) { status.textContent = 'Offline'; status.style.color = '#f87171'; }
        }

        function addMessage(text, isUser = false) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'bot');
            div.innerHTML = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function addLoading() {
            const div = document.createElement('div');
            div.className = 'message bot loading';
            div.id = 'loading';
            div.textContent = 'A processar...';
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function removeLoading() {
            const loading = document.getElementById('loading');
            if (loading) loading.remove();
        }

        function sendQuick(text) { input.value = text; sendMessage(); }

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            addMessage(text, true);
            input.value = '';
            addLoading();
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                removeLoading();
                addMessage(data.response || 'Sem resposta');
            } catch (e) {
                removeLoading();
                addMessage('Erro de conexao.');
            }
        }

        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        checkConnection();
    </script>
</body>
</html>"""


class ORIONHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[ORION] {format % args}")

    def do_GET(self):
        if self.path == '/api/health':
            self.send_json({"status": "healthy", "version": "5.0"})
        elif self.path == '/' or self.path == '/index.html':
            content = HTML_PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/chat':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                message = data.get('message', '')
                response = self.call_general(message)
                self.send_json({"response": response})
            except Exception as e:
                self.send_json({"response": f"Erro: {str(e)}"})
        else:
            self.send_error(404)

    def call_general(self, message):
        try:
            import subprocess
            script = f'''
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")
try:
    from orion.agents import get_general
    general = get_general()
    result = general.think("{message.replace(chr(34), chr(39))}")
    print(result)
except Exception as e:
    print(f"ORION offline: {{e}}")
'''
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=60,
                cwd=str(PROJECT_ROOT),
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            return result.stdout.strip() if result.returncode == 0 else "Erro ao processar"
        except Exception as e:
            return f"Erro: {str(e)}"

    def send_json(self, data):
        response = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    print(f"ORION Cloud Server - Port {PORT}")
    server = ThreadingHTTPServer(('0.0.0.0', PORT), ORIONHandler)
    print("Server running!")
    server.serve_forever()


if __name__ == "__main__":
    main()
