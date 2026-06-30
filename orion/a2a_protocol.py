"""
Agent-to-Agent (A2A) Protocol Implementation
=============================================
Implements the A2A protocol for standardized communication between agents.
Based on the 2026 A2A protocol standard for multi-agent systems.

Features:
- Agent discovery and registration
- Task delegation and handoff
- Message routing and broadcasting
- Capability negotiation
- Protocol versioning
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger("orion.a2a_protocol")


class A2AMessageType(str, Enum):
    """Types of A2A messages."""
    AGENT_DISCOVERY = "agent_discovery"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    TASK_DELEGATION = "task_delegation"
    TASK_RESULT = "task_result"
    TASK_STATUS = "task_status"
    HEARTBEAT = "heartbeat"
    HANDOFF_REQUEST = "handoff_request"
    HANDOFF_ACCEPT = "handoff_accept"
    HANDOFF_REJECT = "handoff_reject"
    BROADCAST = "broadcast"
    ERROR = "error"


class AgentCapability(str, Enum):
    """Agent capabilities for discovery."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    ORCHESTRATION = "orchestration"
    DOCUMENTATION = "documentation"
    STRATEGY = "strategy"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    COMMUNICATION = "communication"


@dataclass
class A2AAgentCard:
    """Agent capability card for discovery."""
    agent_id: str
    agent_name: str
    capabilities: List[str]
    specializations: List[str]
    max_concurrent_tasks: int = 1
    current_load: float = 0.0
    reliability_score: float = 1.0
    avg_response_time: float = 0.0
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class A2AMessage:
    """Standard A2A message format."""
    message_id: str
    message_type: str
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requires_response: bool = False
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        return cls(**data)


@dataclass
class A2ATask:
    """A2A task representation."""
    task_id: str
    task_type: str
    description: str
    sender_id: str
    receiver_id: str
    priority: str = "normal"
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class A2AHandoff:
    """Agent handoff record."""
    handoff_id: str
    task_id: str
    from_agent: str
    to_agent: str
    reason: str
    status: str = "pending"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class A2AProtocol:
    """
    Agent-to-Agent Protocol Manager
    
    Handles communication between agents using the A2A protocol standard.
    Supports agent discovery, task delegation, handoffs, and broadcasting.
    """
    
    def __init__(self):
        self._agents: Dict[str, A2AAgentCard] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._message_history: List[A2AMessage] = []
        self._pending_tasks: Dict[str, A2ATask] = {}
        self._handoffs: Dict[str, A2AHandoff] = {}
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._protocol_version = "1.0.0"
        
    def register_agent(self, agent_card: A2AAgentCard) -> None:
        """Register an agent with the A2A protocol."""
        self._agents[agent_card.agent_id] = agent_card
        logger.info(f"Agent registered: {agent_card.agent_name} ({agent_card.agent_id})")
        
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the A2A protocol."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            
    def get_agent_card(self, agent_id: str) -> Optional[A2AAgentCard]:
        """Get agent capability card."""
        return self._agents.get(agent_id)
    
    def discover_agents(self, capability: Optional[str] = None) -> List[A2AAgentCard]:
        """Discover agents with specific capabilities."""
        agents = list(self._agents.values())
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        return sorted(agents, key=lambda a: (-a.reliability_score, a.current_load))
    
    def send_message(self, message: A2AMessage) -> bool:
        """Send a message to an agent."""
        if message.receiver_id not in self._agents and message.receiver_id != "*":
            logger.warning(f"Agent not found: {message.receiver_id}")
            return False
            
        self._message_history.append(message)
        
        if message.receiver_id in self._message_handlers:
            try:
                self._message_handlers[message.receiver_id](message)
                return True
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                return False
                
        return True
    
    def broadcast(self, sender_id: str, message_type: str, payload: Dict[str, Any]) -> int:
        """Broadcast a message to all agents."""
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_id=sender_id,
            receiver_id="*",
            payload=payload
        )
        
        count = 0
        for agent_id in self._agents:
            if agent_id != sender_id:
                msg = A2AMessage(
                    message_id=str(uuid.uuid4()),
                    message_type=message_type,
                    sender_id=sender_id,
                    receiver_id=agent_id,
                    payload=payload
                )
                self.send_message(msg)
                count += 1
                
        return count
    
    def delegate_task(self, task: A2ATask) -> bool:
        """Delegate a task to an agent."""
        if task.receiver_id not in self._agents:
            logger.warning(f"Cannot delegate to unknown agent: {task.receiver_id}")
            return False
            
        self._pending_tasks[task.task_id] = task
        
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            message_type=A2AMessageType.TASK_DELEGATION,
            sender_id=task.sender_id,
            receiver_id=task.receiver_id,
            payload=task.to_dict(),
            requires_response=True
        )
        
        return self.send_message(message)
    
    def request_handoff(self, handoff: A2AHandoff) -> bool:
        """Request a task handoff to another agent."""
        self._handoffs[handoff.handoff_id] = handoff
        
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            message_type=A2AMessageType.HANDOFF_REQUEST,
            sender_id=handoff.from_agent,
            receiver_id=handoff.to_agent,
            payload=handoff.to_dict(),
            requires_response=True
        )
        
        return self.send_message(message)
    
    def register_handler(self, agent_id: str, handler: Callable) -> None:
        """Register a message handler for an agent."""
        self._message_handlers[agent_id] = handler
        
    def get_protocol_status(self) -> Dict[str, Any]:
        """Get A2A protocol status."""
        return {
            "protocol_version": self._protocol_version,
            "registered_agents": len(self._agents),
            "total_messages": len(self._message_history),
            "pending_tasks": len(self._pending_tasks),
            "pending_handoffs": len(self._handoffs),
            "agents": {aid: card.to_dict() for aid, card in self._agents.items()}
        }
    
    def get_agent_ranking(self) -> List[Dict[str, Any]]:
        """Get agents ranked by reliability and load."""
        agents = list(self._agents.values())
        agents.sort(key=lambda a: (-a.reliability_score, a.current_load))
        return [
            {
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "reliability_score": a.reliability_score,
                "current_load": a.current_load,
                "capabilities": a.capabilities
            }
            for a in agents
        ]
