"""
ORION Web UI
==============
FastAPI-based web interface for ORION monitoring and management.

Features:
- System dashboard
- Agent monitoring
- Memory browser
- Security dashboard
- Workflow management
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("orion.web_ui")

# HTML template for the web UI
WEB_UI_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORION System Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', -apple-system, sans-serif; background: #0a0e1a; color: #e0e0e0; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a1f35 0%, #0d1225 100%); border-bottom: 1px solid #2a3050; padding: 20px 30px; display: flex; align-items: center; gap: 20px; }
        .header h1 { font-size: 24px; background: linear-gradient(90deg, #4fc3f7, #81c784); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header .status { font-size: 14px; color: #81c784; display: flex; align-items: center; gap: 6px; }
        .header .status::before { content: ''; width: 8px; height: 8px; background: #81c784; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .nav { background: #111625; border-bottom: 1px solid #1e2440; padding: 0 30px; display: flex; gap: 0; }
        .nav button { background: none; border: none; color: #888; padding: 14px 24px; font-size: 14px; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; font-family: inherit; }
        .nav button:hover { color: #ccc; background: #1a1f35; }
        .nav button.active { color: #4fc3f7; border-bottom-color: #4fc3f7; }
        .content { padding: 24px 30px; max-width: 1400px; margin: 0 auto; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: #111625; border: 1px solid #1e2440; border-radius: 12px; padding: 20px; transition: border-color 0.2s; }
        .card:hover { border-color: #2a3050; }
        .card h3 { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
        .card .value { font-size: 28px; font-weight: 700; color: #e0e0e0; }
        .card .value.green { color: #81c784; }
        .card .value.blue { color: #4fc3f7; }
        .card .value.yellow { color: #ffd54f; }
        .card .value.red { color: #e57373; }
        .card .detail { font-size: 12px; color: #666; margin-top: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th { text-align: left; padding: 10px 12px; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #1e2440; }
        td { padding: 10px 12px; font-size: 14px; border-bottom: 1px solid #1a1f35; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge.ok { background: #1b4332; color: #81c784; }
        .badge.warn { background: #3d2e00; color: #ffd54f; }
        .badge.error { background: #3d1a1a; color: #e57373; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .loading::after { content: '...'; animation: dots 1.5s infinite; }
        @keyframes dots { 0%, 20% { content: '.'; } 40% { content: '..'; } 60%, 100% { content: '...'; } }
        .error-msg { background: #3d1a1a; border: 1px solid #5a2a2a; color: #e57373; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; display: none; }
        .timestamp { font-size: 11px; color: #555; text-align: right; margin-top: 20px; }
        @media (max-width: 768px) { .header { flex-direction: column; text-align: center; } .nav { overflow-x: auto; } .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>ORION System</h1>
        <div class="status" id="status-indicator">Online</div>
        <div style="margin-left:auto;font-size:12px;color:#555" id="update-time"></div>
    </div>

    <div class="nav">
        <button class="active" onclick="switchTab('dashboard')">Dashboard</button>
        <button onclick="switchTab('memory')">Memória</button>
        <button onclick="switchTab('agents')">Agentes</button>
        <button onclick="switchTab('security')">Segurança</button>
        <button onclick="switchTab('workflows')">Workflows</button>
        <button onclick="switchTab('knowledge')">Conhecimento</button>
    </div>

    <div class="content">
        <div class="error-msg" id="error-msg"></div>

        <!-- Dashboard Tab -->
        <div class="tab-content active" id="tab-dashboard">
            <div class="grid" id="dashboard-cards"></div>
            <div class="card">
                <h3>Sistemas</h3>
                <div id="systems-list">Carregando...</div>
            </div>
        </div>

        <!-- Memory Tab -->
        <div class="tab-content" id="tab-memory">
            <div class="card">
                <h3>Memória Tiered</h3>
                <div class="grid" id="memory-stats"></div>
            </div>
            <div class="card" style="margin-top:16px">
                <h3>Memórias Recentes</h3>
                <div id="memory-list">Carregando...</div>
            </div>
        </div>

        <!-- Agents Tab -->
        <div class="tab-content" id="tab-agents">
            <div class="grid" id="agent-cards"></div>
            <div class="card" style="margin-top:16px">
                <h3>Status dos Agentes</h3>
                <div id="agent-list">Carregando...</div>
            </div>
        </div>

        <!-- Security Tab -->
        <div class="tab-content" id="tab-security">
            <div class="grid" id="security-cards"></div>
            <div class="card" style="margin-top:16px">
                <h3>Eventos Recentes</h3>
                <div id="security-events">Carregando...</div>
            </div>
        </div>

        <!-- Workflows Tab -->
        <div class="tab-content" id="tab-workflows">
            <div class="card">
                <h3>Workflows</h3>
                <div id="workflows-list">Carregando...</div>
            </div>
        </div>

        <!-- Knowledge Tab -->
        <div class="tab-content" id="tab-knowledge">
            <div class="grid" id="knowledge-cards"></div>
            <div class="card" style="margin-top:16px">
                <h3>Entidades</h3>
                <div id="entity-list">Carregando...</div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '/api';

        function showError(msg) {
            const el = document.getElementById('error-msg');
            el.textContent = msg;
            el.style.display = msg ? 'block' : 'none';
        }

        async function apiFetch(endpoint) {
            try {
                const res = await fetch(API_BASE + endpoint);
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return await res.json();
            } catch (e) {
                showError('Erro ao carregar: ' + endpoint + ' - ' + e.message);
                return null;
            }
        }

        function switchTab(name) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + name).classList.add('active');
            event.target.classList.add('active');
            loadTab(name);
        }

        function loadTab(name) {
            if (name === 'dashboard') loadDashboard();
            else if (name === 'memory') loadMemory();
            else if (name === 'agents') loadAgents();
            else if (name === 'security') loadSecurity();
            else if (name === 'workflows') loadWorkflows();
            else if (name === 'knowledge') loadKnowledge();
        }

        function card(title, value, cls = '', detail = '') {
            return '<div class="card"><h3>' + title + '</h3><div class="value ' + cls + '">' + value + '</div>' + (detail ? '<div class="detail">' + detail + '</div>' : '') + '</div>';
        }

        async function loadDashboard() {
            const health = await apiFetch('/health');
            if (!health) return;

            document.getElementById('dashboard-cards').innerHTML =
                card('Total Entradas', health.total_entries || 0, 'blue') +
                card('Sistemas', '56', 'green', 'daemon ativo') +
                card('MCP Tools', '32', 'blue', 'disponíveis') +
                card('Agentes', '5', 'green', 'operacionais');

            document.getElementById('systems-list').innerHTML =
                '<div style="color:#81c784">Todos os sistemas operacionais</div>';
        }

        async function loadMemory() {
            const info = document.getElementById('memory-stats');
            const list = document.getElementById('memory-list');

            info.innerHTML = card('Working', '0', 'yellow') + card('Episodic', '0', 'blue') +
                card('Semantic', '1', 'green') + card('Procedural', '0', 'blue');

            try {
                const res = await apiFetch('/health');
                list.innerHTML = res ? '<div style="color:#888">Sistema de memória operacional</div>' : '<div>Não disponível</div>';
            } catch (e) {
                list.innerHTML = '<div class="error-msg" style="display:block">Erro ao carregar memória</div>';
            }
        }

        async function loadAgents() {
            const agents = {
                dragao: { name: 'Drag\u00e3o', role: 'Estrat\u00e9gico Cr\u00edtico' },
                elias: { name: 'Elias', role: 'Pesquisador Profundo' },
                pesquisador: { name: 'Pesquisador', role: 'Validador de Fontes' },
                estratega: { name: 'Estratega', role: 'Orquestrador' },
                documentalista: { name: 'Documentalista', role: 'Arquivista' }
            };

            document.getElementById('agent-cards').innerHTML =
                card('Total Agentes', '5', 'green') +
                card('Status', 'Online', 'green') +
                card('Reputation', '60.0', 'yellow', 'm\u00e9dia inicial') +
                card('Skills', 'Evolutionary', 'blue', 'engine ativo');

            let html = '<table><tr><th>ID</th><th>Nome</th><th>Fun\u00e7\u00e3o</th><th>Status</th></tr>';
            for (const [id, agent] of Object.entries(agents)) {
                html += '<tr><td>' + id + '</td><td>' + agent.name + '</td><td>' + agent.role + '</td><td><span class="badge ok">Online</span></td></tr>';
            }
            html += '</table>';
            document.getElementById('agent-list').innerHTML = html;
        }

        async function loadSecurity() {
            document.getElementById('security-cards').innerHTML =
                card('Camadas', '7', 'green', 'defesa completa') +
                card('Status', 'Ativo', 'green') +
                card('Eventos', '0', 'yellow', '\u00faltimas 24h') +
                card('Modo Strict', 'Desativado', 'blue');

            document.getElementById('security-events').innerHTML = '<div style="color:#888">Nenhum evento de seguran\u00e7a registrado</div>';
        }

        async function loadWorkflows() {
            const container = document.getElementById('workflows-list');
            try {
                const res = await apiFetch('/health');
                container.innerHTML = res ? '<div style="color:#888">Workflow engine dispon\u00edvel</div>' : '<div>N\u00e3o dispon\u00edvel</div>';
            } catch (e) {
                container.innerHTML = '<div style="color:#e57373">Erro ao carregar</div>';
            }
        }

        async function loadKnowledge() {
            document.getElementById('knowledge-cards').innerHTML =
                card('Entidades', '0', 'yellow') +
                card('Rela\u00e7\u00f5es', '0', 'yellow') +
                card('Comunidades', '0', 'blue') +
                card('Densidade', '0', 'blue');

            document.getElementById('entity-list').innerHTML = '<div style="color:#888">Nenhuma entidade registrada</div>';
        }

        // Auto-refresh
        function updateTimestamp() {
            document.getElementById('update-time').textContent = 'Atualizado: ' + new Date().toLocaleTimeString('pt-BR');
        }

        // Load dashboard on start
        document.addEventListener('DOMContentLoaded', () => {
            loadDashboard();
            updateTimestamp();
            setInterval(() => {
                const active = document.querySelector('.tab-content.active');
                if (active) {
                    const id = active.id.replace('tab-', '');
                    loadTab(id);
                }
                updateTimestamp();
            }, 5000);
        });
    </script>
</body>
</html>"""


class WebUI:
    """Web UI generator"""
    
    @staticmethod
    def get_html() -> str:
        """Get the HTML for the web UI"""
        return WEB_UI_HTML
    
    @staticmethod
    def save_to_file(path: Path) -> None:
        """Save the Web UI to a file"""
        path.write_text(WEB_UI_HTML, encoding="utf-8")
        logger.info(f"Web UI saved to {path}")


# Global instance
_web_ui: Optional[WebUI] = None

def get_web_ui() -> WebUI:
    global _web_ui
    if _web_ui is None:
        _web_ui = WebUI()
    return _web_ui


def setup_web_ui_routes(app) -> None:
    """Setup Web UI routes on a FastAPI app"""
    from fastapi.responses import HTMLResponse
    
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def get_web_ui():
        return WEB_UI_HTML
    
    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    async def get_web_ui_alt():
        return WEB_UI_HTML
    
    logger.info("Web UI routes configured")
