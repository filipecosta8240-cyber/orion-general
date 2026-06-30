"""
ORION General Agent - Cloud Server
====================================
Servidor para deployment em cloud (Railway, Render, etc.)

Uso:
    python orion_cloud_server.py

Endpoints:
    GET  /          - Interface web
    GET  /api/health - Health check
    POST /api/chat  - Chat com General Agent
"""

import json
import sys
import os
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading

# Configuração
PORT = int(os.environ.get('PORT', 8080))
PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "ORION_SYSTEM" / "web_ui"


class ORIONCloudHandler(BaseHTTPRequestHandler):
    """Handler para servidor cloud"""
    
    def log_message(self, format, *args):
        print(f"[ORION] {self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        if self.path == '/api/health':
            self.send_json({"status": "healthy", "service": "ORION General Agent", "version": "5.0"})
        elif self.path == '/' or self.path == '/index.html':
            self.serve_file('index.html', 'text/html')
        elif self.path == '/manifest.json':
            self.serve_file('manifest.json', 'application/json')
        elif self.path.endswith('.css'):
            self.serve_file(self.path[1:], 'text/css')
        elif self.path.endswith('.js'):
            self.serve_file(self.path[1:], 'application/javascript')
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
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
        """Chama o General Agent"""
        try:
            import subprocess
            
            python_path = sys.executable
            script = f"""
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")

# Tenta importar ORION
try:
    from orion.agents import get_general
    general = get_general()
    result = general.think("{message.replace('"', '\\"')}")
    print(result)
except ImportError:
    # Fallback se ORION não estiver disponível
    print("ORION não disponível no cloud. Mensagem recebida: {message}")
"""
            result = subprocess.run(
                [python_path, "-c", script],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Erro: {result.stderr[:200]}"
                
        except subprocess.TimeoutExpired:
            return "Timeout: resposta demorou mais de 60 segundos"
        except Exception as e:
            return f"Erro ao processar: {str(e)}"
    
    def serve_file(self, filename, content_type):
        """Serve um ficheiro estático"""
        file_path = WEB_DIR / filename
        if file_path.exists():
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', f'{content_type}; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)
    
    def send_json(self, data):
        """Envia resposta JSON"""
        response = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)
    
    def do_OPTIONS(self):
        """Handle CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    print("=" * 50)
    print("  ORION GENERAL AGENT - Cloud Server")
    print("=" * 50)
    print()
    print(f"  Porta: {PORT}")
    print(f"  Web Dir: {WEB_DIR}")
    print()
    
    server = ThreadingHTTPServer(('0.0.0.0', PORT), ORIONCloudHandler)
    
    print("  Servidor iniciado!")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")
        server.shutdown()


if __name__ == "__main__":
    main()
