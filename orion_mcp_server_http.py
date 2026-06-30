#!/usr/bin/env python3
"""
ORION MCP Server - HTTP/SSE Version
====================================
HTTP server that exposes ORION's tools via SSE (Server-Sent Events)
for Gemini Desktop and other MCP clients.

Usage:
    python orion_mcp_server_http.py

Gemini Configuration:
    Add to ~/.gemini/settings.json
"""

import sys
import json
import logging
import asyncio
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
import queue

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from orion.daemon import ORIONDaemon

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[ORION MCP HTTP] %(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orion_mcp_http")


class MCPHandler(BaseHTTPRequestHandler):
    """HTTP Handler for MCP protocol"""
    
    daemon = None
    clients = []
    client_lock = threading.Lock()
    
    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        if self.path == '/sse':
            self.handle_sse()
        elif self.path == '/api/health':
            self.handle_health()
        elif self.path == '/api/tools':
            self.handle_tools()
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/mcp':
            self.handle_mcp_request()
        else:
            self.send_error(404)
    
    def handle_sse(self):
        """Server-Sent Events endpoint for MCP"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        client_queue = queue.Queue()
        with MCPHandler.client_lock:
            MCPHandler.clients.append(client_queue)
        
        try:
            self.wfile.write(b'event: connected\ndata: {"status": "connected"}\n\n')
            self.wfile.flush()
            
            while True:
                try:
                    message = client_queue.get(timeout=30)
                    self.wfile.write(f"data: {json.dumps(message)}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with MCPHandler.client_lock:
                if client_queue in MCPHandler.clients:
                    MCPHandler.clients.remove(client_queue)
    
    def handle_health(self):
        """Health check endpoint"""
        response = {
            "status": "healthy",
            "service": "ORION MCP Server",
            "version": "4.0",
            "agents": ["general", "dragao", "elias", "pesquisador", "estratega", "documentalista"]
        }
        self.send_json(response)
    
    def handle_tools(self):
        """List available tools"""
        tools = [
            {
                "name": "general_analyze",
                "description": "Análise estratégica com anti-alucinação",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {"type": "string", "enum": ["URGENTE", "DEEP DIVE", "ANALISAR", "COMPARAR", "RISCOS", "RESUMIR"]},
                        "data": {"type": "string", "description": "Dados para análise"}
                    },
                    "required": ["analysis_type", "data"]
                }
            },
            {
                "name": "general_think",
                "description": "Pensamento profundo com 5 Tiers de Certeza",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Prompt de análise"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "general_research",
                "description": "Pesquisa com fontes confiáveis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Tópico para pesquisar"}
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "general_status",
                "description": "Status do sistema General",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
        self.send_json({"tools": tools})
    
    def handle_mcp_request(self):
        """Handle MCP JSON-RPC requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            request = json.loads(body)
            response = self.process_mcp_request(request)
            self.send_json(response)
        except json.JSONDecodeError:
            self.send_json({"error": {"code": -32700, "message": "Parse error"}})
    
    def process_mcp_request(self, request):
        """Process MCP JSON-RPC request"""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "orion-mcp",
                        "version": "4.0"
                    }
                }
            }
        
        elif method == "tools/list":
            tools = [
                {
                    "name": "general_analyze",
                    "description": "Análise estratégica com anti-alucinação",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "analysis_type": {"type": "string"},
                            "data": {"type": "string"}
                        },
                        "required": ["analysis_type", "data"]
                    }
                },
                {
                    "name": "general_think",
                    "description": "Pensamento profundo com 5 Tiers de Certeza",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"}
                        },
                        "required": ["prompt"]
                    }
                }
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "general_analyze":
                result = self.analyze(arguments)
                return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}
            elif tool_name == "general_think":
                result = self.think(arguments)
                return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}
            elif tool_name == "general_status":
                result = {"status": "active", "version": "4.0", "modules": 67}
                return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
            else:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": f"Tool not found: {tool_name}"}}
        
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    
    def analyze(self, arguments):
        """Execute analysis"""
        from orion.agents import get_general
        general = get_general()
        
        analysis_type = arguments.get("analysis_type", "ANALISAR")
        data = arguments.get("data", "")
        
        prompt = f"[{analysis_type}] {data}"
        result = general.think(prompt)
        
        return {
            "analysis_type": analysis_type,
            "result": result.get("final_analysis", str(result)),
            "confidence": result.get("confidence", {}).get("percentage", 0),
            "certainty_tier": result.get("certainty_tier", "DESCONHECIDO")
        }
    
    def think(self, arguments):
        """Execute thinking"""
        from orion.agents import get_general
        general = get_general()
        
        prompt = arguments.get("prompt", "")
        result = general.think(prompt)
        
        return {
            "result": result.get("final_analysis", str(result)),
            "confidence": result.get("confidence", {}).get("percentage", 0)
        }
    
    def send_json(self, data):
        """Send JSON response"""
        response = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    """Start HTTP MCP server"""
    logger.info("Initializing ORION MCP HTTP Server...")
    
    try:
        MCPHandler.daemon = ORIONDaemon()
        logger.info("ORION Daemon loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ORION Daemon: {e}")
        sys.exit(1)
    
    port = 8001
    server = ThreadingHTTPServer(('0.0.0.0', port), MCPHandler)
    
    logger.info(f"ORION MCP HTTP Server running on http://localhost:{port}")
    logger.info(f"SSE Endpoint: http://localhost:{port}/sse")
    logger.info(f"Health Check: http://localhost:{port}/api/health")
    logger.info(f"Tools List: http://localhost:{port}/api/tools")
    logger.info("Waiting for connections...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
