from __future__ import annotations

import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from .agents import Documentalista, Dragao, Elias, Estratega, Pesquisador, General
from .memory import ObsidianMemoryBridge
from .scheduler import ORIONProductionScheduler, ScheduledJob
from .self_evolution import SelfEvolutionEngine
from .tools import ORIONToolRegistry
from .events import EventBus, EventType, Event, EventLogger
from .mcp_server import MCPServer
from .evolutionary_skills import EvolutionarySkillsEngine
from .orchestrator import MultiAgentOrchestrator, WorkflowType, WorkflowTask
from .memory_manager import AdvancedMemoryManager
from .agent_state_machine import GlobalStateMachineManager, AgentStateType
from .agent_reputation import AgentReputationEngine, ReputationMetric
from .agent_health_monitor import SystemHealthMonitor
from .consensus_engine import ConsensusEngine, ConsensusStrategy
from .conflict_resolution import ConflictResolver, ConflictType, ResolutionStrategy
from .negotiation_protocol import NegotiationProtocol
from .social_dynamics import SocialDynamicsManager
import logging

...

from .swarm_intelligence import SwarmIntelligenceEngine
from .sleep_processor import SleepTimeProcessor
from .knowledge_graph import KnowledgeGraph, KnowledgeGraphQueryEngine
from .reflection_engine import ReflectionEngine
from .goal_planner import GoalPlanner
from .memory_salience import MemorySalienceEngine
from .backup_system import BackupSystem
from .episodic_memory import EpisodicMemory
from .prospective_memory import ProspectiveMemory
from .memory_guard import MemoryGuard
from .idle_processor import IdleProcessor
from .audit_trail import AuditTrail
from .performance_metrics import PerformanceMetrics
from .data_retention import DataRetentionManager
from .a2a_protocol import A2AProtocol, A2AAgentCard, AgentCapability
from .checkpointing import CheckpointManager
from .cost_engineering import CostEngineeringManager, ModelPricing, ModelTier
from .observability import ObservabilityManager
from .rag_system import RAGSystem
from .web_scraping import WebScrapingSystem
from .code_execution import CodeExecutor
from .streaming import StreamingSystem
from .webhooks import WebhookManager

# Ronda 6 - Novos sistemas avançados (2026 patterns)
from .reasoning_engine import ReasoningEngine, ReasoningPattern
from .guardrails import GuardrailsSystem, PolicyRule, RiskLevel
from .model_router import ModelRouter, ModelConfig, ModelTier
from .observability_advanced import ObservabilitySystem, SpanKind
from .human_in_the_loop import HumanInTheLoop, HITLConfig, ApprovalStatus
from .context_manager import ContextManager, CompressionStrategy

# Ronda 7 - Sistemas avançados (2026 cutting-edge patterns)
from .tiered_memory import TieredMemorySystem, MemoryTier, MemoryType, get_tiered_memory
from .knowledge_graph_advanced import AdvancedKnowledgeGraph, EntityType, RelationType, get_knowledge_graph
from .security_layers import AdvancedSecuritySystem, SecurityLevel, ThreatType, get_security_system
from .embeddings import EmbeddingEngine, get_embedding_engine
from .workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowNode, NodeType, get_workflow_engine
from .evaluation import Evaluator, TestSuite, TestCase, get_evaluator
from .plugin_system import PluginManager, PluginBase, PluginManifest, get_plugin_manager
from .multimodal import MultimodalProcessor, MediaType, get_multimodal
from .self_healing import SelfHealingEngine, get_self_healing
from .federated_memory import FederatedMemoryNode, get_federated_memory
from .task_scheduler import PersistentTaskScheduler, get_task_scheduler, TaskStatus, TaskPriority

logger = logging.getLogger("orion")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT_NAME = _PROJECT_ROOT / "ORION_SYSTEM" / "MEMORIA"

class ORIONDaemon:
    def __init__(self, vault_root: Path = DEFAULT_VAULT_NAME):
        self.memory = ObsidianMemoryBridge(vault_root=vault_root)
        
        # Novos componentes de arquitetura melhorada
        self.event_bus = EventBus()
        self.event_logger = EventLogger(self.memory)
        
        self.scheduler = ORIONProductionScheduler()
        self.dragao = Dragao(self.memory)
        self.elias = Elias(self.memory)
        self.pesquisador = Pesquisador(self.memory)
        self.estratega = Estratega(self.memory)
        self.documentalista = Documentalista(self.memory)
        self.general = General(self.memory)
        self.tool_registry = ORIONToolRegistry(self.memory)
        self.self_evolution = SelfEvolutionEngine(self.memory, self.tool_registry)
        
        # Novos sistemas integrados
        self.mcp_server = MCPServer(self)
        self.skills_engine = EvolutionarySkillsEngine(self.memory, self.event_bus)
        self.orchestrator = MultiAgentOrchestrator(self.event_bus, self.memory)
        self.memory_manager = AdvancedMemoryManager(self.memory)
        
        # 8 Novos sistemas avançados
        self.state_machine_manager = GlobalStateMachineManager(self.event_bus)
        self.reputation_engine = AgentReputationEngine(decay_factor=0.98)
        self.health_monitor = SystemHealthMonitor(self.event_bus)
        self.consensus_engine = ConsensusEngine(self.event_bus)
        self.conflict_resolver = ConflictResolver(self.event_bus)
        self.negotiation_protocol = NegotiationProtocol(self.event_bus)
        self.social_dynamics = SocialDynamicsManager()
        self.swarm_intelligence = SwarmIntelligenceEngine(self.memory_manager)
        
        # Motor de processamento noturno
        self.sleep_processor = SleepTimeProcessor(self.memory)
        
        # Novos sistemas avançados (Ronda 2)
        self.knowledge_graph = KnowledgeGraph(self.memory)
        self.kg_query = KnowledgeGraphQueryEngine(self.knowledge_graph)
        self.reflection_engine = ReflectionEngine(self.memory)
        self.goal_planner = GoalPlanner(self.memory)
        self.memory_salience = MemorySalienceEngine(self.memory)
        self.backup_system = BackupSystem(self.memory)
        
        # Ronda 3 - Novos sistemas
        self.episodic_memory = EpisodicMemory()
        self.prospective_memory = ProspectiveMemory()
        self.memory_guard = MemoryGuard()
        self.idle_processor = IdleProcessor()
        self.audit_trail = AuditTrail()
        self.performance_metrics = PerformanceMetrics()
        self.data_retention = DataRetentionManager()
        
        # Ronda 4 - Novos sistemas avançados (2026 patterns)
        self.a2a_protocol = A2AProtocol()
        self.checkpoint_manager = CheckpointManager()
        self.cost_engineering = CostEngineeringManager()
        self.observability = ObservabilityManager()
        
        # Ronda 5 - Novos sistemas de produção (2026 advanced patterns)
        self.rag_system = RAGSystem()
        self.web_scraping = WebScrapingSystem()
        self.code_executor = CodeExecutor()
        self.streaming = StreamingSystem()
        self.webhook_manager = WebhookManager()
        
        # Ronda 6 - Sistemas avançados (2026 cutting-edge patterns)
        self.reasoning_engine = ReasoningEngine()
        self.guardrails = GuardrailsSystem()
        self.model_router = ModelRouter()
        self.observability_advanced = ObservabilitySystem()
        self.human_in_the_loop = HumanInTheLoop()
        self.context_manager = ContextManager()
        
        # Ronda 7 - Sistemas avançados (2026 latest patterns)
        self.tiered_memory = get_tiered_memory()
        self.advanced_kg = get_knowledge_graph()
        self.security_system = get_security_system()
        self.embedding_engine = get_embedding_engine()
        self.workflow_engine = get_workflow_engine()
        self.evaluator = get_evaluator()
        self.plugin_manager = get_plugin_manager()
        self.multimodal = get_multimodal()
        self.self_healing = get_self_healing()
        self.federated_memory = get_federated_memory()
        self.task_scheduler = get_task_scheduler()
        self.task_scheduler.start_background(interval_seconds=30)  # Process tasks every 30s
        
        # Registra agentes nos novos sistemas
        self._register_agents_to_orchestrator()
        self._register_agents_to_advanced_systems()
        self._register_agents_to_a2a()
        
        # Inscreve sistemas avançados no event bus
        self._wire_event_subscriptions()
        
        self.should_stop = False
        self._register_jobs()

    def _register_agents_to_orchestrator(self) -> None:
        """Registra agentes no orquestrador com suas capacidades"""
        from .orchestrator import AgentCapability, AgentRole
        
        # Dragão - Estratégia
        dragao_caps = [
            AgentCapability(
                name="critical_analysis",
                description="Análise crítica e identificação de riscos",
                required_skills=["critical_thinking"],
                supported_domains=["strategy", "risk"]
            )
        ]
        self.orchestrator.register_agent("dragao", self.dragao.profile.name, dragao_caps, AgentRole.STRATEGIST)
        
        # Elias - Pesquisa
        elias_caps = [
            AgentCapability(
                name="deep_research",
                description="Pesquisa aprofundada de tópicos",
                required_skills=["research"],
                supported_domains=["avicultura", "analysis"]
            )
        ]
        self.orchestrator.register_agent("elias", self.elias.profile.name, elias_caps, AgentRole.EXECUTOR)
        
        # Pesquisador - Validação
        pesquisador_caps = [
            AgentCapability(
                name="source_validation",
                description="Validação de fontes e integridade de dados",
                required_skills=["validation"],
                supported_domains=["verification", "quality"]
            )
        ]
        self.orchestrator.register_agent("pesquisador", self.pesquisador.profile.name, pesquisador_caps, AgentRole.VALIDATOR)
        
        # Estratega - Coordenação
        estratega_caps = [
            AgentCapability(
                name="workflow_coordination",
                description="Coordenação de workflows entre agentes",
                required_skills=["synthesis"],
                supported_domains=["coordination", "strategy"]
            )
        ]
        self.orchestrator.register_agent("estratega", self.estratega.profile.name, estratega_caps, AgentRole.COORDINATOR)
        
        # Documentalista - Documentação
        documentalista_caps = [
            AgentCapability(
                name="knowledge_synthesis",
                description="Síntese de conhecimento em documentação",
                required_skills=["synthesis", "pattern_recognition"],
                supported_domains=["documentation", "analysis"]
            )
        ]
        self.orchestrator.register_agent("documentalista", self.documentalista.profile.name, documentalista_caps, AgentRole.ANALYZER)
        
        # General - Comando Estratégico
        general_caps = [
            AgentCapability(
                name="strategic_command",
                description="Comando estratégico com análise fria e honestidade brutal",
                required_skills=["critical_thinking", "research", "synthesis"],
                supported_domains=["strategy", "analysis", "decision_making"]
            )
        ]
        self.orchestrator.register_agent("general", self.general.profile.name, general_caps, AgentRole.STRATEGIST)
    
    def _register_agents_to_advanced_systems(self) -> None:
        """Registra agentes nos 8 novos sistemas avançados"""
        agents = ["dragao", "elias", "pesquisador", "estratega", "documentalista", "general"]
        
        # State Machine - Cada agente tem sua máquina de estados
        for agent_id in agents:
            sm = self.state_machine_manager.register_agent(agent_id)
            sm.on_state_change.append(self._on_agent_state_change)
        
        # Reputation - Inicializa reputação para cada agente
        for agent_id in agents:
            self.reputation_engine.register_agent(agent_id, initial_reputation=60.0)
        
        # Health Monitoring - Registra cada agente para monitoramento
        for agent_id in agents:
            monitor = self.health_monitor.register_agent(agent_id)
            monitor.on_health_change.append(self._on_health_alert)
        
        # Social Dynamics - Cria relacionamentos entre agentes
        for agent_1 in agents:
            for agent_2 in agents:
                if agent_1 < agent_2:  # Evita duplicatas
                    self.social_dynamics.get_or_create_relationship(agent_1, agent_2)
        
        # Reputation decay job
        self.scheduler.add_job(ScheduledJob(
            name="Reputation Decay",
            callback=self.reputation_engine.apply_decay,
            interval_seconds=60 * 60,  # Every hour
        ))
        
        # Swarm intelligence update job
        self.scheduler.add_job(ScheduledJob(
            name="Swarm Intelligence Update",
            callback=self.swarm_intelligence.update_pheromones,
            interval_seconds=30,  # Every 30 seconds
        ))
        
        # Health monitoring job
        self.scheduler.add_job(ScheduledJob(
            name="System Health Check",
            callback=self._check_all_health,
            interval_seconds=60,  # Every minute
        ))
        
        # Processamento noturno - consolida memória e cristaliza skills
        self.scheduler.add_job(ScheduledJob(
            name="Sleep Time Processing",
            callback=self.run_sleep_processing,
            schedule_times=["03:00"],
        ))
        
        # Backup diário
        self.scheduler.add_job(ScheduledJob(
            name="Daily Backup",
            callback=self.run_backup,
            schedule_times=["04:00"],
        ))
        
        # State machine timeout check job
        self.scheduler.add_job(ScheduledJob(
            name="State Machine Timeout Check",
            callback=self._check_state_timeouts,
            interval_seconds=10,  # Every 10 seconds
        ))
        
        # Checkpoint auto-save job
        self.scheduler.add_job(ScheduledJob(
            name="Auto Checkpoint",
            callback=self._auto_checkpoint,
            interval_seconds=300,  # Every 5 minutes
        ))
        
        # Cost metrics collection job
        self.scheduler.add_job(ScheduledJob(
            name="Cost Metrics Collection",
            callback=self._collect_cost_metrics,
            interval_seconds=60,  # Every minute
        ))
    
    def _register_agents_to_a2a(self) -> None:
        """Registra agentes no protocolo A2A"""
        agents_config = [
            ("dragao", self.dragao.profile.name, ["strategy", "critical_analysis"], ["strategy", "risk"]),
            ("elias", self.elias.profile.name, ["research", "analysis"], ["avicultura", "analysis"]),
            ("pesquisador", self.pesquisador.profile.name, ["validation", "verification"], ["verification", "quality"]),
            ("estratega", self.estratega.profile.name, ["orchestration", "coordination"], ["planning", "coordination"]),
            ("documentalista", self.documentalista.profile.name, ["documentation", "synthesis"], ["documentation", "analysis"]),
            ("general", self.general.profile.name, ["strategic_command", "deep_research", "audit"], ["strategy", "analysis", "decision_making"]),
        ]
        
        for agent_id, name, capabilities, specializations in agents_config:
            card = A2AAgentCard(
                agent_id=agent_id,
                agent_name=name,
                capabilities=capabilities,
                specializations=specializations,
                max_concurrent_tasks=3,
                reliability_score=0.8
            )
            self.a2a_protocol.register_agent(card)
        
        logger.info(f"Registered {len(agents_config)} agents to A2A protocol")
    
    def _wire_event_subscriptions(self) -> None:
        """Inscreve sistemas avançados no event bus para funcionarem em conjunto"""
        # Reputation: registra performance quando agentes completam ações
        self.event_bus.subscribe(
            [EventType.AGENT_ACTION_COMPLETED],
            self._on_action_completed,
            subscriber_id="reputation_tracker"
        )
        # Health Monitor: regista heartbeat quando eventos de sistema ocorrem
        self.event_bus.subscribe(
            [EventType.SYSTEM_STARTED, EventType.SCHEDULE_JOB_EXECUTED],
            self._on_system_event,
            subscriber_id="health_tracker"
        )
        # Social Dynamics: regista colaboração bem sucedida
        self.event_bus.subscribe(
            [EventType.AGENT_COLLABORATION_SUCCESS],
            self._on_collaboration_success,
            subscriber_id="social_tracker"
        )
        # Event Logger: loga todos os eventos para memória
        self.event_bus.subscribe(
            [ev for ev in EventType],
            self.event_logger.log_event,
            subscriber_id="event_logger"
        )

    def _on_action_completed(self, event: Event) -> None:
        """Regista performance de agente no reputation engine"""
        agent_id = event.payload.get("agent_id", "unknown")
        task_id = event.payload.get("task_id", "unknown")
        success = event.payload.get("success", True)
        domain = event.payload.get("domain", "general")
        score = 80.0 if success else 30.0
        self.reputation_engine.record_performance(
            agent_id=agent_id,
            task_id=task_id,
            metric=ReputationMetric.RELIABILITY,
            score=score,
            context={"domain": domain}
        )

    def _on_system_event(self, event: Event) -> None:
        """Regista heartbeat para todos os agentes quando sistema está activo"""
        for agent_id in list(self.health_monitor.agents):
            self.health_monitor.agents[agent_id].record_heartbeat()

    def _on_collaboration_success(self, event: Event) -> None:
        """Regista colaboração bem sucedida no social dynamics"""
        agent_1 = event.payload.get("agent_1")
        agent_2 = event.payload.get("agent_2")
        context = event.payload.get("context", "collaboration")
        if agent_1 and agent_2:
            self.social_dynamics.record_successful_collaboration(agent_1, agent_2, context)

    def _on_agent_state_change(self, event) -> None:
        """Callback para mudanças de estado de agentes"""
        try:
            from .events import Event, EventType
            ev = Event(
                type=EventType.AGENT_STATE_CHANGED,
                source="ORIONDaemon",
                payload={
                    "agent_id": event.agent_id,
                    "from_state": event.from_state.value,
                    "to_state": event.to_state.value
                }
            )
            self.event_bus.publish(ev)
        except Exception:
            logger.warning("Erro ao publicar evento de mudança de estado", exc_info=True)
    
    def _on_health_alert(self, alert) -> None:
        """Callback para alertas de saúde"""
        pass  # Já publicado pelo HealthMonitor
    
    def _check_all_health(self) -> None:
        """Verifica saúde de todos os agentes"""
        self.health_monitor.check_all_health()
    
    def _check_state_timeouts(self) -> None:
        """Verifica timeouts de estado de máquinas de estados"""
        timeouts = self.state_machine_manager.check_all_timeouts()
        for agent_id, target_state in timeouts:
            try:
                sm = self.state_machine_manager.get_agent_state_machine(agent_id)
                if sm:
                    from .agent_state_machine import StateTransitionTrigger
                    sm.transition_to(target_state, StateTransitionTrigger.TIMEOUT)
            except Exception:
                logger.warning("Erro ao verificar timeout para agente %s", agent_id, exc_info=True)
    
    def _auto_checkpoint(self) -> None:
        """Auto-save checkpoint do estado atual"""
        try:
            from .checkpointing import WorkflowState
            
            # Cria snapshot do estado de cada agente
            snapshots = []
            for agent_id in ["dragao", "elias", "pesquisador", "estratega", "documentalista"]:
                state_data = {
                    "agent_id": agent_id,
                    "status": "active",
                    "last_activity": datetime.now(timezone.utc).isoformat()
                }
                snapshot = self.checkpoint_manager.create_snapshot(
                    workflow_id="main",
                    agent_id=agent_id,
                    state_data=state_data,
                    tags=["auto_checkpoint"]
                )
                snapshots.append(snapshot)
            
            # Salva checkpoint
            if snapshots:
                self.checkpoint_manager.create_checkpoint(
                    workflow_id="main",
                    task_id="auto_save",
                    snapshots=snapshots
                )
        except Exception:
            logger.warning("Erro ao criar checkpoint automático", exc_info=True)
    
    def _collect_cost_metrics(self) -> None:
        """Collect cost metrics for observability"""
        try:
            summary = self.cost_engineering.get_system_cost_summary(days=1)
            self.observability.metrics.set_gauge(
                "daily_cost_usd",
                summary["total_cost"],
                labels={"period": "daily"}
            )
            self.observability.metrics.set_gauge(
                "daily_tokens",
                summary["total_tokens"],
                labels={"period": "daily"}
            )
        except Exception:
            logger.warning("Erro ao coleter métricas de custo", exc_info=True)

    def _register_jobs(self) -> None:
        self.scheduler.add_job(ScheduledJob(
            name="Health Check",
            callback=self.run_health_check,
            interval_seconds=60 * 60 * 4,
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Morning Research",
            callback=lambda: self.run_research_topic("doenças e epidemiologia"),
            schedule_times=["06:00"],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Genetics Research",
            callback=lambda: self.run_research_topic("genética e reprodução"),
            schedule_times=["09:00"],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Nutrition Research",
            callback=lambda: self.run_research_topic("nutrição e ração"),
            schedule_times=["12:00"],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Behavior Research",
            callback=lambda: self.run_research_topic("comportamento e bem-estar"),
            schedule_times=["15:00"],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Emerging Trends Research",
            callback=lambda: self.run_research_topic("tendências emergentes"),
            schedule_times=["18:00"],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Night Research",
            callback=lambda: self.run_research_topic("produção e economia"),
            schedule_times=["21:00"],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Self Evolution Monday",
            callback=lambda: self.run_self_evolution("proposta de prompt", tool_name="PromptTool"),
            schedule_times=["21:00"],
            weekdays=[0],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Self Evolution Wednesday",
            callback=lambda: self.run_self_evolution("proposta de ferramenta", tool_name="ResearchTool"),
            schedule_times=["21:00"],
            weekdays=[2],
        ))
        self.scheduler.add_job(ScheduledJob(
            name="Self Evolution Friday",
            callback=lambda: self.run_self_evolution("proposta de estratégia", tool_name="ValidationTool"),
            schedule_times=["21:00"],
            weekdays=[4],
        ))

    def start(self) -> None:
        logger.info("Inicializando daemon...")
        
        # Publica evento de inicialização
        startup_event = Event(
            type=EventType.SYSTEM_STARTED,
            source="ORIONDaemon",
            payload={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        self.event_bus.publish(startup_event)
        
        self.run_background()
        self._install_exit_handler()
        logger.info("Daemon em execução. Pressiona CTRL+C para parar.")
        try:
            while not self.should_stop:
                time.sleep(1)
                if self.idle_processor.is_idle():
                    result = self.idle_processor.run_next_task()
                    if result:
                        logger.info("Tarefa idle executada: %s", result.task_name)
        except KeyboardInterrupt:
            self.stop()

    def run_background(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        logger.info("Parando daemon...")
        self.should_stop = True
        self.scheduler.stop()
        logger.info("Desligado com segurança.")

    def _install_exit_handler(self) -> None:
        def handler(signum, frame):
            self.stop()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def run_health_check(self) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        message = (
            f"Health check ORION realizado em {now}.\n"
            "Scheduler: ativo.\n"
            "Memória: operacional.\n"
            "Número de entradas: {count}.\n"
        ).format(count=len(self.memory.list_entries()))
        self.documentalista.archive("Health Check", message, scope="system")
        # Regista heartbeat para todos os agentes
        for agent_id in self.health_monitor.agents:
            self.health_monitor.agents[agent_id].record_heartbeat()
        # Publica evento de job executado
        self.event_bus.publish(Event(
            type=EventType.SCHEDULE_JOB_EXECUTED,
            source="HealthCheck",
            payload={"timestamp": now}
        ))
        logger.info("Health check criado em %s", now)

    def run_research_topic(self, topic: str) -> None:
        start_time = datetime.now(timezone.utc)
        findings = self.tool_registry.run_tool("ResearchTool", topic=topic, depth=2)
        entry = self.elias.research_summary(topic, findings)
        self.estratega.plan(
            objective=f"Validar e operacionalizar pesquisa sobre {topic}",
            next_steps="1. Reunir fontes.\n2. Comparar dados.\n3. Priorizar ações concretas."
        )
        self.pesquisador.validate(
            claim=f"Pesquisa de avicultura sobre {topic}",
            reference="literatura acadêmica simulada"
        )
        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        self.episodic_memory.record(
            event_type="research",
            agent="elias",
            action=f"Pesquisa: {topic}",
            result=f"Entrada criada: {entry.id}, Descobertas: {len(findings)}",
            outcome="success",
            duration_seconds=duration / 1000,
            tags=[topic],
        )
        
        self.audit_trail.log(
            agent="elias",
            action="research",
            target=topic,
            result=f"Entrada: {entry.id}",
            success=True,
            duration_ms=duration,
        )
        
        self.performance_metrics.record_action(
            agent="elias",
            action="research",
            duration_ms=duration,
            success=True,
        )
        
        ev = Event(
            type=EventType.AGENT_ACTION_COMPLETED,
            source="ORIONDaemon",
            payload={
                "agent_id": "elias",
                "task_id": entry.id,
                "success": True,
                "domain": "avicultura"
            }
        )
        self.event_bus.publish(ev)
        logger.info("Pesquisa criada para: %s -> %s", topic, entry.id)

    def run_self_evolution(self, subject: str, tool_name: str) -> None:
        start_time = datetime.now(timezone.utc)
        report = self.self_evolution.generate_proposal_from_tool(tool_name, objective=subject)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        self.episodic_memory.record(
            event_type="self_evolution",
            agent="system",
            action=f"Auto-evolução: {subject}",
            result=f"Status: {report.status}, Skills: {len(report.new_skills)}",
            outcome="success" if report.status == "INSTALLED" else "pending",
            duration_seconds=duration / 1000,
            tags=[tool_name, subject],
        )
        
        self.audit_trail.log(
            agent="system",
            action="self_evolution",
            target=subject,
            result=report.status,
            success=report.status == "INSTALLED",
            duration_ms=duration,
            metadata={"tool": tool_name},
        )
        
        self.performance_metrics.record_action(
            agent="system",
            action="self_evolution",
            duration_ms=duration,
            success=report.status == "INSTALLED",
        )
        
        self.documentalista.archive(
            "Self Evolution Installed",
            report.to_markdown(),
            scope="self_evolution"
        )
        logger.info("Auto-evolução instalada: %s via %s", report.subject, report.tool_name)

        dashboard = (
            f"\n{'='*60}\n"
            f"  QUADRO DE AUTO-EVOLUCAO\n"
            f"{'='*60}\n"
            f"  Ferramenta: {report.tool_name}\n"
            f"  Objetivo:   {report.subject}\n"
            f"  Status:     {report.status}\n"
            f"  Instalado:  {report.installed_at}\n"
            f"{'-'*60}\n"
            f"  O QUE FOI ENCONTRADO:\n"
        )
        for f in report.findings:
            dashboard += f"    - {f}\n"
        dashboard += f"{'-'*60}\n  O QUE FOI INSTALADO:\n"
        for a in report.actions_taken:
            dashboard += f"    - {a}\n"
        if report.new_skills:
            dashboard += f"{'-'*60}\n  NOVOS CONHECIMENTOS:\n"
            for s in report.new_skills:
                dashboard += f"    - {s}\n"
        dashboard += f"{'='*60}\n"
        print(dashboard)
    
    def run_sleep_processing(self) -> None:
        logger.info("Iniciando processamento noturno...")
        report = self.sleep_processor.run_cycle()
        
        try:
            new_nodes = self.knowledge_graph.build_from_memory()
            logger.info("Knowledge graph: %d nós adicionados", new_nodes)
        except Exception as e:
            logger.error("Erro ao construir knowledge graph: %s", e)
        
        try:
            retention_report = self.data_retention.run_cleanup()
            logger.info("Data retention: %d ficheiros removidos (%d bytes)", 
                        retention_report.files_deleted, retention_report.bytes_freed)
        except Exception as e:
            logger.error("Erro no data retention: %s", e)
        
        salience_stats = self.memory_salience.get_stats()
        logger.info("Salience: %d alta, %d média, %b baixa", 
                    salience_stats.get("high_salience", 0),
                    salience_stats.get("medium_salience", 0),
                    salience_stats.get("low_salience", 0))
        
        self.documentalista.archive(
            "Sleep Processing Report",
            report.to_markdown(),
            scope="system"
        )
        dashboard = (
            f"\n{'='*60}\n"
            f"  PROCESSAMENTO NOTURNO CONCLUIDO\n"
            f"{'='*60}\n"
            f"  Duracao: {report.duration_seconds:.1f}s\n"
        )
        if report.consolidation:
            c = report.consolidation
            dashboard += (
                f"  Consolidacao: {c.entries_archived} arquivadas, "
                f"{c.entries_pruned} removidas, {c.summaries_created} resumos\n"
            )
        if report.crystallization:
            s = report.crystallization
            dashboard += (
                f"  Cristalizacao: {s.skills_created} skills criadas, "
                f"{s.skills_updated} atualizadas\n"
            )
        kg_stats = self.knowledge_graph.get_stats()
        dashboard += (
            f"  Knowledge Graph: {kg_stats['total_nodes']} nós, "
            f"{kg_stats['total_edges']} arestas\n"
        )
        dashboard += (
            f"  Salience: {salience_stats.get('high_salience', 0)} alta, "
            f"{salience_stats.get('low_salience', 0)} baixa\n"
        )
        if report.errors:
            dashboard += f"  Erros: {len(report.errors)}\n"
            for e in report.errors:
                dashboard += f"    - {e}\n"
        dashboard += f"{'='*60}\n"
        print(dashboard)
    
    def run_backup(self) -> None:
        logger.info("Criando backup diário...")
        backup_id = self.backup_system.create_backup(description="Backup diário automático")
        if backup_id:
            logger.info("Backup criado: %s", backup_id)
        else:
            logger.error("Falha ao criar backup")
