"""
ORION Web Server - Interface Móvel
===================================
Servidor web para aceder ao General Agent via telemóvel.

Uso:
    python orion_web_server.py

Aceder no telemóvel:
    http://IP_COMPUTADOR:8080
"""

import json
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web_ui"

# IP do computador na rede local
def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"


class ORIONHandler(SimpleHTTPRequestHandler):
    """Handler para o servidor web ORION"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)
    
    def log_message(self, format, *args):
        print(f"[ORION Web] {self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        if self.path == '/api/health':
            self.send_json({"status": "healthy", "service": "ORION General Agent"})
        elif self.path == '/':
            self.path = '/index.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                message = data.get('message', '')
                
                # Chama o General Agent
                response = self.call_general(message)
                
                self.send_json({"response": response})
            except Exception as e:
                self.send_json({"response": f"Erro: {str(e)}"})
        else:
            self.send_error(404)
    
    def call_general(self, message):
        """Chama o General Agent"""
        try:
            import subprocess
            python_path = r"C:\Users\BIG_P\AppData\Local\Programs\Python\Python314\python.exe"
            script = f"""
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")
from orion.agents import get_general
general = get_general()
result = general.think("{message}")
print(result)
"""
            result = subprocess.run(
                [python_path, "-c", script],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
                env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Erro: {result.stderr[:200]}"
                
        except subprocess.TimeoutExpired:
            return "Timeout: resposta demorou mais de 60 segundos"
        except Exception as e:
            return f"Erro ao processar: {str(e)}"
    
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
    port = 8080
    ip = get_local_ip()
    
    print("=" * 50)
    print("  ORION GENERAL AGENT - Interface Móvel")
    print("=" * 50)
    print()
    print(f"  Servidor: http://{ip}:{port}")
    print(f"  Local:    http://localhost:{port}")
    print()
    print("  Para aceder no telemóvel:")
    print(f"  1. Ligue o telemóvel à mesma rede WiFi")
    print(f"  2. Abra o navegador")
    print(f"  3. Digite: http://{ip}:{port}")
    print()
    print("  Para instalar como app:")
    print("  1. Abra no Chrome")
    print("  2. Toque nos 3 pontos")
    print("  3. Selecione 'Adicionar ao ecrã inicial'")
    print()
    print("  Ctrl+C para parar")
    print("=" * 50)
    print()
    
    server = ThreadingHTTPServer(('0.0.0.0', port), ORIONHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")
        server.shutdown()


if __name__ == "__main__":
    main()
