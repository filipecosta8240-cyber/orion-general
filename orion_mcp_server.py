#!/usr/bin/env python3
"""
ORION MCP Server for Claude Desktop
====================================
Standalone MCP server that exposes ORION's tools and resources to Claude Desktop.

Usage:
    python orion_mcp_server.py

Configuration for Claude Desktop:
    Add to ~/.claude/claude_desktop_config.json
"""

import sys
import json
import logging
from pathlib import Path

# Adiciona o diretório do projeto ao path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from orion.mcp_server import MCPServer, MCPToolDefinition, MCPResource
from orion.daemon import ORIONDaemon

# Configuração de logging para stderr (não stdout!)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[ORION MCP] %(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orion_mcp")


class ORIONMCPServer:
    """MCP Server standalone para Claude Desktop"""
    
    def __init__(self):
        logger.info("Inicializando ORION MCP Server...")
        self.daemon = ORIONDaemon()
        self.mcp = MCPServer(self.daemon)
        logger.info(f"ORION MCP Server pronto com {len(self.mcp.tools)} ferramentas")
    
    def send_response(self, response):
        """Envia resposta JSON-RPC para stdout"""
        print(json.dumps(response), flush=True)
    
    def handle_request(self, request):
        """Processa uma requisição JSON-RPC"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.info(f"Método: {method}")
        
        try:
            if method == "initialize":
                return self.handle_initialize(request_id, params)
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                return self.handle_tools_list(request_id)
            elif method == "tools/call":
                return self.handle_tools_call(request_id, params)
            elif method == "resources/list":
                return self.handle_resources_list(request_id)
            elif method == "resources/read":
                return self.handle_resources_read(request_id, params)
            elif method == "prompts/list":
                return self.handle_prompts_list(request_id)
            elif method == "prompts/get":
                return self.handle_prompts_get(request_id, params)
            else:
                return self.error_response(request_id, -32601, f"Método não encontrado: {method}")
        except Exception as e:
            logger.error(f"Erro ao processar {method}: {e}")
            return self.error_response(request_id, -32603, str(e))
    
    def handle_initialize(self, request_id, params):
        """Handler para initialize"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {
                        "subscribe": False
                    },
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "orion-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    def handle_tools_list(self, request_id):
        """Lista todas as ferramentas disponíveis"""
        tools = []
        
        # Ferramentas do ORION
        for name, tool_def in self.mcp.tools.items():
            tools.append({
                "name": name,
                "description": tool_def.description,
                "inputSchema": tool_def.inputSchema.to_dict()
            })
        
        # Ferramentas adicionais
        additional_tools = [
            {
                "name": "orion_memory_search",
                "description": "Busca na memória do ORION por palavras-chave ou filtros",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termo de busca"},
                        "domain": {"type": "string", "description": "Domínio para filtrar"},
                        "agent": {"type": "string", "description": "Agente para filtrar"}
                    },
                    "required": []
                }
            },
            {
                "name": "orion_memory_create",
                "description": "Cria uma nova entrada na memória do ORION",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Título da entrada"},
                        "content": {"type": "string", "description": "Conteúdo da entrada"},
                        "domain": {"type": "string", "description": "Domínio da entrada"},
                        "priority": {"type": "string", "description": "Prioridade (baixo, normal, alto, critico)"}
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "orion_agents_status",
                "description": "Retorna o status de todos os agentes do ORION",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_knowledge_graph",
                "description": "Consulta o grafo de conhecimento do ORION",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Consulta sobre o grafo"},
                        "node_type": {"type": "string", "description": "Tipo de nó para filtrar"}
                    },
                    "required": []
                }
            },
            {
                "name": "orion_rag_search",
                "description": "Busca semântica nos documentos do ORION usando RAG",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Pergunta para buscar"},
                        "top_k": {"type": "number", "description": "Número de resultados"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "orion_rag_add",
                "description": "Adiciona um documento ao sistema RAG do ORION",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Conteúdo do documento"},
                        "source": {"type": "string", "description": "Fonte do documento"},
                        "metadata": {"type": "object", "description": "Metadados adicionais"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "orion_execute_code",
                "description": "Executa código Python de forma segura no ORION",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Código Python para executar"}
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "orion_web_search",
                "description": "Busca conteúdo na web usando o sistema de scraping do ORION",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL para buscar"},
                        "extract_links": {"type": "boolean", "description": "Extrair links"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "orion_goals_list",
                "description": "Lista todos os objetivos e tarefas do ORION",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_health_check",
                "description": "Verifica a saúde de todos os sistemas do ORION",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_reasoning_execute",
                "description": "Executa raciocínio avançado com padrões ReAct, Reflexion, Plan-and-Execute ou Tree of Thoughts",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Tarefa para resolver"},
                        "pattern": {"type": "string", "description": "Padrão de raciocínio (react, reflexion, plan_execute, tree_of_thoughts)", "enum": ["react", "reflexion", "plan_execute", "tree_of_thoughts"]}
                    },
                    "required": ["task"]
                }
            },
            {
                "name": "orion_guardrails_scan",
                "description": "Verifica conteúdo contra ameaças de segurança (prompt injection, PII, toxicidade, segredos)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Conteúdo para verificar"},
                        "type": {"type": "string", "description": "Tipo de verificação (input ou output)", "enum": ["input", "output"]}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "orion_model_route",
                "description": "Roteia tarefa para o modelo mais adequado baseado em complexidade e custo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Descrição da tarefa"},
                        "provider": {"type": "string", "description": "Proveedor preferido (openai, anthropic)"},
                        "max_cost": {"type": "number", "description": "Custo máximo por milhão de tokens"}
                    },
                    "required": ["task"]
                }
            },
            {
                "name": "orion_hitl_check",
                "description": "Verifica se uma ação requer aprovação humana",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Nome da ferramenta"},
                        "parameters": {"type": "object", "description": "Parâmetros da ação"},
                        "confidence": {"type": "number", "description": "Confiança do agente (0-1)"}
                    },
                    "required": ["tool_name"]
                }
            },
            {
                "name": "orion_context_compress",
                "description": "Comprime contexto de conversa para economizar tokens",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "messages": {"type": "array", "description": "Mensagens para comprimir"},
                        "strategy": {"type": "string", "description": "Estratégia de compressão", "enum": ["truncate", "sliding_window", "importance_based", "summarize"]}
                    },
                    "required": ["messages"]
                }
            },
            {
                "name": "orion_observability_dashboard",
                "description": "Retorna dashboard de observabilidade do ORION",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_tiered_memory_add",
                "description": "Adiciona memória ao sistema tiered (working, episodic, semantic, procedural)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Conteúdo da memória"},
                        "tier": {"type": "string", "description": "Nível da memória", "enum": ["working", "episodic", "semantic", "procedural"]},
                        "memory_type": {"type": "string", "description": "Tipo da memória", "enum": ["fact", "preference", "event", "skill", "relationship", "temporal"]},
                        "agent_id": {"type": "string", "description": "ID do agente"},
                        "confidence": {"type": "number", "description": "Confiança (0-1)"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "orion_tiered_memory_recall",
                "description": "Recupera memórias do sistema tiered por similaridade",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Consulta para busca"},
                        "tier": {"type": "string", "description": "Filtrar por nível", "enum": ["working", "episodic", "semantic", "procedural"]},
                        "limit": {"type": "number", "description": "Limite de resultados"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "orion_tiered_memory_stats",
                "description": "Retorna estatísticas do sistema tiered de memória",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_kg_advanced_add_entity",
                "description": "Adiciona entidade ao grafo de conhecimento avançado",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nome da entidade"},
                        "entity_type": {"type": "string", "description": "Tipo da entidade", "enum": ["concept", "person", "organization", "technology", "project", "event", "location", "document", "skill", "agent"]},
                        "description": {"type": "string", "description": "Descrição da entidade"},
                        "properties": {"type": "object", "description": "Propriedades adicionais"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "orion_kg_advanced_add_relation",
                "description": "Adiciona relação entre entidades no grafo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source_name": {"type": "string", "description": "Nome da entidade origem"},
                        "target_name": {"type": "string", "description": "Nome da entidade destino"},
                        "relation_type": {"type": "string", "description": "Tipo da relação", "enum": ["uses", "implements", "depends_on", "related_to", "created_by", "part_of", "caused_by", "temporal", "semantic", "structural"]},
                        "weight": {"type": "number", "description": "Peso da relação"}
                    },
                    "required": ["source_name", "target_name"]
                }
            },
            {
                "name": "orion_kg_advanced_search",
                "description": "Busca entidades no grafo de conhecimento avançado",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termo de busca"},
                        "entity_type": {"type": "string", "description": "Filtrar por tipo"},
                        "limit": {"type": "number", "description": "Limite de resultados"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "orion_kg_advanced_stats",
                "description": "Retorna estatísticas do grafo de conhecimento avançado",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_security_scan_input",
                "description": "Escaneia input através das 7 camadas de segurança",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Conteúdo para escanear"},
                        "agent_id": {"type": "string", "description": "ID do agente"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "orion_security_scan_output",
                "description": "Escaneia output através das 7 camadas de segurança",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Conteúdo para escanear"},
                        "agent_id": {"type": "string", "description": "ID do agente"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "orion_security_dashboard",
                "description": "Retorna dashboard de segurança do ORION",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_security_events",
                "description": "Retorna eventos de segurança recentes",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "hours": {"type": "number", "description": "Últimas N horas"},
                        "severity": {"type": "string", "description": "Filtrar por severidade", "enum": ["low", "medium", "high", "critical"]}
                    },
                    "required": []
                }
            },
            {
                "name": "orion_workflow_execute",
                "description": "Executa um workflow do ORION",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "ID do workflow"},
                        "initial_state": {"type": "object", "description": "Estado inicial"}
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "orion_workflow_list",
                "description": "Lista workflows registrados",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_self_healing_status",
                "description": "Retorna status de auto-cura dos componentes",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_self_healing_stats",
                "description": "Retorna estatísticas do sistema de auto-cura",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_plugins_list",
                "description": "Lista plugins do ORION",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_evaluator_stats",
                "description": "Retorna estatísticas de avaliação",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "orion_task_queue",
                "description": "Enfileira uma tarefa para execução (persiste entre desligamentos)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nome da tarefa"},
                        "handler": {"type": "string", "description": "Handler: health_check, memory_consolidation, knowledge_graph_sync, security_scan, data_cleanup, python:<code>"},
                        "payload": {"type": "object", "description": "Dados da tarefa"},
                        "run_at": {"type": "number", "description": "Timestamp Unix para executar (opcional)"},
                        "recurrence": {"type": "string", "description": "none, once, daily, hourly, weekly, minutes", "enum": ["none", "once", "daily", "hourly", "weekly", "minutes"]},
                        "recurrence_minutes": {"type": "number", "description": "Intervalo em minutos para recurrence=minutes"},
                        "max_recurrences": {"type": "number", "description": "Máximo de recorrências (-1 = infinito)"},
                        "priority": {"type": "string", "description": "low, normal, high, critical", "enum": ["low", "normal", "high", "critical"]},
                        "wake_computer": {"type": "boolean", "description": "Criar tarefa Windows para acordar o computador"}
                    },
                    "required": ["name", "handler"]
                }
            },
            {
                "name": "orion_task_list",
                "description": "Lista tarefas enfileiradas",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Filtrar por status", "enum": ["pending", "running", "completed", "failed", "cancelled", "paused"]}
                    }
                }
            },
            {
                "name": "orion_task_cancel",
                "description": "Cancela uma tarefa enfileirada",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID da tarefa"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "orion_task_history",
                "description": "Histórico de tarefas executadas",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "number", "description": "Número de resultados"}
                    }
                }
            },
            {
                "name": "orion_task_stats",
                "description": "Estatísticas do scheduler de tarefas",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        
        tools.extend(additional_tools)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }
    
    def handle_tools_call(self, request_id, params):
        """Executa uma ferramenta"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "orion_memory_search":
                return self._handle_memory_search(request_id, arguments)
            elif tool_name == "orion_memory_create":
                return self._handle_memory_create(request_id, arguments)
            elif tool_name == "orion_agents_status":
                return self._handle_agents_status(request_id)
            elif tool_name == "orion_knowledge_graph":
                return self._handle_knowledge_graph(request_id, arguments)
            elif tool_name == "orion_rag_search":
                return self._handle_rag_search(request_id, arguments)
            elif tool_name == "orion_rag_add":
                return self._handle_rag_add(request_id, arguments)
            elif tool_name == "orion_execute_code":
                return self._handle_execute_code(request_id, arguments)
            elif tool_name == "orion_web_search":
                return self._handle_web_search(request_id, arguments)
            elif tool_name == "orion_goals_list":
                return self._handle_goals_list(request_id)
            elif tool_name == "orion_health_check":
                return self._handle_health_check(request_id)
            elif tool_name == "orion_reasoning_execute":
                return self._handle_reasoning_execute(request_id, arguments)
            elif tool_name == "orion_guardrails_scan":
                return self._handle_guardrails_scan(request_id, arguments)
            elif tool_name == "orion_model_route":
                return self._handle_model_route(request_id, arguments)
            elif tool_name == "orion_hitl_check":
                return self._handle_hitl_check(request_id, arguments)
            elif tool_name == "orion_context_compress":
                return self._handle_context_compress(request_id, arguments)
            elif tool_name == "orion_observability_dashboard":
                return self._handle_observability_dashboard(request_id)
            elif tool_name == "orion_tiered_memory_add":
                return self._handle_tiered_memory_add(request_id, arguments)
            elif tool_name == "orion_tiered_memory_recall":
                return self._handle_tiered_memory_recall(request_id, arguments)
            elif tool_name == "orion_tiered_memory_stats":
                return self._handle_tiered_memory_stats(request_id)
            elif tool_name == "orion_kg_advanced_add_entity":
                return self._handle_kg_advanced_add_entity(request_id, arguments)
            elif tool_name == "orion_kg_advanced_add_relation":
                return self._handle_kg_advanced_add_relation(request_id, arguments)
            elif tool_name == "orion_kg_advanced_search":
                return self._handle_kg_advanced_search(request_id, arguments)
            elif tool_name == "orion_kg_advanced_stats":
                return self._handle_kg_advanced_stats(request_id)
            elif tool_name == "orion_security_scan_input":
                return self._handle_security_scan_input(request_id, arguments)
            elif tool_name == "orion_security_scan_output":
                return self._handle_security_scan_output(request_id, arguments)
            elif tool_name == "orion_security_dashboard":
                return self._handle_security_dashboard(request_id)
            elif tool_name == "orion_security_events":
                return self._handle_security_events(request_id, arguments)
            elif tool_name == "orion_workflow_execute":
                return self._handle_workflow_execute(request_id, arguments)
            elif tool_name == "orion_workflow_list":
                return self._handle_workflow_list(request_id)
            elif tool_name == "orion_self_healing_status":
                return self._handle_self_healing_status(request_id)
            elif tool_name == "orion_self_healing_stats":
                return self._handle_self_healing_stats(request_id)
            elif tool_name == "orion_plugins_list":
                return self._handle_plugins_list(request_id)
            elif tool_name == "orion_evaluator_stats":
                return self._handle_evaluator_stats(request_id)
            elif tool_name == "orion_task_queue":
                return self._handle_task_queue(request_id, arguments)
            elif tool_name == "orion_task_list":
                return self._handle_task_list(request_id, arguments)
            elif tool_name == "orion_task_cancel":
                return self._handle_task_cancel(request_id, arguments)
            elif tool_name == "orion_task_history":
                return self._handle_task_history(request_id, arguments)
            elif tool_name == "orion_task_stats":
                return self._handle_task_stats(request_id)
            else:
                return self.error_response(request_id, -32602, f"Ferramenta não encontrada: {tool_name}")
        except Exception as e:
            return self.error_response(request_id, -32603, f"Erro ao executar {tool_name}: {str(e)}")
    
    def _handle_memory_search(self, request_id, args):
        """Busca na memória"""
        query = args.get("query", "")
        filters = {}
        if args.get("domain"):
            filters["domain"] = args["domain"]
        if args.get("agent"):
            filters["agent"] = args["agent"]
        
        entries = self.daemon.memory.search(filters) if filters else self.daemon.memory.list_entries()
        
        if query:
            entries = [e for e in entries if query.lower() in e.content.lower() or query.lower() in e.title.lower()]
        
        results = []
        for entry in entries[:10]:
            results.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content[:500],
                "tags": entry.tags,
                "created_at": entry.created_at
            })
        
        return self.success_response(request_id, {
            "found": len(results),
            "entries": results
        })
    
    def _handle_memory_create(self, request_id, args):
        """Cria entrada na memória"""
        entry = self.daemon.memory.create_entry(
            title=args["title"],
            content=args["content"],
            tags={
                "domain": args.get("domain", "user"),
                "priority": args.get("priority", "normal"),
                "freshness": "today"
            },
            source="claude_desktop"
        )
        
        return self.success_response(request_id, {
            "id": entry.id,
            "message": "Entrada criada com sucesso"
        })
    
    def _handle_agents_status(self, request_id):
        """Status dos agentes"""
        agents = {
            "dragao": {"name": "Dragão", "role": "Estratégico Crítico"},
            "elias": {"name": "Elias", "role": "Pesquisador Profundo"},
            "pesquisador": {"name": "Pesquisador", "role": "Validador de Fontes"},
            "estratega": {"name": "Estratega", "role": "Orquestrador"},
            "documentalista": {"name": "Documentalista", "role": "Arquivista"}
        }
        
        return self.success_response(request_id, {"agents": agents})
    
    def _handle_knowledge_graph(self, request_id, args):
        """Consulta grafo de conhecimento"""
        query = args.get("query", "")
        node_type = args.get("node_type")
        
        nodes = list(self.daemon.knowledge_graph._nodes.values())
        
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        
        if query:
            nodes = [n for n in nodes if query.lower() in n.label.lower()]
        
        results = [{"id": n.id, "label": n.label, "type": n.node_type} for n in nodes[:20]]
        
        return self.success_response(request_id, {
            "found": len(results),
            "nodes": results
        })
    
    def _handle_rag_search(self, request_id, args):
        """Busca RAG"""
        query = args["query"]
        top_k = args.get("top_k", 5)
        
        results = self.daemon.rag_system.search(query, top_k)
        
        formatted = []
        for r in results:
            formatted.append({
                "content": r.chunk.content,
                "score": r.score,
                "rank": r.rank
            })
        
        return self.success_response(request_id, {
            "query": query,
            "results": formatted
        })
    
    def _handle_rag_add(self, request_id, args):
        """Adiciona documento ao RAG"""
        doc = self.daemon.rag_system.add_document(
            content=args["content"],
            source=args.get("source", ""),
            metadata=args.get("metadata", {})
        )
        
        return self.success_response(request_id, {
            "doc_id": doc.doc_id,
            "message": "Documento adicionado ao RAG"
        })
    
    def _handle_execute_code(self, request_id, args):
        """Executa código"""
        result = self.daemon.code_executor.execute(args["code"])
        
        return self.success_response(request_id, {
            "status": result.status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "duration_ms": result.duration_ms
        })
    
    def _handle_web_search(self, request_id, args):
        """Busca web"""
        result = self.daemon.web_scraping.fetch_page(args["url"])
        
        if result.page:
            return self.success_response(request_id, {
                "url": result.url,
                "title": result.page.title,
                "content": result.page.content[:2000],
                "links": result.page.links[:20]
            })
        else:
            return self.success_response(request_id, {
                "url": result.url,
                "error": result.error
            })
    
    def _handle_goals_list(self, request_id):
        """Lista objetivos"""
        goals = self.daemon.goal_planner._goals
        tasks = self.daemon.goal_planner._tasks
        
        return self.success_response(request_id, {
            "goals": {gid: g.to_dict() for gid, g in goals.items()},
            "tasks": {tid: t.to_dict() for tid, t in tasks.items()}
        })
    
    def _handle_health_check(self, request_id):
        """Verificação de saúde"""
        health = {
            "memory": "ok",
            "knowledge_graph": "ok",
            "rag_system": "ok",
            "agents": "ok",
            "total_entries": len(self.daemon.memory.list_entries())
        }
        
        return self.success_response(request_id, health)
    
    def _handle_reasoning_execute(self, request_id, args):
        """Executa raciocínio avançado"""
        from orion.reasoning_engine import ReasoningPattern
        
        task = args.get("task", "")
        pattern_str = args.get("pattern", "react")
        
        try:
            pattern = ReasoningPattern(pattern_str)
        except ValueError:
            pattern = ReasoningPattern.REACT
        
        result = self.daemon.reasoning_engine.reason(task, pattern)
        
        return self.success_response(request_id, {
            "pattern": result.pattern.value,
            "answer": result.answer,
            "confidence": result.confidence,
            "steps": len(result.steps),
            "duration_ms": result.total_duration_ms
        })
    
    def _handle_guardrails_scan(self, request_id, args):
        """Verifica conteúdo contra ameaças"""
        content = args.get("content", "")
        scan_type = args.get("type", "input")
        
        if scan_type == "output":
            result = self.daemon.guardrails.scan_output(content)
        else:
            result = self.daemon.guardrails.scan_input(content)
        
        return self.success_response(request_id, {
            "allowed": result.allowed,
            "risk_level": result.risk_level.value,
            "message": result.message,
            "scans": [{"scanner": s.scanner, "result": s.result.value, "message": s.message} for s in result.scans],
            "duration_ms": result.duration_ms
        })
    
    def _handle_model_route(self, request_id, args):
        """Roteia para modelo adequado"""
        task = args.get("task", "")
        
        decision = self.daemon.model_router.route(
            task,
            provider=args.get("provider"),
            require_tools=args.get("require_tools", False),
            require_vision=args.get("require_vision", False),
            max_cost=args.get("max_cost")
        )
        
        return self.success_response(request_id, {
            "model_id": decision.model_id,
            "reason": decision.reason,
            "complexity": decision.complexity.value,
            "estimated_cost": decision.estimated_cost,
            "alternatives": decision.alternatives,
            "confidence": decision.confidence
        })
    
    def _handle_hitl_check(self, request_id, args):
        """Verifica se ação requer aprovação"""
        tool_name = args.get("tool_name", "")
        parameters = args.get("parameters", {})
        confidence = args.get("confidence", 0.8)
        
        needs_approval, request_id_new = self.daemon.human_in_the_loop.check_action(
            agent_id="mcp_user",
            tool_name=tool_name,
            parameters=parameters,
            confidence=confidence
        )
        
        return self.success_response(request_id, {
            "needs_approval": needs_approval,
            "request_id": request_id_new,
            "message": "Ação requer aprovação humana" if needs_approval else "Ação permitida"
        })
    
    def _handle_context_compress(self, request_id, args):
        """Comprime contexto"""
        from orion.context_manager import CompressionStrategy
        
        messages = args.get("messages", [])
        strategy_str = args.get("strategy", "importance_based")
        
        try:
            strategy = CompressionStrategy(strategy_str)
        except ValueError:
            strategy = CompressionStrategy.IMPORTANCE_BASED
        
        result = self.daemon.context_manager.compressor.compress(messages, strategy=strategy)
        
        return self.success_response(request_id, {
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_ratio": result.compression_ratio,
            "strategy": result.strategy.value,
            "kept_messages": len(result.kept_messages)
        })
    
    def _handle_observability_dashboard(self, request_id):
        """Dashboard de observabilidade"""
        dashboard = self.daemon.observability_advanced.get_dashboard()
        
        return self.success_response(request_id, dashboard)
    
    def _handle_tiered_memory_add(self, request_id, args):
        """Adiciona memória ao sistema tiered"""
        from orion.tiered_memory import MemoryTier, MemoryType, get_tiered_memory
        
        content = args.get("content", "")
        tier_str = args.get("tier", "semantic")
        type_str = args.get("memory_type", "fact")
        agent_id = args.get("agent_id", "system")
        confidence = args.get("confidence", 1.0)
        
        try:
            tier = MemoryTier(tier_str)
        except ValueError:
            tier = MemoryTier.SEMANTIC
        
        try:
            memory_type = MemoryType(type_str)
        except ValueError:
            memory_type = MemoryType.FACT
        
        memory_system = get_tiered_memory()
        item = memory_system.add_memory(
            content=content,
            memory_type=memory_type,
            tier=tier,
            agent_id=agent_id,
            confidence=confidence
        )
        
        return self.success_response(request_id, {
            "id": item.id,
            "tier": item.tier.value,
            "memory_type": item.memory_type.value,
            "message": "Memória adicionada com sucesso"
        })
    
    def _handle_tiered_memory_recall(self, request_id, args):
        """Recupera memórias do sistema tiered"""
        from orion.tiered_memory import MemoryTier, get_tiered_memory
        
        query = args.get("query", "")
        tier_str = args.get("tier")
        limit = args.get("limit", 10)
        
        tier = None
        if tier_str:
            try:
                tier = MemoryTier(tier_str)
            except ValueError:
                pass
        
        memory_system = get_tiered_memory()
        results = memory_system.recall(query, tier=tier, limit=limit)
        
        formatted = []
        for item in results:
            formatted.append({
                "id": item.id,
                "content": item.content[:500],
                "tier": item.tier.value,
                "memory_type": item.memory_type.value,
                "confidence": item.confidence,
                "access_count": item.access_count
            })
        
        return self.success_response(request_id, {
            "query": query,
            "found": len(formatted),
            "memories": formatted
        })
    
    def _handle_tiered_memory_stats(self, request_id):
        """Estatísticas do sistema tiered"""
        from orion.tiered_memory import get_tiered_memory
        
        memory_system = get_tiered_memory()
        stats = memory_system.get_memory_stats()
        
        return self.success_response(request_id, stats)
    
    def _handle_kg_advanced_add_entity(self, request_id, args):
        """Adiciona entidade ao grafo avançado"""
        from orion.knowledge_graph_advanced import EntityType, get_knowledge_graph
        
        name = args.get("name", "")
        type_str = args.get("entity_type", "concept")
        description = args.get("description", "")
        properties = args.get("properties", {})
        
        try:
            entity_type = EntityType(type_str)
        except ValueError:
            entity_type = EntityType.CONCEPT
        
        kg = get_knowledge_graph()
        entity = kg.add_entity(
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties
        )
        
        return self.success_response(request_id, {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type.value,
            "message": "Entidade adicionada com sucesso"
        })
    
    def _handle_kg_advanced_add_relation(self, request_id, args):
        """Adiciona relação ao grafo avançado"""
        from orion.knowledge_graph_advanced import RelationType, get_knowledge_graph
        
        source_name = args.get("source_name", "")
        target_name = args.get("target_name", "")
        relation_str = args.get("relation_type", "related_to")
        weight = args.get("weight", 1.0)
        
        try:
            relation_type = RelationType(relation_str)
        except ValueError:
            relation_type = RelationType.RELATED_TO
        
        kg = get_knowledge_graph()
        
        # Find entities by name
        source = kg.get_entity_by_name(source_name)
        target = kg.get_entity_by_name(target_name)
        
        if not source or not target:
            return self.error_response(request_id, -32602, f"Entidade não encontrada: {source_name if not source else target_name}")
        
        relation = kg.add_relation(
            source_id=source.id,
            target_id=target.id,
            relation_type=relation_type,
            weight=weight
        )
        
        if relation:
            return self.success_response(request_id, {
                "id": relation.id,
                "source": source_name,
                "target": target_name,
                "relation_type": relation.relation_type.value,
                "message": "Relação adicionada com sucesso"
            })
        else:
            return self.error_response(request_id, -32603, "Erro ao adicionar relação")
    
    def _handle_kg_advanced_search(self, request_id, args):
        """Busca entidades no grafo avançado"""
        from orion.knowledge_graph_advanced import EntityType, get_knowledge_graph
        
        query = args.get("query", "")
        entity_type_str = args.get("entity_type")
        limit = args.get("limit", 10)
        
        entity_type = None
        if entity_type_str:
            try:
                entity_type = EntityType(entity_type_str)
            except ValueError:
                pass
        
        kg = get_knowledge_graph()
        results = kg.search_entities(query, entity_type=entity_type, limit=limit)
        
        formatted = []
        for entity in results:
            formatted.append({
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type.value,
                "description": entity.description[:200],
                "confidence": entity.confidence
            })
        
        return self.success_response(request_id, {
            "query": query,
            "found": len(formatted),
            "entities": formatted
        })
    
    def _handle_kg_advanced_stats(self, request_id):
        """Estatísticas do grafo avançado"""
        from orion.knowledge_graph_advanced import get_knowledge_graph
        
        kg = get_knowledge_graph()
        stats = kg.get_graph_statistics()
        
        return self.success_response(request_id, stats)
    
    def _handle_security_scan_input(self, request_id, args):
        """Escaneia input through security layers"""
        from orion.security_layers import get_security_system
        
        content = args.get("content", "")
        agent_id = args.get("agent_id", "system")
        
        security = get_security_system()
        sanitized, allowed, events = security.scan_input(content, agent_id)
        
        return self.success_response(request_id, {
            "allowed": allowed,
            "sanitized": sanitized[:500],
            "events_count": len(events),
            "events": [{"threat": e.threat_type.value, "severity": e.severity.value, "action": e.action_taken.value} for e in events]
        })
    
    def _handle_security_scan_output(self, request_id, args):
        """Escaneia output through security layers"""
        from orion.security_layers import get_security_system
        
        content = args.get("content", "")
        agent_id = args.get("agent_id", "system")
        
        security = get_security_system()
        filtered, allowed, events = security.scan_output(content, agent_id)
        
        return self.success_response(request_id, {
            "allowed": allowed,
            "filtered": filtered[:500],
            "events_count": len(events),
            "events": [{"threat": e.threat_type.value, "severity": e.severity.value, "action": e.action_taken.value} for e in events]
        })
    
    def _handle_security_dashboard(self, request_id):
        """Dashboard de segurança"""
        from orion.security_layers import get_security_system
        
        security = get_security_system()
        dashboard = security.get_security_dashboard()
        
        return self.success_response(request_id, dashboard)
    
    def _handle_security_events(self, request_id, args):
        """Eventos de segurança"""
        from orion.security_layers import SecurityLevel, get_security_system
        
        hours = args.get("hours", 24)
        severity_str = args.get("severity")
        
        severity = None
        if severity_str:
            try:
                severity = SecurityLevel(severity_str)
            except ValueError:
                pass
        
        security = get_security_system()
        events = security.get_events(severity=severity, hours=hours)
        
        formatted = []
        for event in events[:50]:
            formatted.append({
                "event_id": event.event_id,
                "threat_type": event.threat_type.value,
                "severity": event.severity.value,
                "action_taken": event.action_taken.value,
                "timestamp": event.timestamp,
                "agent_id": event.agent_id
            })
        
        return self.success_response(request_id, {
            "period_hours": hours,
            "found": len(formatted),
            "events": formatted
        })
    
    def _handle_workflow_execute(self, request_id, args):
        """Executa workflow"""
        workflow_id = args.get("workflow_id", "")
        initial_state = args.get("initial_state", {})
        
        from orion.workflow_engine import get_workflow_engine
        engine = get_workflow_engine()
        
        try:
            exec_id = engine.execute(workflow_id, initial_state)
            return self.success_response(request_id, {
                "execution_id": exec_id,
                "status": "started"
            })
        except Exception as e:
            return self.error_response(request_id, -32603, str(e))
    
    def _handle_workflow_list(self, request_id):
        """Lista workflows"""
        from orion.workflow_engine import get_workflow_engine
        engine = get_workflow_engine()
        workflows = engine.list_workflows()
        
        return self.success_response(request_id, {
            "workflows": workflows
        })
    
    def _handle_self_healing_status(self, request_id):
        """Status de auto-cura"""
        from orion.self_healing import get_self_healing
        healing = get_self_healing()
        
        return self.success_response(request_id, {
            "components": healing.get_all_status(),
            "circuit_breakers": healing.get_circuit_breakers()
        })
    
    def _handle_self_healing_stats(self, request_id):
        """Estatísticas de auto-cura"""
        from orion.self_healing import get_self_healing
        healing = get_self_healing()
        
        return self.success_response(request_id, healing.get_statistics())
    
    def _handle_plugins_list(self, request_id):
        """Lista plugins"""
        from orion.plugin_system import get_plugin_manager
        manager = get_plugin_manager()
        
        return self.success_response(request_id, {
            "plugins": manager.list_plugins()
        })
    
    def _handle_evaluator_stats(self, request_id):
        """Estatísticas de avaliação"""
        from orion.evaluation import get_evaluator
        evaluator = get_evaluator()
        
        return self.success_response(request_id, evaluator.get_statistics())
    
    def _handle_task_queue(self, request_id, args):
        """Enfileira tarefa"""
        from orion.task_scheduler import get_task_scheduler, RecurrenceType, TaskPriority
        
        scheduler = get_task_scheduler()
        
        # Parse recurrence
        recurrence_str = args.get("recurrence", "none")
        try:
            recurrence = RecurrenceType(recurrence_str)
        except ValueError:
            recurrence = RecurrenceType.NONE
        
        # Parse priority
        priority_str = args.get("priority", "normal")
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.NORMAL
        
        task = scheduler.queue_task(
            name=args.get("name", "Unnamed Task"),
            handler=args.get("handler", ""),
            payload=args.get("payload", {}),
            run_at=args.get("run_at"),
            recurrence=recurrence,
            recurrence_minutes=args.get("recurrence_minutes", 60),
            max_recurrences=args.get("max_recurrences", -1),
            priority=priority,
            description=args.get("description", ""),
            wake_computer=args.get("wake_computer", False)
        )
        
        return self.success_response(request_id, {
            "task_id": task.id,
            "name": task.name,
            "status": task.status.value,
            "message": "Tarefa enfileirada com sucesso"
        })
    
    def _handle_task_list(self, request_id, args):
        """Lista tarefas"""
        from orion.task_scheduler import get_task_scheduler, TaskStatus
        
        scheduler = get_task_scheduler()
        status_str = args.get("status")
        
        status = None
        if status_str:
            try:
                status = TaskStatus(status_str)
            except ValueError:
                pass
        
        tasks = scheduler.list_tasks(status=status)
        
        return self.success_response(request_id, {
            "found": len(tasks),
            "tasks": tasks
        })
    
    def _handle_task_cancel(self, request_id, args):
        """Cancela tarefa"""
        from orion.task_scheduler import get_task_scheduler
        
        scheduler = get_task_scheduler()
        task_id = args.get("task_id", "")
        
        success = scheduler.cancel_task(task_id)
        
        return self.success_response(request_id, {
            "task_id": task_id,
            "cancelled": success,
            "message": "Tarefa cancelada" if success else "Tarefa não encontrada"
        })
    
    def _handle_task_history(self, request_id, args):
        """Histórico de tarefas"""
        from orion.task_scheduler import get_task_scheduler
        
        scheduler = get_task_scheduler()
        limit = args.get("limit", 20)
        
        history = scheduler.get_history(limit=limit)
        
        return self.success_response(request_id, {
            "found": len(history),
            "history": history
        })
    
    def _handle_task_stats(self, request_id):
        """Estatísticas do scheduler"""
        from orion.task_scheduler import get_task_scheduler
        
        scheduler = get_task_scheduler()
        
        return self.success_response(request_id, scheduler.get_statistics())
    
    def handle_resources_list(self, request_id):
        """Lista recursos"""
        resources = [
            {
                "uri": "orion://memory",
                "name": "Memória ORION",
                "description": "Acesso à memória do ORION",
                "mimeType": "application/json"
            },
            {
                "uri": "orion://agents",
                "name": "Agentes ORION",
                "description": "Status dos agentes",
                "mimeType": "application/json"
            },
            {
                "uri": "orion://knowledge-graph",
                "name": "Grafo de Conhecimento",
                "description": "Grafo de conhecimento do ORION",
                "mimeType": "application/json"
            },
            {
                "uri": "orion://goals",
                "name": "Objetivos",
                "description": "Objetivos e tarefas do ORION",
                "mimeType": "application/json"
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"resources": resources}
        }
    
    def handle_resources_read(self, request_id, params):
        """Lê um recurso"""
        uri = params.get("uri", "")
        
        if uri == "orion://memory":
            entries = self.daemon.memory.list_entries()[-20:]
            data = [{"title": e.title, "content": e.content[:200]} for e in entries]
            return self.success_response(request_id, data)
        elif uri == "orion://agents":
            return self._handle_agents_status(request_id)
        elif uri == "orion://knowledge-graph":
            nodes = [{"label": n.label, "type": n.node_type} for n in list(self.daemon.knowledge_graph._nodes.values())[:20]]
            return self.success_response(request_id, nodes)
        elif uri == "orion://goals":
            return self._handle_goals_list(request_id)
        else:
            return self.error_response(request_id, -32602, f"Recurso não encontrado: {uri}")
    
    def handle_prompts_list(self, request_id):
        """Lista prompts"""
        prompts = [
            {
                "name": "orion_research",
                "description": "Prompt para pesquisa aprofundada",
                "arguments": [
                    {"name": "topic", "description": "Tópico para pesquisar", "required": True}
                ]
            },
            {
                "name": "orion_analyze",
                "description": "Prompt para análise de dados",
                "arguments": [
                    {"name": "data", "description": "Dados para analisar", "required": True}
                ]
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"prompts": prompts}
        }
    
    def handle_prompts_get(self, request_id, params):
        """Obtém um prompt"""
        name = params.get("name")
        args = params.get("arguments", {})
        
        if name == "orion_research":
            topic = args.get("topic", "geral")
            prompt = f"""Pesquisa aprofundada sobre: {topic}

Use o ORION para:
1. Buscar na memória por informações relacionadas
2. Consultar o grafo de conhecimento
3. Pesquisar na web se necessário
4. Sintetizar os achados
5. Criar uma entrada na memória com o resumo"""
            
            return self.success_response(request_id, {
                "description": f"Pesquisa sobre {topic}",
                "messages": [{"role": "user", "content": prompt}]
            })
        elif name == "orion_analyze":
            data = args.get("data", "")
            prompt = f"""Analise os seguintes dados usando o ORION:

{data}

Forneça:
1. Resumo dos dados
2. Padrões identificados
3. Insights principais
4. Recomendações"""
            
            return self.success_response(request_id, {
                "description": "Análise de dados",
                "messages": [{"role": "user", "content": prompt}]
            })
        else:
            return self.error_response(request_id, -32602, f"Prompt não encontrado: {name}")
    
    def success_response(self, request_id, result):
        """Cria resposta de sucesso"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
            }
        }
    
    def error_response(self, request_id, code, message):
        """Cria resposta de erro"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }
    
    def run(self):
        """Executa o servidor MCP via stdin/stdout"""
        logger.info("Servidor MCP iniciado. Aguardando mensagens...")
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response:
                    self.send_response(response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON inválido: {e}")
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                })
            except Exception as e:
                logger.error(f"Erro: {e}")


def main():
    """Ponto de entrada principal"""
    server = ORIONMCPServer()
    server.run()


if __name__ == "__main__":
    main()
