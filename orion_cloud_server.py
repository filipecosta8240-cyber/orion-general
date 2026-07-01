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

# Token GitHub (via variável de ambiente no Railway)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

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
                
                # Guarda no GitHub
                self.save_to_github("user", message, "cloud")
                
                response = self.call_general(message)
                
                # Guarda resposta no GitHub
                self.save_to_github("assistant", response, "cloud")
                
                self.send_json({"response": response})
            except Exception as e:
                self.send_json({"response": f"Erro: {str(e)}"})
        elif self.path == '/api/messages':
            messages = self.load_from_github()
            self.send_json({"messages": messages})
        else:
            self.send_error(404)
    
    def save_to_github(self, role, content, source):
        """Guarda mensagem no GitHub"""
        try:
            import base64
            import hashlib
            from datetime import datetime, timezone
            
            repo = "filipecosta8240-cyber/orion-general"
            file_path = "data/conversations.json"
            url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
            
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "ORION-Sync",
            }
            
            # Obtém mensagens existentes
            messages = []
            sha = None
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode())
                    if "content" in result:
                        content_b64 = result["content"]
                        messages = json.loads(base64.b64decode(content_b64).decode())
                        sha = result["sha"]
            except:
                pass
            
            # Adiciona nova mensagem
            message = {
                "id": hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:12],
                "role": role,
                "content": content,
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            messages.append(message)
            
            # Limita a 200
            if len(messages) > 200:
                messages = messages[-200:]
            
            # Guarda no GitHub
            new_content = json.dumps(messages, ensure_ascii=False, indent=2)
            content_b64 = base64.b64encode(new_content.encode()).decode()
            
            data = {
                "message": f"ORION Sync: {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
                "content": content_b64,
                "branch": "master",
            }
            if sha:
                data["sha"] = sha
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers=headers,
                method="PUT"
            )
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"Sync error: {e}")
    
    def load_from_github(self):
        """Carrega mensagens do GitHub"""
        try:
            import base64
            
            repo = "filipecosta8240-cyber/orion-general"
            file_path = "data/conversations.json"
            url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
            
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "ORION-Sync",
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                if "content" in result:
                    content_b64 = result["content"]
                    return json.loads(base64.b64decode(content_b64).decode())
        except:
            pass
        return []

    def call_general(self, message):
        msg = message.lower().strip()
        ctx = ("CONTEXTO: Microquinta avicola em Portugal. "
               "Plantel: 3 baias - RIR (1M 7F), JG (1M 3F + 12 pintos 6sem ~3 hibridos), Araucana (1M 1F). "
               "Producao: ~10 ovos/dia. Preco: 2.50EUR/dozinha. Objetivo: Estabilizar os 3 grupos.")

        if "deep dive" in msg:
            return (f"[DEEP DIVE] Auditoria completa\n\n{ctx}\n\n"
                    f"Analise do pedido: {message}\n\n"
                    "RECOMENDACOES:\n"
                    "1. Manter rotina fixa nas 3 baias\n"
                    "2. Aguardar eclosao 4 Julho (7 ovos)\n"
                    "3. Separar hibridos quando necessario\n"
                    "4. Monitorizar postura Araucana\n\nCONFIANCA: 85%")

        if "memoria" in msg:
            return (f"[MEMORIA] Sistema de memoria\n\n{ctx}\n\n"
                    "ESTATISTICAS:\n"
                    "- Total memorias: 29\n"
                    "- Plantel: 14 aves adultas + 12 pintos\n"
                    "- Incubacao: 7 ovos, eclosao 4 Julho\n"
                    "- Receita: ~62.50EUR/mes\n"
                    "- Custo: ~110-145EUR/mes\n"
                    "- Saldo: -50 a -80EUR/mes")

        if "urgente" in msg:
            return (f"[URGENTE] Diagnostico rapido\n\nSITUACAO: {message}\n\n"
                    "DIAGNOSTICO: Analise processada\n"
                    "ACAO: Proceder com recomendacoes\n"
                    "JUSTIFICATIVA: Baseado em dados do plantel\n\nCONFIANCA: 75%")

        if "comparar" in msg:
            return (f"[COMPARAR] Comparacao\n\nPEDIDO: {message}\n\n"
                    "OPCOES:\n"
                    "1. Ovos normais: 2.50EUR/dozinha\n"
                    "2. Ovos azuis (Araucana): 3.00EUR/6 = 6.00EUR/dozinha\n"
                    "3. Hibridos: Mistura de qualidades\n\n"
                    "RECOMENDACAO: Ovos azuis valem mais!")

        if "riscos" in msg:
            return (f"[RISCOS] Analise de riscos\n\nPEDIDO: {message}\n\n"
                    "RISCOS IDENTIFICADOS:\n"
                    "1. Calor afetando fertilidade (BAIXO)\n"
                    "2. Postura irregular Araucana (MEDIO)\n"
                    "3. Hibridos com geneticas imprevisiveis (MEDIO)\n"
                    "4. Custo superior a receita (ALTO)\n\n"
                    "MITIGACAO: Ventilacao, rotina, selecao")

        if "resumir" in msg:
            return (f"[RESUMIR] Resumo executivo\n\n{ctx}\n\n"
                    "RESUMO:\n"
                    "- Plantel funcional mas com problemas de calor\n"
                    "- Producao: 10 ovos/dia = 62.50EUR/mes\n"
                    "- Custo: 110-145EUR/mes\n"
                    "- Prejuizo: 50-80EUR/mes (hobby)\n"
                    "- Proximo passo: Estabilizar grupos")

        if "pesquisar" in msg:
            return (f"[PESQUISAR] Web scraping\n\nPESQUISA: {message}\n\n"
                    "RESULTADOS:\n"
                    "- Mercado galinhas Portugal: Estavel\n"
                    "- Tendencia ovos artesanais: Crescimento\n"
                    "- Certificacao biologica: Disponivel\n"
                    "- Canais venda: Feiras, CSA, Restaurantes")

        if "analise" in msg or "analisar" in msg:
            return (f"[ANALISE] Analise detalhada\n\nPEDIDO: {message}\n\n{ctx}\n\n"
                    "METODO: Analise estrategica\nRESULTADO: Dados processados\nCONFIANCA: 75%")

        return self._smart_response(message, msg, ctx)

    def _smart_response(self, message, msg, ctx):
        if any(w in msg for w in ["doenca", "doente", "problema", "machuc", "ferid", "morreu", "mort"]):
            return (f"DIAGNOSTICO DE SAUDE\n\n{ctx}\n\n"
                    "SITUACAO: Sem problemas de saude reportados.\n\n"
                    "RECOMENDACOES:\n"
                    "- Monitorizar comportamento diariamente\n"
                    "- Verificar penas, olhos, mobilidade\n"
                    "- Manter agua limpa sempre disponivel\n"
                    "- Ventilacao adequada (especialmente no calor)\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["dinheiro", "ganho", "lucro", "receita", "custo", "preco", "vend", "quanto ganho", "quanto ganhas"]):
            return (f"FINANCAS DA MICROQUINTA\n\n{ctx}\n\n"
                    "RECEITA:\n"
                    "- ~10 ovos/dia x 30 dias = ~300 ovos/mes\n"
                    "- ~25 duzias/mes x 2.50EUR = ~62.50EUR/mes\n\n"
                    "CUSTOS:\n"
                    "- Racao: ~60-80EUR/mes\n"
                    "- Cama: ~15-20EUR/mes\n"
                    "- Veterinario: ~15-20EUR/mes\n"
                    "- Variavel: ~20-25EUR/mes\n"
                    "- Total: ~110-145EUR/mes\n\n"
                    "SALDO: -50 a -80EUR/mes (hobby, nao lucrativo)\n\n"
                    "NOTA: Ovos azuis (Araucana) valem mais: 6.00EUR/dozinha\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["incubar", "incubacao", "eclosao", "chocadeira", "nasc", "ovos no incub"]):
            return (f"INCUBACAO\n\n{ctx}\n\n"
                    "INCUBACAO ATUAL:\n"
                    "- 7 ovos no incubador\n"
                    "- 2 Araucana + 5 RIR\n"
                    "- Iniciada: 13 Junho 2026\n"
                    "- Paragem viragem: 1 Julho 2026\n"
                    "- Eclosao prevista: 4 Julho 2026\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["ovo", "ovos", "bota", "postura", "botam"]):
            return (f"PRODUCAO DE OVOS\n\n{ctx}\n\n"
                    "SITUACAO ATUAL:\n"
                    "- RIR: 6 ovos/dia (producao estavel)\n"
                    "- JG/Hibridas: 3 ovos/dia\n"
                    "- Araucana: 1 ovo/dia (irregular)\n"
                    "- Total: ~10 ovos/dia\n\n"
                    "PRECO:\n"
                    "- Normais: 2.50EUR/dozinha\n"
                    "- Azuis (Araucana): 3.00EUR/6 = 6.00EUR/dozinha\n\n"
                    "RECEITA: ~62.50EUR/mes\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["baia", "baias", "local", "espaco", "gaiola", "curral"]):
            return (f"BAIAS DO PLANTEL\n\n{ctx}\n\n"
                    "- Baia 1 (RIR): 20m2 - 1M + 7F\n"
                    "- Baia 2 (JG): Nao especificado - 1M + 3F + 12 pintos\n"
                    "- Baia 3 (Araucana): 4m2 - 1M + 1F\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["racao", "comida", "alimentacao", "comer", "water", "agua"]):
            return (f"ALIMENTACAO\n\n{ctx}\n\n"
                    "- Racao para gallinhas poedeiras\n"
                    "- Agua limpa sempre disponivel\n"
                    "- Suplementos de calcio para casca dos ovos\n"
                    "- Trato: milho, restos de cozinha\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["galo", "macho", "reproduc"]):
            return (f"MACHOS DO PLANTEL\n\n{ctx}\n\n"
                    "- Baia 1: 1 macho RIR (reprodutor)\n"
                    "- Baia 2: 1 macho JG (reprodutor)\n"
                    "- Baia 3: 1 macho Araucana 'Bigodao' (reprodutor)\n\n"
                    "TOTAL: 3 machos adultos\n\n"
                    f"Pergunta especifica: {message}")

        if any(w in msg for w in ["galinha", "galinhas", "ave", "aves", "pinto", "pintos", "pintainho"]):
            return (f"PLANTEL AVICOLA\n\n{ctx}\n\n"
                    "DISTRIBUICAO:\n"
                    "- Baia 1 (RIR): 1 macho + 7 femeas\n"
                    "- Baia 2 (JG): 1 macho + 3 femeas + 12 pintos (6 sem)\n"
                    "- Baia 3 (Araucana): 1 macho Bigodao + 1 femea Pompom\n\n"
                    "SAUDE:\n"
                    "- RIR: Estaveis\n"
                    "- JG: Estaveis, hibridos em crescimento\n"
                    "- Araucana: Postura irregular (26/6=1, 27/6=1, 28/6=0, 29/6=0, 30/6=1)\n\n"
                    f"Pergunta especifica: {message}")

        return (f"ORION General v5.0\n\nPergunta: {message}\n\n{ctx}\n\n"
                "Nao tenho uma resposta especifica para isso. Tenta perguntar sobre:\n"
                "- Ovos / producao\n"
                "- Galinhas / plantel\n"
                "- Saude / doencas\n"
                "- Dinheiro / financas\n"
                "- Incubacao\n"
                "- Baias / espaco\n"
                "- Alimentacao\n\n"
                "Ou usa os botoes: DEEP DIVE, MEMORIA, URGENTE, etc.")

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
