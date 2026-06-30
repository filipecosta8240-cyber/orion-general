from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger("orion.events")

class EventType(Enum):
    """Tipos de eventos no sistema ORION"""
    # Agent events
    AGENT_INITIALIZED = "agent.initialized"
    AGENT_ACTION_STARTED = "agent.action.started"
    AGENT_ACTION_COMPLETED = "agent.action.completed"
    AGENT_ACTION_FAILED = "agent.action.failed"
    AGENT_PROPOSAL = "agent.proposal"
    
    # Memory events
    MEMORY_ENTRY_CREATED = "memory.entry.created"
    MEMORY_ENTRY_UPDATED = "memory.entry.updated"
    MEMORY_SEARCH_PERFORMED = "memory.search.performed"
    
    # Evolution events
    EVOLUTION_PROPOSAL_CREATED = "evolution.proposal.created"
    EVOLUTION_PROPOSAL_APPROVED = "evolution.proposal.approved"
    EVOLUTION_PROPOSAL_REJECTED = "evolution.proposal.rejected"
    EVOLUTION_SKILL_LEARNED = "evolution.skill.learned"
    
    # Tool events
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"
    TOOL_REGISTERED = "tool.registered"
    
    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"
    
    # Schedule events
    SCHEDULE_JOB_EXECUTED = "schedule.job.executed"
    SCHEDULE_JOB_FAILED = "schedule.job.failed"
    
    # State Machine events
    AGENT_STATE_CHANGED = "agent.state.changed"
    AGENT_STATE_TIMEOUT = "agent.state.timeout"
    
    # Reputation events
    AGENT_REPUTATION_UPDATED = "agent.reputation.updated"
    AGENT_REPUTATION_PENALTY = "agent.reputation.penalty"
    
    # Health Monitoring events
    AGENT_HEALTH_ALERT = "agent.health.alert"
    AGENT_HEALTH_CRITICAL = "agent.health.critical"
    
    # Consensus events
    CONSENSUS_BUILDING = "consensus.building"
    CONSENSUS_REACHED = "consensus.reached"
    
    # Conflict events
    AGENT_CONFLICT_DETECTED = "agent.conflict.detected"
    AGENT_CONFLICT_RESOLVED = "agent.conflict.resolved"
    
    # Negotiation events
    AGENT_NEGOTIATION_STARTED = "agent.negotiation.started"
    AGENT_NEGOTIATION_SUCCESS = "agent.negotiation.success"
    AGENT_NEGOTIATION_FAILED = "agent.negotiation.failed"
    
    # Social Dynamics events
    AGENT_RELATIONSHIP_UPDATED = "agent.relationship.updated"
    AGENT_COLLABORATION_SUCCESS = "agent.collaboration.success"
    
    # Swarm Intelligence events
    SWARM_PHEROMONE_DEPOSITED = "swarm.pheromone.deposited"
    SWARM_EMERGENT_SOLUTION = "swarm.emergent.solution"

@dataclass
class Event:
    """Estrutura de um evento no sistema"""
    type: EventType
    source: str  # Agent ou componente que gerou o evento
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    event_id: str = field(default_factory=lambda: str(uuid4()))
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    priority: str = "normal"  # "critical", "high", "normal", "low"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "payload": self.payload,
            "tags": self.tags,
            "priority": self.priority,
        }

class EventSubscription:
    """Representação de uma subscrição a eventos"""
    def __init__(self, event_types: Set[EventType], callback: Callable, subscriber_id: str):
        self.event_types = event_types
        self.callback = callback
        self.subscriber_id = subscriber_id
        self.created_at = datetime.now(timezone.utc)
        self.call_count = 0

class EventBus:
    """Bus de eventos centralized para o sistema ORION"""
    
    def __init__(self, max_history: int = 10000):
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.event_history: List[Event] = []
        self.max_history = max_history
        self._lock = threading.RLock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        
    def subscribe(
        self, 
        event_types: List[EventType], 
        callback: Callable, 
        subscriber_id: Optional[str] = None
    ) -> str:
        """Subscribe a um ou mais tipos de eventos"""
        subscriber_id = subscriber_id or str(uuid4())
        event_types_set = set(event_types)
        
        subscription = EventSubscription(event_types_set, callback, subscriber_id)
        
        with self._lock:
            for event_type in event_types:
                key = event_type.value
                if key not in self.subscriptions:
                    self.subscriptions[key] = []
                self.subscriptions[key].append(subscription)
        
        return subscriber_id
    
    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe de todos os eventos"""
        with self._lock:
            for key, event_list in list(self.subscriptions.items()):
                filtered = [sub for sub in event_list if sub.subscriber_id != subscriber_id]
                if filtered:
                    self.subscriptions[key] = filtered
                else:
                    del self.subscriptions[key]
    
    def publish(self, event: Event) -> None:
        """Publica um evento para todos os subscribers"""
        with self._lock:
            # Adiciona ao histórico
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
            
            # Encontra subscribers interessados
            key = event.type.value
            subscribers = self.subscriptions.get(key, [])
            
        # Executa callbacks fora da lock
        for subscription in subscribers:
            try:
                subscription.call_count += 1
                subscription.callback(event)
            except Exception as e:
                logger.exception("Erro ao executar callback para %s:", event.type.value, exc_info=e)
    
    def get_history(
        self, 
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Retorna histórico de eventos com filtros opcionais"""
        with self._lock:
            filtered = self.event_history.copy()
        
        if event_type:
            filtered = [e for e in filtered if e.type == event_type]
        if source:
            filtered = [e for e in filtered if e.source == source]
        
        if limit:
            filtered = filtered[-limit:]
        
        return filtered
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do event bus"""
        with self._lock:
            stats = {
                "total_events": len(self.event_history),
                "event_types_count": len(self.subscriptions),
                "subscribers_count": sum(len(subs) for subs in self.subscriptions.values()),
                "events_by_type": {},
            }
            
            for event in self.event_history:
                event_key = event.type.value
                if event_key not in stats["events_by_type"]:
                    stats["events_by_type"][event_key] = 0
                stats["events_by_type"][event_key] += 1
        
        return stats

class EventFilter:
    """Filtro de eventos com múltiplos critérios"""
    def __init__(self):
        self.event_types: Optional[Set[EventType]] = None
        self.sources: Optional[Set[str]] = None
        self.priorities: Optional[Set[str]] = None
        self.min_timestamp: Optional[datetime] = None
    
    def matches(self, event: Event) -> bool:
        """Verifica se um evento passa no filtro"""
        if self.event_types and event.type not in self.event_types:
            return False
        if self.sources and event.source not in self.sources:
            return False
        if self.priorities and event.priority not in self.priorities:
            return False
        if self.min_timestamp:
            event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            if event_time < self.min_timestamp:
                return False
        return True

class EventLogger:
    """Logger de eventos que salva para memória"""
    def __init__(self, memory_bridge):
        self.memory = memory_bridge
        self.event_buffer: List[Event] = []
        self.buffer_size = 50
        
    def log_event(self, event: Event) -> None:
        """Registra um evento na memória"""
        self.event_buffer.append(event)
        
        if len(self.event_buffer) >= self.buffer_size:
            self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Salva buffer de eventos para memória"""
        if not self.event_buffer:
            return
        
        content = "# Event Log\n\n"
        for event in self.event_buffer:
            content += f"- [{event.timestamp}] {event.type.value} (from {event.source})\n"
            if event.payload:
                content += f"  Payload: {event.payload}\n"
        
        self.memory.create_entry(
            title="EVENT_LOG",
            content=content,
            tags={"domain": "events", "priority": "normal"},
            source="event_logger"
        )
        
        self.event_buffer.clear()
