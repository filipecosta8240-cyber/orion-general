from __future__ import annotations

import json
import logging
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .daemon import ORIONDaemon
from .reasoning_engine import ReasoningPattern

WEB_ROOT = Path(__file__).resolve().parents[1]
API_PREFIX = "/api"
logger = logging.getLogger("orion.server")

class ORIONRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: Optional[str] = None, orion: Optional[ORIONDaemon] = None, **kwargs: Any) -> None:
        self.orion = orion
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("Request: %s", format % args)

    def do_GET(self) -> None:
        logger.info("GET %s", self.path)
        parsed = urlparse(self.path)
        if parsed.path.startswith(API_PREFIX):
            self.handle_api_get(parsed)
            return
        super().do_GET()

    def do_POST(self) -> None:
        logger.info("POST %s", self.path)
        parsed = urlparse(self.path)
        if parsed.path == f"{API_PREFIX}/log":
            self.handle_log_post()
            return
        if parsed.path == f"{API_PREFIX}/proposals/create":
            self.handle_create_proposal()
            return
        if parsed.path == f"{API_PREFIX}/proposals/approve":
            self.handle_proposal_approve()
            return
        if parsed.path == f"{API_PREFIX}/proposals/decline":
            self.handle_proposal_decline()
            return
        if parsed.path == f"{API_PREFIX}/rag/add":
            self.handle_rag_add()
            return
        if parsed.path == f"{API_PREFIX}/code/execute":
            self.handle_code_execute()
            return
        if parsed.path == f"{API_PREFIX}/webhooks/register":
            self.handle_webhook_register()
            return
        
        # POST handlers para Ronda 6
        if parsed.path == f"{API_PREFIX}/reasoning/execute":
            self.handle_reasoning_execute()
            return
        if parsed.path == f"{API_PREFIX}/guardrails/scan":
            self.handle_guardrails_scan()
            return
        if parsed.path == f"{API_PREFIX}/router/route":
            self.handle_model_route()
            return
        if parsed.path == f"{API_PREFIX}/hitl/approve":
            self.handle_hitl_approve()
            return
        if parsed.path == f"{API_PREFIX}/hitl/reject":
            self.handle_hitl_reject()
            return
        
        self.send_error(404, "Not found")

    def handle_api_get(self, parsed) -> None:
        logger.debug("API GET %s", parsed.path)
        if parsed.path == f"{API_PREFIX}/status":
            self.respond_json({"status": "ok", "entries": len(self.orion.memory.list_entries())})
            return

        if parsed.path == f"{API_PREFIX}/memory":
            self.respond_json(self.format_entries(self.orion.memory.list_entries()))
            return

        if parsed.path == f"{API_PREFIX}/tools":
            tools = [tool.metadata().__dict__ for tool in self.orion.tool_registry.tools.values()]
            self.respond_json(tools)
            return

        if parsed.path == f"{API_PREFIX}/proposals":
            proposals = [proposal.to_dict() for proposal in self.orion.self_evolution.list_proposals()]
            self.respond_json(proposals)
            return

        if parsed.path == f"{API_PREFIX}/memory/search":
            parameters = parse_qs(parsed.query)
            filters = {
                key: parameters[key][0]
                for key in ("agent", "domain", "priority", "freshness")
                if key in parameters and parameters[key]
            }
            entries = self.orion.memory.search(filters) if filters else self.orion.memory.list_entries()
            self.respond_json(self.format_entries(entries))
            return

        if parsed.path == f"{API_PREFIX}/suggestions":
            self.respond_json(self.create_suggestion())
            return

        if parsed.path == f"{API_PREFIX}/mcp/capabilities":
            self.respond_json(self.orion.mcp_server.to_mcp_capabilities())
            return

        if parsed.path == f"{API_PREFIX}/events/statistics":
            self.respond_json(self.orion.event_bus.get_statistics())
            return

        if parsed.path == f"{API_PREFIX}/events/history":
            limit = parse_qs(parsed.query).get("limit", ["50"])[0]
            events = self.orion.event_bus.get_history(limit=int(limit))
            self.respond_json([event.to_dict() for event in events])
            return

        if parsed.path == f"{API_PREFIX}/skills/status":
            skills = self.orion.skills_engine.list_skills()
            self.respond_json({
                "total_skills": len(skills),
                "skills": [skill.to_dict() for skill in skills],
                "recommendations": self.orion.skills_engine.get_skill_recommendations()
            })
            return

        if parsed.path == f"{API_PREFIX}/orchestrator/status":
            self.respond_json({
                "agents": self.orion.orchestrator.get_all_agents_status(),
                "workflows": {wid: self.orion.orchestrator.get_workflow_status(wid) for wid in self.orion.orchestrator.workflows}
            })
            return

        if parsed.path == f"{API_PREFIX}/memory/cache-stats":
            self.respond_json(self.orion.memory_manager.get_cache_statistics())
            return

        # 8 Novos endpoints para sistemas avan\u00e7ados
        
        # State Machine
        if parsed.path == f"{API_PREFIX}/state-machine/status":
            self.respond_json(self.orion.state_machine_manager.get_system_state_summary())
            return
        
        if parsed.path == f"{API_PREFIX}/state-machine/all-stats":
            self.respond_json(self.orion.state_machine_manager.get_all_statistics())
            return
        
        # Reputation
        if parsed.path == f"{API_PREFIX}/reputation/status":
            self.respond_json(self.orion.reputation_engine.get_all_statistics())
            return
        
        if parsed.path == f"{API_PREFIX}/reputation/ranking":
            self.respond_json({"ranking": self.orion.reputation_engine.get_agent_ranking()})
            return
        
        # Health Monitoring
        if parsed.path == f"{API_PREFIX}/health/status":
            self.respond_json(self.orion.health_monitor.get_system_health_summary())
            return
        
        # Consensus Engine
        if parsed.path == f"{API_PREFIX}/consensus/history":
            self.respond_json(self.orion.consensus_engine.get_consensus_history())
            return
        
        # Conflict Resolution
        if parsed.path == f"{API_PREFIX}/conflicts/statistics":
            self.respond_json(self.orion.conflict_resolver.get_conflict_statistics())
            return
        
        # Negotiation Protocol
        if parsed.path == f"{API_PREFIX}/negotiations/statistics":
            self.respond_json(self.orion.negotiation_protocol.get_negotiation_statistics())
            return
        
        # Social Dynamics
        if parsed.path == f"{API_PREFIX}/social/network":
            self.respond_json(self.orion.social_dynamics.get_social_network_status())
            return
        
        # Swarm Intelligence
        if parsed.path == f"{API_PREFIX}/swarm/status":
            self.respond_json(self.orion.swarm_intelligence.get_swarm_status())
            return
        
        if parsed.path == f"{API_PREFIX}/swarm/solutions":
            self.respond_json({"emergent_solutions": self.orion.swarm_intelligence.get_emergent_solutions()})
            return
        
        # 4 Novos sistemas avançados (Ronda 4)
        
        # A2A Protocol
        if parsed.path == f"{API_PREFIX}/a2a/status":
            self.respond_json(self.orion.a2a_protocol.get_protocol_status())
            return
        
        if parsed.path == f"{API_PREFIX}/a2a/agents":
            capability = parse_qs(parsed.query).get("capability", [None])[0]
            agents = self.orion.a2a_protocol.discover_agents(capability)
            self.respond_json([a.to_dict() for a in agents])
            return
        
        if parsed.path == f"{API_PREFIX}/a2a/ranking":
            self.respond_json({"ranking": self.orion.a2a_protocol.get_agent_ranking()})
            return
        
        # Checkpointing
        if parsed.path == f"{API_PREFIX}/checkpoints/status":
            self.respond_json(self.orion.checkpoint_manager.get_checkpoint_status())
            return
        
        # Cost Engineering
        if parsed.path == f"{API_PREFIX}/costs/summary":
            days = int(parse_qs(parsed.query).get("days", ["30"])[0])
            self.respond_json(self.orion.cost_engineering.get_system_cost_summary(days))
            return
        
        if parsed.path == f"{API_PREFIX}/costs/agent":
            agent_id = parse_qs(parsed.query).get("agent_id", [""])[0]
            if agent_id:
                self.respond_json(self.orion.cost_engineering.get_agent_cost_summary(agent_id))
            else:
                self.send_error(400, "agent_id required")
            return
        
        if parsed.path == f"{API_PREFIX}/costs/recommendations":
            self.respond_json({"recommendations": self.orion.cost_engineering.get_cost_optimization_recommendations()})
            return
        
        # Observability
        if parsed.path == f"{API_PREFIX}/observability/health":
            self.respond_json(self.orion.observability.get_system_health())
            return
        
        if parsed.path == f"{API_PREFIX}/observability/traces":
            agent_id = parse_qs(parsed.query).get("agent_id", [None])[0]
            if agent_id:
                traces = self.orion.observability.tracing.get_agent_traces(agent_id)
                self.respond_json([t.to_dict() for t in traces])
            else:
                self.respond_json(self.orion.observability.tracing.get_trace_statistics())
            return
        
        if parsed.path == f"{API_PREFIX}/observability/metrics":
            self.respond_json(self.orion.observability.metrics.get_metrics_summary())
            return
        
        if parsed.path == f"{API_PREFIX}/observability/alerts":
            alerts = self.orion.observability.alerts.get_active_alerts()
            self.respond_json([a.to_dict() for a in alerts])
            return
        
        # 5 Novos sistemas (Ronda 5)
        
        # RAG System
        if parsed.path == f"{API_PREFIX}/rag/stats":
            self.respond_json(self.orion.rag_system.get_stats())
            return
        
        if parsed.path == f"{API_PREFIX}/rag/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            if query:
                results = self.orion.rag_system.search(query)
                self.respond_json([r.to_dict() for r in results])
            else:
                self.send_error(400, "Query parameter 'q' required")
            return
        
        # Web Scraping
        if parsed.path == f"{API_PREFIX}/web/stats":
            self.respond_json(self.orion.web_scraping.get_stats())
            return
        
        # Code Execution
        if parsed.path == f"{API_PREFIX}/code/stats":
            self.respond_json(self.orion.code_executor.get_stats())
            return
        
        if parsed.path == f"{API_PREFIX}/code/history":
            history = self.orion.code_executor.get_history()
            self.respond_json([r.to_dict() for r in history])
            return
        
        # Streaming
        if parsed.path == f"{API_PREFIX}/streaming/stats":
            self.respond_json(self.orion.streaming.get_stats())
            return
        
        # Webhooks
        if parsed.path == f"{API_PREFIX}/webhooks":
            webhooks = self.orion.webhook_manager.list_webhooks()
            self.respond_json([w.to_dict() for w in webhooks])
            return
        
        if parsed.path == f"{API_PREFIX}/webhooks/stats":
            self.respond_json(self.orion.webhook_manager.get_stats())
            return
        
        # 6 Novos sistemas avançados (Ronda 6 - 2026 cutting-edge patterns)
        
        # Reasoning Engine
        if parsed.path == f"{API_PREFIX}/reasoning/stats":
            self.respond_json(self.orion.reasoning_engine.get_stats())
            return
        
        if parsed.path == f"{API_PREFIX}/reasoning/patterns":
            self.respond_json({"patterns": [p.value for p in ReasoningPattern]})
            return
        
        # Guardrails
        if parsed.path == f"{API_PREFIX}/guardrails/stats":
            self.respond_json(self.orion.guardrails.get_stats())
            return
        
        if parsed.path == f"{API_PREFIX}/guardrails/audit":
            count = int(parse_qs(parsed.query).get("count", ["100"])[0])
            self.respond_json(self.orion.guardrails.get_audit_trail(count))
            return
        
        # Model Router
        if parsed.path == f"{API_PREFIX}/router/stats":
            self.respond_json(self.orion.model_router.get_stats())
            return
        
        if parsed.path == f"{API_PREFIX}/router/models":
            models = [self.orion.model_router.get_model_info(mid) for mid in self.orion.model_router.models]
            self.respond_json([m for m in models if m])
            return
        
        # Advanced Observability
        if parsed.path == f"{API_PREFIX}/observability/dashboard":
            self.respond_json(self.orion.observability_advanced.get_dashboard())
            return
        
        if parsed.path == f"{API_PREFIX}/observability/traces/recent":
            count = int(parse_qs(parsed.query).get("count", ["10"])[0])
            traces = self.orion.observability_advanced.tracer.get_recent_traces(count)
            self.respond_json([self.orion.observability_advanced.get_trace_summary(t.trace_id) for t in traces])
            return
        
        # Human-in-the-Loop
        if parsed.path == f"{API_PREFIX}/hitl/stats":
            self.respond_json(self.orion.human_in_the_loop.get_stats())
            return
        
        if parsed.path == f"{API_PREFIX}/hitl/pending":
            self.respond_json(self.orion.human_in_the_loop.queue.get_pending())
            return
        
        if parsed.path == f"{API_PREFIX}/hitl/completed":
            count = int(parse_qs(parsed.query).get("count", ["50"])[0])
            self.respond_json(self.orion.human_in_the_loop.queue.get_completed(count))
            return
        
        # Context Manager
        if parsed.path == f"{API_PREFIX}/context/stats":
            self.respond_json(self.orion.context_manager.get_stats())
            return

        self.send_error(404, "API endpoint not found")

    def handle_log_post(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        title = payload.get("title", "ORION Jogo de Leitura")
        content = payload.get("content", "Sem detalhes")
        tags = {
            "agent": payload.get("agent", "DOCUMENTALISTA"),
            "domain": payload.get("domain", "jogo"),
            "priority": payload.get("priority", "normal"),
            "freshness": payload.get("freshness", "today"),
        }
        entry = self.orion.memory.create_entry(title=title, content=content, tags=tags, source="JOGO")
        self.respond_json({"status": "ok", "id": entry.id})

    def handle_create_proposal(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        tool = payload.get("tool")
        objective = payload.get("objective", "")
        context = payload.get("context", "")
        if not tool or not objective:
            self.send_error(400, "tool e objective são obrigatórios")
            return

        proposal = self.orion.self_evolution.generate_proposal_from_tool(tool, objective=objective, context=context)
        self.respond_json({"status": "ok", "proposal": proposal.to_dict()})

    def handle_proposal_approve(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        pid = payload.get("id")
        if not pid:
            self.send_error(400, "id é obrigatório")
            return
        proposal = self.orion.self_evolution.approve_proposal(pid)
        if proposal:
            self.respond_json({"status": "approved", "proposal": proposal.to_dict()})
        else:
            self.send_error(404, "Proposal não encontrada")

    def handle_proposal_decline(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        pid = payload.get("id")
        if not pid:
            self.send_error(400, "id é obrigatório")
            return
        proposal = self.orion.self_evolution.decline_proposal(pid)
        if proposal:
            self.respond_json({"status": "declined", "proposal": proposal.to_dict()})
        else:
            self.send_error(404, "Proposal não encontrada")
    
    def handle_rag_add(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        content = payload.get("content", "")
        source = payload.get("source", "")
        metadata = payload.get("metadata", {})
        
        if not content:
            self.send_error(400, "content é obrigatório")
            return
        
        doc = self.orion.rag_system.add_document(content, metadata, source)
        self.respond_json({"status": "ok", "doc_id": doc.doc_id})
    
    def handle_code_execute(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        code = payload.get("code", "")
        if not code:
            self.send_error(400, "code é obrigatório")
            return
        
        result = self.orion.code_executor.execute(code)
        self.respond_json(result.to_dict())
    
    def handle_webhook_register(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        url = payload.get("url", "")
        events = payload.get("events", [])
        description = payload.get("description", "")
        
        if not url or not events:
            self.send_error(400, "url e events são obrigatórios")
            return
        
        webhook = self.orion.webhook_manager.register_webhook(url, events, description)
        self.respond_json({"status": "ok", "webhook_id": webhook.webhook_id, "secret": webhook.secret})
    
    # POST handlers para Ronda 6
    
    def handle_reasoning_execute(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        task = payload.get("task", "")
        pattern = payload.get("pattern", "react")
        
        if not task:
            self.send_error(400, "task é obrigatório")
            return
        
        try:
            reasoning_pattern = ReasoningPattern(pattern)
        except ValueError:
            reasoning_pattern = ReasoningPattern.REACT
        
        result = self.orion.reasoning_engine.reason(task, reasoning_pattern)
        self.respond_json({
            "pattern": result.pattern.value,
            "answer": result.answer,
            "confidence": result.confidence,
            "steps": len(result.steps),
            "duration_ms": result.total_duration_ms
        })
    
    def handle_guardrails_scan(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        content = payload.get("content", "")
        scan_type = payload.get("type", "input")
        
        if not content:
            self.send_error(400, "content é obrigatório")
            return
        
        if scan_type == "output":
            result = self.orion.guardrails.scan_output(content)
        else:
            result = self.orion.guardrails.scan_input(content)
        
        self.respond_json({
            "allowed": result.allowed,
            "risk_level": result.risk_level.value,
            "message": result.message,
            "scans": [{"scanner": s.scanner, "result": s.result.value, "message": s.message} for s in result.scans],
            "duration_ms": result.duration_ms
        })
    
    def handle_model_route(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        task = payload.get("task", "")
        if not task:
            self.send_error(400, "task é obrigatório")
            return
        
        decision = self.orion.model_router.route(
            task,
            provider=payload.get("provider"),
            require_tools=payload.get("require_tools", False),
            require_vision=payload.get("require_vision", False),
            max_cost=payload.get("max_cost")
        )
        
        self.respond_json({
            "model_id": decision.model_id,
            "reason": decision.reason,
            "complexity": decision.complexity.value,
            "estimated_cost": decision.estimated_cost,
            "alternatives": decision.alternatives,
            "confidence": decision.confidence
        })
    
    def handle_hitl_approve(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        request_id = payload.get("request_id", "")
        reviewer = payload.get("reviewer", "user")
        comment = payload.get("comment", "")
        
        if not request_id:
            self.send_error(400, "request_id é obrigatório")
            return
        
        success = self.orion.human_in_the_loop.approve(request_id, reviewer, comment)
        if success:
            self.respond_json({"status": "approved", "request_id": request_id})
        else:
            self.send_error(404, "Request não encontrada")
    
    def handle_hitl_reject(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return
        
        request_id = payload.get("request_id", "")
        reviewer = payload.get("reviewer", "user")
        comment = payload.get("comment", "")
        
        if not request_id:
            self.send_error(400, "request_id é obrigatório")
            return
        
        success = self.orion.human_in_the_loop.reject(request_id, reviewer, comment)
        if success:
            self.respond_json({"status": "rejected", "request_id": request_id})
        else:
            self.send_error(404, "Request não encontrada")

    def respond_json(self, payload: Any, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def format_entries(self, entries: list) -> list:
        return [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "tags": entry.tags,
                "source": entry.source,
                "created_at": entry.created_at,
                "version": entry.version,
            }
            for entry in sorted(entries, key=lambda item: item.created_at, reverse=True)
        ]

    def create_suggestion(self) -> dict:
        entries = [entry for entry in self.orion.memory.list_entries() if entry.tags.get("domain") == "jogo"]
        if not entries:
            return {
                "recommendation": "Ainda não temos histórico de jogo. Começa com um texto Fácil e registra sua primeira leitura.",
                "average_score": None,
                "recommended_difficulty": "Fácil",
                "reasoning": [
                    "Sem dados de jogo, ORION recomenda começar pela dificuldade mais acessível.",
                ],
                "recent_results": [],
            }

        recent_entries = sorted(entries, key=lambda item: item.created_at, reverse=True)[:6]
        scores = []
        difficulties = []
        for entry in recent_entries:
            score_match = re.search(r"Pontuação:\s*(\d+)", entry.content)
            if score_match:
                scores.append(int(score_match.group(1)))
            difficulty_match = re.search(r"Dificuldade:\s*(Fácil|Médio|Difícil)", entry.content)
            if difficulty_match:
                difficulties.append(difficulty_match.group(1))

        average_score = round(sum(scores) / len(scores), 1) if scores else None
        suggested_difficulty = "Médio"
        reasoning = []

        if average_score is None:
            reasoning.append("Pontos de desempenho não foram extraídos dos resultados anteriores.")
        else:
            reasoning.append(f"Última média de pontuação: {average_score}.")
            if average_score < 60:
                suggested_difficulty = "Fácil"
                reasoning.append("Resultados recentes mostram necessidade de mais prática em textos simples.")
            elif average_score < 85:
                suggested_difficulty = "Médio"
                reasoning.append("Boa base atual; o próximo passo é consolidar com um texto de dificuldade moderada.")
            else:
                suggested_difficulty = "Difícil"
                reasoning.append("Desempenho forte; ORION sugere um texto mais complexo para desafiar a leitura.")

        top_subject = None
        if difficulties:
            most_common = max(set(difficulties), key=difficulties.count)
            top_subject = f"A dificuldade mais frequente recentemente foi {most_common}."
            reasoning.append(top_subject)

        recommendation_text = (
            f"ORION recomenda um texto {suggested_difficulty} para sua próxima prática. "
            "Foca em fluência gradual e confirmação de compreensão."
        )

        return {
            "recommendation": recommendation_text,
            "average_score": average_score,
            "recommended_difficulty": suggested_difficulty,
            "reasoning": reasoning,
            "recent_results": [
                {
                    "title": entry.title,
                    "created_at": entry.created_at,
                    "content": entry.content,
                    "score": int(re.search(r"Pontuação:\s*(\d+)", entry.content).group(1)) if re.search(r"Pontuação:\s*(\d+)", entry.content) else None,
                }
                for entry in recent_entries
            ],
        }


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    orion = ORIONDaemon()
    orion.run_background()
    server_address = (host, port)
    handler = lambda *args, **kwargs: ORIONRequestHandler(*args, directory=str(WEB_ROOT), orion=orion, **kwargs)
    with ThreadingHTTPServer(server_address, handler) as httpd:
        logger.info("Servidor iniciado em http://%s:%s", host, port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Servidor interrompido.")

if __name__ == "__main__":
    run_server()
