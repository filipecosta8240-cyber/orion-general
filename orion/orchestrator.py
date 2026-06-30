from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

class WorkflowType(Enum):
    """Tipos de workflows de orquestração"""
    SEQUENTIAL = "sequential"      # Um agente após outro
    PARALLEL = "parallel"          # Múltiplos agentes em paralelo
    HIERARCHICAL = "hierarchical"  # Com coordenador
    REACTIVE = "reactive"          # Event-driven
    COLLABORATIVE = "collaborative" # Com consenso

class AgentRole(Enum):
    """Papéis especializados para agentes"""
    COORDINATOR = "coordinator"     # Coordena workflow
    EXECUTOR = "executor"          # Executa tarefas
    VALIDATOR = "validator"        # Valida resultados
    ANALYZER = "analyzer"          # Analisa padrões
    STRATEGIST = "strategist"      # Planeja

@dataclass
class AgentCapability:
    """Capacidade de um agente"""
    name: str
    description: str
    required_skills: List[str] = field(default_factory=list)
    supported_domains: List[str] = field(default_factory=list)
    confidence_level: float = 0.5  # 0-1

@dataclass
class AgentState:
    """Estado atual de um agente"""
    agent_id: str
    name: str
    status: str  # "idle", "busy", "blocked"
    current_task: Optional[str] = None
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    error_count: int = 0
    success_count: int = 0
    
    @property
    def reliability(self) -> float:
        """Confiabilidade baseada em histórico"""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.5
        return self.success_count / total

@dataclass
class WorkflowTask:
    """Tarefa dentro de um workflow"""
    task_id: str
    description: str
    assigned_to: Optional[str] = None
    status: str = "pending"  # "pending", "assigned", "executing", "completed", "failed"
    priority: str = "normal"
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class OrchestrationWorkflow:
    """Define um workflow de orquestração"""
    
    def __init__(
        self,
        workflow_id: str,
        description: str,
        workflow_type: WorkflowType,
        tasks: List[WorkflowTask]
    ):
        self.workflow_id = workflow_id
        self.description = description
        self.workflow_type = workflow_type
        self.tasks = {task.task_id: task for task in tasks}
        self.status = "created"
        self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.execution_log: List[Dict[str, Any]] = []
    
    def get_tasks_by_status(self, status: str) -> List[WorkflowTask]:
        """Retorna tarefas com status específico"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_pending_tasks(self) -> List[WorkflowTask]:
        """Retorna tarefas prontas para execução"""
        pending = self.get_tasks_by_status("pending")
        
        # Filtra por dependências satisfeitas
        ready = []
        for task in pending:
            if all(self.tasks[dep_id].status == "completed" for dep_id in task.dependencies):
                ready.append(task)
        
        return ready
    
    def mark_task_assigned(self, task_id: str, agent_id: str) -> bool:
        """Marca tarefa como atribuída"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.assigned_to = agent_id
        task.status = "assigned"
        task.start_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        self.execution_log.append({
            "timestamp": task.start_time,
            "event": "task_assigned",
            "task_id": task_id,
            "agent_id": agent_id
        })
        
        return True
    
    def mark_task_completed(self, task_id: str, result: Any) -> bool:
        """Marca tarefa como completada"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "completed"
        task.result = result
        task.end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        self.execution_log.append({
            "timestamp": task.end_time,
            "event": "task_completed",
            "task_id": task_id
        })
        
        return True
    
    def mark_task_failed(self, task_id: str, error: str) -> bool:
        """Marca tarefa como falhada"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "failed"
        task.error = error
        task.end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        self.execution_log.append({
            "timestamp": task.end_time,
            "event": "task_failed",
            "task_id": task_id,
            "error": error
        })
        
        return True

class MultiAgentOrchestrator:
    """Orquestra colaboração entre múltiplos agentes"""
    
    def __init__(self, event_bus=None, memory_bridge=None):
        self.event_bus = event_bus
        self.memory = memory_bridge
        self.agents: Dict[str, AgentState] = {}
        self.capabilities: Dict[str, List[AgentCapability]] = {}
        self.workflows: Dict[str, OrchestrationWorkflow] = {}
        self.active_workflow: Optional[str] = None
        self._lock = threading.RLock()
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        capabilities: List[AgentCapability],
        role: AgentRole = AgentRole.EXECUTOR
    ) -> None:
        """Registra um agente no orquestrador"""
        with self._lock:
            self.agents[agent_id] = AgentState(
                agent_id=agent_id,
                name=name,
                status="idle"
            )
            self.capabilities[agent_id] = capabilities
    
    def create_workflow(
        self,
        workflow_id: str,
        description: str,
        workflow_type: WorkflowType,
        tasks: List[WorkflowTask]
    ) -> OrchestrationWorkflow:
        """Cria um novo workflow"""
        workflow = OrchestrationWorkflow(
            workflow_id=workflow_id,
            description=description,
            workflow_type=workflow_type,
            tasks=tasks
        )
        
        with self._lock:
            self.workflows[workflow_id] = workflow
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.AGENT_ACTION_STARTED,
                source="MultiAgentOrchestrator",
                payload={"workflow_id": workflow_id, "type": workflow_type.value}
            )
            self.event_bus.publish(event)
        
        return workflow
    
    def find_best_agent_for_task(
        self,
        task: WorkflowTask,
        required_domains: Optional[List[str]] = None
    ) -> Optional[str]:
        """Encontra melhor agente para uma tarefa"""
        with self._lock:
            candidates = []

            for agent_id, agent_state in self.agents.items():
                if agent_state.status != "idle":
                    continue

                capabilities = self.capabilities.get(agent_id, [])

                if required_domains:
                    agent_domains = set()
                    for cap in capabilities:
                        agent_domains.update(cap.supported_domains)

                    if not any(domain in agent_domains for domain in required_domains):
                        continue

                score = agent_state.reliability
                candidates.append((agent_id, score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def assign_task(self, workflow_id: str, task_id: str) -> bool:
        """Atribui tarefa a um agente"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return False
        
        task = workflow.tasks.get(task_id)
        if not task:
            return False
        
        # Encontra melhor agente
        agent_id = self.find_best_agent_for_task(task)
        if not agent_id:
            return False
        
        # Atribui tarefa
        with self._lock:
            workflow.mark_task_assigned(task_id, agent_id)
            self.agents[agent_id].status = "busy"
            self.agents[agent_id].current_task = task_id
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.AGENT_ACTION_STARTED,
                source="MultiAgentOrchestrator",
                payload={"workflow_id": workflow_id, "task_id": task_id, "agent_id": agent_id}
            )
            self.event_bus.publish(event)
        
        return True
    
    def complete_task(self, workflow_id: str, task_id: str, result: Any) -> None:
        """Marca tarefa como completada"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return
        
        task = workflow.tasks.get(task_id)
        if not task or not task.assigned_to:
            return
        
        with self._lock:
            workflow.mark_task_completed(task_id, result)
            
            # Liberta agente
            agent_id = task.assigned_to
            self.agents[agent_id].status = "idle"
            self.agents[agent_id].current_task = None
            self.agents[agent_id].success_count += 1
            self.agents[agent_id].last_activity = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.AGENT_ACTION_COMPLETED,
                source="MultiAgentOrchestrator",
                payload={"workflow_id": workflow_id, "task_id": task_id, "agent_id": agent_id, "success": True}
            )
            self.event_bus.publish(event)
    
    def fail_task(self, workflow_id: str, task_id: str, error: str) -> None:
        """Marca tarefa como falhada"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return
        
        task = workflow.tasks.get(task_id)
        if not task or not task.assigned_to:
            return
        
        with self._lock:
            workflow.mark_task_failed(task_id, error)
            
            # Liberta agente e incrementa erro
            agent_id = task.assigned_to
            self.agents[agent_id].status = "idle"
            self.agents[agent_id].current_task = None
            self.agents[agent_id].error_count += 1
            self.agents[agent_id].last_activity = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.AGENT_ACTION_FAILED,
                source="MultiAgentOrchestrator",
                payload={"workflow_id": workflow_id, "task_id": task_id, "agent_id": task.assigned_to, "error": error}
            )
            self.event_bus.publish(event)
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Retorna status atual de um workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {}
        
        total_tasks = len(workflow.tasks)
        completed = len(workflow.get_tasks_by_status("completed"))
        failed = len(workflow.get_tasks_by_status("failed"))
        pending = len(workflow.get_tasks_by_status("pending"))
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "type": workflow.workflow_type.value,
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress": (completed + failed) / total_tasks if total_tasks > 0 else 0,
            "created_at": workflow.created_at,
            "execution_log_size": len(workflow.execution_log)
        }
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retorna status de um agente específico"""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        
        return {
            "agent_id": agent_id,
            "name": agent.name,
            "status": agent.status,
            "current_task": agent.current_task,
            "reliability": f"{agent.reliability:.1%}",
            "success_count": agent.success_count,
            "error_count": agent.error_count,
            "last_activity": agent.last_activity
        }
    
    def get_all_agents_status(self) -> List[Dict[str, Any]]:
        """Retorna status de todos os agentes"""
        return [self.get_agent_status(aid) for aid in self.agents.keys()]
