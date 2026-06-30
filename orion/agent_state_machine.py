"""
Agent State Machine & Lifecycle Management
==========================================
Manages the lifecycle and state transitions of each agent with automatic
detection of stuck agents and proper cleanup.

States:
  - IDLE: Agent waiting for tasks
  - THINKING: Agent processing information
  - EXECUTING: Agent performing an action
  - COMMUNICATING: Agent exchanging messages
  - LEARNING: Agent updating skills/memory
  - RESTING: Agent recovering resources
  - ERROR: Agent encountered an error
  - TERMINATED: Agent stopped/dead

Transitions are triggered by events, timeouts, or explicit commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Callable, List, Optional, Tuple
from datetime import datetime
import logging
import threading
from collections import defaultdict

logger = logging.getLogger("orion.agent_state_machine")


class AgentStateType(str, Enum):
    """Possible states for an agent."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMMUNICATING = "communicating"
    LEARNING = "learning"
    RESTING = "resting"
    ERROR = "error"
    TERMINATED = "terminated"


class StateTransitionTrigger(str, Enum):
    """Events that trigger state transitions."""
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    COMMUNICATION_NEEDED = "communication_needed"
    LEARNING_TRIGGERED = "learning_triggered"
    ERROR_OCCURRED = "error_occurred"
    RECOVERY_STARTED = "recovery_started"
    TIMEOUT = "timeout"
    EXPLICIT_COMMAND = "explicit_command"
    RESOURCE_DEPLETION = "resource_depletion"


@dataclass
class StateTransitionRule:
    """Defines valid transitions between states."""
    from_state: AgentStateType
    to_state: AgentStateType
    trigger: StateTransitionTrigger
    description: str = ""
    min_duration: float = 0  # Minimum time in from_state before transition (seconds)


@dataclass
class AgentLifecycleEvent:
    """Records a state transition event."""
    agent_id: str
    from_state: AgentStateType
    to_state: AgentStateType
    trigger: StateTransitionTrigger
    timestamp: datetime
    duration_in_previous_state: float  # seconds
    metadata: Dict = field(default_factory=dict)


@dataclass
class AgentStatistics:
    """Tracks statistics about agent state patterns."""
    agent_id: str
    total_transitions: int = 0
    state_durations: Dict[AgentStateType, List[float]] = field(default_factory=lambda: defaultdict(list))
    transition_history: List[AgentLifecycleEvent] = field(default_factory=list)
    error_count: int = 0
    timeout_count: int = 0
    recovery_attempts: int = 0
    last_state_change: Optional[datetime] = None


class AgentStateMachine:
    """
    Manages state machine for a single agent with lifecycle tracking.
    
    Features:
    - Automatic state transitions based on events
    - Timeout detection for stuck agents
    - State duration tracking
    - Comprehensive lifecycle history
    - Thread-safe operations
    """
    
    # Default transition rules
    TRANSITION_RULES = [
        StateTransitionRule(AgentStateType.IDLE, AgentStateType.THINKING, StateTransitionTrigger.TASK_ASSIGNED, "Task assigned"),
        StateTransitionRule(AgentStateType.THINKING, AgentStateType.EXECUTING, StateTransitionTrigger.TASK_COMPLETED, "Execution ready"),
        StateTransitionRule(AgentStateType.EXECUTING, AgentStateType.COMMUNICATING, StateTransitionTrigger.COMMUNICATION_NEEDED, "Need to communicate"),
        StateTransitionRule(AgentStateType.EXECUTING, AgentStateType.LEARNING, StateTransitionTrigger.LEARNING_TRIGGERED, "Learning from result"),
        StateTransitionRule(AgentStateType.COMMUNICATING, AgentStateType.IDLE, StateTransitionTrigger.TASK_COMPLETED, "Communication done"),
        StateTransitionRule(AgentStateType.LEARNING, AgentStateType.IDLE, StateTransitionTrigger.TASK_COMPLETED, "Learning complete"),
        StateTransitionRule(AgentStateType.IDLE, AgentStateType.RESTING, StateTransitionTrigger.RESOURCE_DEPLETION, "Resting"),
        StateTransitionRule(AgentStateType.RESTING, AgentStateType.IDLE, StateTransitionTrigger.TASK_ASSIGNED, "Rested"),
        StateTransitionRule(AgentStateType.THINKING, AgentStateType.ERROR, StateTransitionTrigger.ERROR_OCCURRED, "Error in thinking"),
        StateTransitionRule(AgentStateType.EXECUTING, AgentStateType.ERROR, StateTransitionTrigger.ERROR_OCCURRED, "Error in execution"),
        StateTransitionRule(AgentStateType.ERROR, AgentStateType.THINKING, StateTransitionTrigger.RECOVERY_STARTED, "Recovery started"),
        StateTransitionRule(AgentStateType.ERROR, AgentStateType.IDLE, StateTransitionTrigger.TIMEOUT, "Timeout - reset to idle"),
    ]
    
    def __init__(self, agent_id: str, initial_state: AgentStateType = AgentStateType.IDLE):
        self.agent_id = agent_id
        self.current_state = initial_state
        self.state_entry_time = datetime.now()
        self.lock = threading.RLock()
        self.statistics = AgentStatistics(agent_id=agent_id)
        
        # Transition callbacks
        self.on_state_change: List[Callable[[AgentLifecycleEvent], None]] = []
        
        # State timeouts (seconds) - auto-transition if exceeded
        self.state_timeouts: Dict[AgentStateType, float] = {
            AgentStateType.IDLE: 300,          # 5 minutes
            AgentStateType.THINKING: 60,       # 1 minute
            AgentStateType.EXECUTING: 120,     # 2 minutes
            AgentStateType.COMMUNICATING: 30,  # 30 seconds
            AgentStateType.LEARNING: 60,       # 1 minute
            AgentStateType.RESTING: 180,       # 3 minutes
            AgentStateType.ERROR: 30,          # 30 seconds
        }
    
    def transition_to(self, new_state: AgentStateType, trigger: StateTransitionTrigger, metadata: Dict = None) -> bool:
        """
        Attempt to transition to a new state.
        
        Args:
            new_state: Target state
            trigger: What triggered the transition
            metadata: Additional context data
            
        Returns:
            True if transition was successful, False otherwise
        """
        with self.lock:
            # Check if transition is valid
            if not self._is_valid_transition(self.current_state, new_state, trigger):
                return False
            
            # Calculate duration in previous state
            now = datetime.now()
            duration = (now - self.state_entry_time).total_seconds()
            
            # Create transition event
            event = AgentLifecycleEvent(
                agent_id=self.agent_id,
                from_state=self.current_state,
                to_state=new_state,
                trigger=trigger,
                timestamp=now,
                duration_in_previous_state=duration,
                metadata=metadata or {}
            )
            
            # Update state
            old_state = self.current_state
            self.current_state = new_state
            self.state_entry_time = now
            
            # Update statistics
            self.statistics.total_transitions += 1
            self.statistics.state_durations[old_state].append(duration)
            self.statistics.transition_history.append(event)
            self.statistics.last_state_change = now
            
            if trigger == StateTransitionTrigger.ERROR_OCCURRED:
                self.statistics.error_count += 1
            elif trigger == StateTransitionTrigger.TIMEOUT:
                self.statistics.timeout_count += 1
            elif trigger == StateTransitionTrigger.RECOVERY_STARTED:
                self.statistics.recovery_attempts += 1
            
            # Trigger callbacks
            for callback in self.on_state_change:
                try:
                    callback(event)
                except Exception:
                    logger.warning("Erro em callback on_state_change para agente %s", self.agent_id, exc_info=True)
            
            return True
    
    def _is_valid_transition(self, from_state: AgentStateType, to_state: AgentStateType, trigger: StateTransitionTrigger) -> bool:
        """Check if transition is allowed by rules."""
        for rule in self.TRANSITION_RULES:
            if rule.from_state == from_state and rule.to_state == to_state and rule.trigger == trigger:
                return True
        return False
    
    def get_state(self) -> AgentStateType:
        """Get current state."""
        with self.lock:
            return self.current_state
    
    def get_time_in_current_state(self) -> float:
        """Get seconds spent in current state."""
        with self.lock:
            return (datetime.now() - self.state_entry_time).total_seconds()
    
    def check_timeout(self) -> Tuple[bool, Optional[AgentStateType]]:
        """
        Check if current state has exceeded timeout.
        
        Returns:
            (is_timeout, target_state) - if timeout exceeded, suggests recovery state
        """
        with self.lock:
            time_in_state = (datetime.now() - self.state_entry_time).total_seconds()
            timeout = self.state_timeouts.get(self.current_state)
            
            if timeout and time_in_state > timeout:
                # Suggest recovery state
                if self.current_state == AgentStateType.ERROR:
                    return True, AgentStateType.IDLE
                else:
                    return True, AgentStateType.ERROR
            
            return False, None
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about this agent's lifecycle."""
        with self.lock:
            avg_state_durations = {}
            for state, durations in self.statistics.state_durations.items():
                if durations:
                    avg_state_durations[state.value] = {
                        "average": sum(durations) / len(durations),
                        "min": min(durations),
                        "max": max(durations),
                        "count": len(durations)
                    }
            
            return {
                "agent_id": self.agent_id,
                "current_state": self.current_state.value,
                "time_in_current_state": self.get_time_in_current_state(),
                "total_transitions": self.statistics.total_transitions,
                "error_count": self.statistics.error_count,
                "timeout_count": self.statistics.timeout_count,
                "recovery_attempts": self.statistics.recovery_attempts,
                "state_durations": avg_state_durations,
                "last_state_change": self.statistics.last_state_change.isoformat() if self.statistics.last_state_change else None
            }


class GlobalStateMachineManager:
    """
    Manages state machines for all agents in the system.
    
    Features:
    - Centralized state management
    - Automatic timeout detection
    - Batch operations
    - System-wide statistics
    """
    
    def __init__(self, event_bus=None):
        self.agents: Dict[str, AgentStateMachine] = {}
        self.lock = threading.RLock()
        self.event_bus = event_bus
        self.monitoring_active = False
    
    def register_agent(self, agent_id: str) -> AgentStateMachine:
        """Register a new agent and create its state machine."""
        with self.lock:
            if agent_id not in self.agents:
                sm = AgentStateMachine(agent_id)
                self.agents[agent_id] = sm
                
                # Add event callback if event_bus available
                if self.event_bus:
                    sm.on_state_change.append(self._on_state_change)
                
                return sm
            return self.agents[agent_id]
    
    def get_agent_state_machine(self, agent_id: str) -> Optional[AgentStateMachine]:
        """Get state machine for an agent."""
        with self.lock:
            return self.agents.get(agent_id)
    
    def check_all_timeouts(self) -> List[Tuple[str, AgentStateType]]:
        """Check all agents for timeouts. Returns list of (agent_id, suggested_state)."""
        with self.lock:
            timeouts = []
            for agent_id, sm in self.agents.items():
                is_timeout, target_state = sm.check_timeout()
                if is_timeout:
                    timeouts.append((agent_id, target_state))
            return timeouts
    
    def get_system_state_summary(self) -> Dict:
        """Get overview of all agents' states."""
        with self.lock:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "total_agents": len(self.agents),
                "agents_by_state": defaultdict(list),
                "error_agents": [],
                "timeout_agents": []
            }
            
            for agent_id, sm in self.agents.items():
                state = sm.get_state()
                summary["agents_by_state"][state.value].append(agent_id)
                
                if state == AgentStateType.ERROR:
                    summary["error_agents"].append(agent_id)
                
                is_timeout, _ = sm.check_timeout()
                if is_timeout:
                    summary["timeout_agents"].append(agent_id)
            
            return summary
    
    def _on_state_change(self, event: AgentLifecycleEvent):
        """Internal callback for state changes."""
        if self.event_bus:
            from .events import Event, EventType
            try:
                ev = Event(
                    type=EventType.AGENT_STATE_CHANGED,
                    source="StateMachine",
                    payload={
                        "agent_id": event.agent_id,
                        "from_state": event.from_state.value,
                        "to_state": event.to_state.value,
                        "trigger": event.trigger.value
                    }
                )
                self.event_bus.publish(ev)
            except Exception:
                logger.warning("Erro ao publicar evento de mudança de estado para agente %s", event.agent_id, exc_info=True)
    
    def get_all_statistics(self) -> Dict[str, Dict]:
        """Get statistics for all agents."""
        with self.lock:
            return {agent_id: sm.get_statistics() for agent_id, sm in self.agents.items()}
