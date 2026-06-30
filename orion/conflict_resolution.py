"""
Conflict Resolution & Negotiation System
========================================
Automatically detects and resolves conflicts between agents using multiple
resolution strategies. Records conflict history for learning.

Conflict Types:
- PRIORITY_CONFLICT: Disagreement on task priority
- DATA_CONFLICT: Different data/information
- STRATEGY_CONFLICT: Different approaches
- RESOURCE_CONFLICT: Competing for resources
- GOAL_CONFLICT: Different objectives
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import threading

logger = logging.getLogger("orion.conflict_resolution")


class ConflictType(str, Enum):
    """Types of conflicts."""
    PRIORITY_CONFLICT = "priority_conflict"
    DATA_CONFLICT = "data_conflict"
    STRATEGY_CONFLICT = "strategy_conflict"
    RESOURCE_CONFLICT = "resource_conflict"
    GOAL_CONFLICT = "goal_conflict"
    UNKNOWN = "unknown"


class ResolutionStrategy(str, Enum):
    """Strategies for conflict resolution."""
    PRIORITY_BASED = "priority_based"      # Higher priority agent wins
    VOTING = "voting"                      # Majority wins
    NEGOTIATION = "negotiation"            # Agents negotiate
    CONSENSUS = "consensus"                # Full consensus required
    ARBITRATION = "arbitration"            # Neutral arbiter decides
    HYBRID = "hybrid"                      # Combination approach


@dataclass
class Conflict:
    """Represents an active conflict between agents."""
    conflict_id: str
    agents_involved: List[str]
    conflict_type: ConflictType
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict = field(default_factory=dict)


@dataclass
class ConflictResolution:
    """Result of conflict resolution."""
    conflict_id: str
    agents_involved: List[str]
    conflict_type: ConflictType
    resolution_strategy: ResolutionStrategy
    resolution: Any  # The resolved decision/action
    winner: Optional[str] = None  # If applicable
    agreement_level: float = 0.0  # 0-100
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    learning_value: float = 1.0  # How much learning happened


class ConflictResolver:
    """
    Detects and resolves conflicts between agents.
    
    Features:
    - Multiple resolution strategies
    - Conflict history tracking
    - Learning from past conflicts
    - Mediation/arbitration support
    """
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.active_conflicts: Dict[str, Conflict] = {}
        self.resolution_history: List[ConflictResolution] = []
        self.lock = threading.RLock()
    
    def report_conflict(self, agents_involved: List[str], conflict_type: ConflictType,
                       description: str, context: Optional[Dict] = None) -> Conflict:
        """Report a new conflict."""
        with self.lock:
            import uuid
            conflict_id = str(uuid.uuid4())
            
            conflict = Conflict(
                conflict_id=conflict_id,
                agents_involved=agents_involved,
                conflict_type=conflict_type,
                description=description,
                context=context or {}
            )
            
            self.active_conflicts[conflict_id] = conflict
            
            # Publish event
            if self.event_bus:
                try:
                    from .events import Event, EventType
                    ev = Event(
                        type=EventType.AGENT_CONFLICT_DETECTED,
                        source="ConflictResolver",
                        payload={
                            "conflict_id": conflict_id,
                            "agents": agents_involved,
                            "type": conflict_type.value
                        }
                    )
                    self.event_bus.publish(ev)
                except Exception:
                        logger.warning("Erro ao publicar evento de conflito %s", conflict_id, exc_info=True)

            return conflict
    
    def resolve_conflict(self, conflict: Conflict, agent_positions: Dict[str, Any],
                        agent_priorities: Dict[str, float] = None,
                        strategy: ResolutionStrategy = ResolutionStrategy.HYBRID) -> ConflictResolution:
        """
        Resolve a conflict.
        
        Args:
            conflict: The conflict to resolve
            agent_positions: Dict of agent_id -> their position/proposal
            agent_priorities: Dict of agent_id -> priority (0-100)
            strategy: Resolution strategy to use
            
        Returns:
            ConflictResolution with the decided outcome
        """
        with self.lock:
            if strategy == ResolutionStrategy.PRIORITY_BASED:
                return self._resolve_by_priority(conflict, agent_positions, agent_priorities)
            elif strategy == ResolutionStrategy.VOTING:
                return self._resolve_by_voting(conflict, agent_positions)
            elif strategy == ResolutionStrategy.NEGOTIATION:
                return self._resolve_by_negotiation(conflict, agent_positions)
            elif strategy == ResolutionStrategy.CONSENSUS:
                return self._resolve_by_consensus(conflict, agent_positions)
            elif strategy == ResolutionStrategy.ARBITRATION:
                return self._resolve_by_arbitration(conflict, agent_positions)
            elif strategy == ResolutionStrategy.HYBRID:
                return self._resolve_by_hybrid(conflict, agent_positions, agent_priorities)
            
            # Default: arbitration
            return self._resolve_by_arbitration(conflict, agent_positions)
    
    def _resolve_by_priority(self, conflict: Conflict, agent_positions: Dict[str, Any],
                            agent_priorities: Dict[str, float] = None) -> ConflictResolution:
        """Highest priority agent wins."""
        if not agent_priorities:
            agent_priorities = {agent: 50.0 for agent in conflict.agents_involved}
        
        winner = max(agent_priorities.items(), key=lambda x: x[1])
        winner_agent = winner[0]
        winner_position = agent_positions.get(winner_agent)
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            agents_involved=conflict.agents_involved,
            conflict_type=conflict.conflict_type,
            resolution_strategy=ResolutionStrategy.PRIORITY_BASED,
            resolution=winner_position,
            winner=winner_agent,
            agreement_level=winner[1],
            rationale=f"Agent {winner_agent} had highest priority ({winner[1]:.1f})"
        )
    
    def _resolve_by_voting(self, conflict: Conflict, agent_positions: Dict[str, Any]) -> ConflictResolution:
        """Majority vote wins."""
        position_votes: Dict[str, int] = {}
        for agent, position in agent_positions.items():
            pos_str = str(position)
            position_votes[pos_str] = position_votes.get(pos_str, 0) + 1
        
        if not position_votes:
            return self._resolve_by_arbitration(conflict, agent_positions)
        
        winning_position = max(position_votes.items(), key=lambda x: x[1])
        agreement_level = (winning_position[1] / len(agent_positions)) * 100
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            agents_involved=conflict.agents_involved,
            conflict_type=conflict.conflict_type,
            resolution_strategy=ResolutionStrategy.VOTING,
            resolution=winning_position[0],
            agreement_level=agreement_level,
            rationale=f"Majority vote: {winning_position[1]}/{len(agent_positions)} agents agreed"
        )
    
    def _resolve_by_negotiation(self, conflict: Conflict, agent_positions: Dict[str, Any]) -> ConflictResolution:
        """Agents negotiate toward compromise."""
        # Simple compromise: average positions (if numeric)
        try:
            values = [float(p) for p in agent_positions.values()]
            compromise = sum(values) / len(values)
            agreement_level = 50 + (10 * len(agent_positions))  # Better with more agents
            
            return ConflictResolution(
                conflict_id=conflict.conflict_id,
                agents_involved=conflict.agents_involved,
                conflict_type=conflict.conflict_type,
                resolution_strategy=ResolutionStrategy.NEGOTIATION,
                resolution=compromise,
                agreement_level=min(100, agreement_level),
                rationale=f"Negotiated compromise: {compromise:.2f}"
            )
        except (ValueError, TypeError):
            # Non-numeric positions - use voting
            return self._resolve_by_voting(conflict, agent_positions)
    
    def _resolve_by_consensus(self, conflict: Conflict, agent_positions: Dict[str, Any]) -> ConflictResolution:
        """Consensus: all must agree, otherwise escalate."""
        unique_positions = set(str(p) for p in agent_positions.values())
        
        if len(unique_positions) == 1:
            # Already consensus
            return ConflictResolution(
                conflict_id=conflict.conflict_id,
                agents_involved=conflict.agents_involved,
                conflict_type=conflict.conflict_type,
                resolution_strategy=ResolutionStrategy.CONSENSUS,
                resolution=list(agent_positions.values())[0],
                agreement_level=100,
                rationale="Full consensus achieved"
            )
        else:
            # No consensus - escalate to arbitration
            return self._resolve_by_arbitration(conflict, agent_positions)
    
    def _resolve_by_arbitration(self, conflict: Conflict, agent_positions: Dict[str, Any]) -> ConflictResolution:
        """Neutral arbitration - pick most balanced option."""
        position_votes: Dict[str, int] = {}
        for agent, position in agent_positions.items():
            pos_str = str(position)
            position_votes[pos_str] = position_votes.get(pos_str, 0) + 1
        
        arbitrated = max(position_votes.items(), key=lambda x: x[1]) if position_votes else ("DEADLOCK", 0)
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            agents_involved=conflict.agents_involved,
            conflict_type=conflict.conflict_type,
            resolution_strategy=ResolutionStrategy.ARBITRATION,
            resolution=arbitrated[0],
            agreement_level=50,
            rationale=f"Arbitrated resolution: {arbitrated[0]}"
        )
    
    def _resolve_by_hybrid(self, conflict: Conflict, agent_positions: Dict[str, Any],
                          agent_priorities: Dict[str, float] = None) -> ConflictResolution:
        """Adaptively select resolution strategy."""
        # Choose strategy based on conflict type and context
        if conflict.conflict_type == ConflictType.PRIORITY_CONFLICT and agent_priorities:
            strategy = ResolutionStrategy.PRIORITY_BASED
        elif len(agent_positions) <= 2:
            strategy = ResolutionStrategy.VOTING
        else:
            strategy = ResolutionStrategy.NEGOTIATION
        
        # Resolve using selected strategy
        result = self.resolve_conflict(conflict, agent_positions, agent_priorities, strategy)
        result.resolution_strategy = ResolutionStrategy.HYBRID
        result.learning_value = 1.5
        
        return result
    
    def record_resolution(self, resolution: ConflictResolution):
        """Record a resolved conflict."""
        with self.lock:
            self.resolution_history.append(resolution)
            
            # Remove from active conflicts
            if resolution.conflict_id in self.active_conflicts:
                del self.active_conflicts[resolution.conflict_id]
            
            # Publish resolution event
            if self.event_bus:
                try:
                    from .events import Event, EventType
                    ev = Event(
                        type=EventType.AGENT_CONFLICT_RESOLVED,
                        source="ConflictResolver",
                        payload={
                            "conflict_id": resolution.conflict_id,
                            "strategy": resolution.resolution_strategy.value,
                            "agreement_level": resolution.agreement_level
                        }
                    )
                    self.event_bus.publish(ev)
                except Exception:
                    logger.warning("Erro ao publicar evento de resolução %s", resolution.conflict_id, exc_info=True)
    
    def get_conflict_statistics(self) -> Dict:
        """Get statistics about conflicts."""
        with self.lock:
            conflict_types = {}
            resolution_strategies = {}
            
            for resolution in self.resolution_history:
                ctype = resolution.conflict_type.value
                conflict_types[ctype] = conflict_types.get(ctype, 0) + 1
                
                rstrat = resolution.resolution_strategy.value
                resolution_strategies[rstrat] = resolution_strategies.get(rstrat, 0) + 1
            
            return {
                "total_conflicts": len(self.resolution_history),
                "active_conflicts": len(self.active_conflicts),
                "conflict_types": conflict_types,
                "resolution_strategies": resolution_strategies,
                "avg_agreement_level": sum(r.agreement_level for r in self.resolution_history) / len(self.resolution_history) if self.resolution_history else 0
            }
