"""
Agent Reputation & Performance Scoring System
==============================================
Tracks individual performance metrics and reputation score for each agent,
enabling intelligent task assignment and competitive learning.

Each agent has:
- Overall reputation: 0-100
- Domain-specific expertise scores
- Performance metrics: accuracy, speed, reliability
- Reputation history with decay factor
- Automatic rewards/penalties based on outcomes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading
from collections import defaultdict


class ReputationMetric(str, Enum):
    """Types of performance metrics tracked."""
    ACCURACY = "accuracy"              # Correctness of results
    SPEED = "speed"                    # Execution time
    RELIABILITY = "reliability"        # No crashes/errors
    CONSISTENCY = "consistency"        # Similar quality over time
    INNOVATION = "innovation"          # Novel solutions
    COLLABORATION = "collaboration"    # Works well with others


@dataclass
class PerformanceRecord:
    """Records a single performance evaluation."""
    agent_id: str
    task_id: str
    metric: ReputationMetric
    score: float  # 0-100
    timestamp: datetime
    context: Dict = field(default_factory=dict)  # Task domain, difficulty, etc


@dataclass
class ReputationSnapshot:
    """Snapshot of reputation at a point in time."""
    timestamp: datetime
    overall_reputation: float
    accuracy_score: float
    speed_score: float
    reliability_score: float
    consistency_score: float
    innovation_score: float
    collaboration_score: float
    specializations: Dict[str, float]  # Domain -> score


class AgentReputationEngine:
    """
    Manages reputation scoring and performance tracking for agents.
    
    Features:
    - Multi-dimensional performance tracking
    - Domain-specific expertise scoring
    - Automatic decay of old scores
    - Reputation-based agent ranking
    - Performance benchmarking
    - Reputation history and trends
    """
    
    def __init__(self, decay_factor: float = 0.98):
        """
        Initialize reputation engine.
        
        Args:
            decay_factor: How much reputation decays per period (0.98 = 2% decay)
        """
        self.decay_factor = decay_factor
        self.agents: Dict[str, 'AgentReputation'] = {}
        self.lock = threading.RLock()
        self.performance_history: List[PerformanceRecord] = []
    
    def register_agent(self, agent_id: str, initial_reputation: float = 50.0):
        """Register a new agent with initial reputation."""
        with self.lock:
            if agent_id not in self.agents:
                self.agents[agent_id] = AgentReputation(
                    agent_id=agent_id,
                    overall_reputation=initial_reputation,
                    decay_factor=self.decay_factor
                )
    
    def record_performance(self, agent_id: str, task_id: str, metric: ReputationMetric, 
                          score: float, context: Dict = None) -> float:
        """
        Record a performance metric for an agent.
        
        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            metric: Type of performance metric
            score: Score 0-100
            context: Additional context (domain, difficulty, etc)
            
        Returns:
            Updated overall reputation
        """
        self.register_agent(agent_id)
        
        with self.lock:
            agent = self.agents[agent_id]
            record = PerformanceRecord(
                agent_id=agent_id,
                task_id=task_id,
                metric=metric,
                score=max(0, min(100, score)),  # Clamp 0-100
                timestamp=datetime.now(),
                context=context or {}
            )
            
            self.performance_history.append(record)
            
            # Update agent reputation
            if metric == ReputationMetric.ACCURACY:
                agent.accuracy_score = (agent.accuracy_score * 0.8) + (score * 0.2)
            elif metric == ReputationMetric.SPEED:
                agent.speed_score = (agent.speed_score * 0.8) + (score * 0.2)
            elif metric == ReputationMetric.RELIABILITY:
                agent.reliability_score = (agent.reliability_score * 0.8) + (score * 0.2)
            elif metric == ReputationMetric.CONSISTENCY:
                agent.consistency_score = (agent.consistency_score * 0.8) + (score * 0.2)
            elif metric == ReputationMetric.INNOVATION:
                agent.innovation_score = (agent.innovation_score * 0.8) + (score * 0.2)
            elif metric == ReputationMetric.COLLABORATION:
                agent.collaboration_score = (agent.collaboration_score * 0.8) + (score * 0.2)
            
            # Update domain specialization if specified
            if context and "domain" in context:
                domain = context["domain"]
                if domain not in agent.specializations:
                    agent.specializations[domain] = 50.0
                agent.specializations[domain] = (agent.specializations[domain] * 0.85) + (score * 0.15)
            
            # Recalculate overall reputation
            agent.calculate_overall_reputation()
            agent.reputation_history.append(ReputationSnapshot(
                timestamp=datetime.now(),
                overall_reputation=agent.overall_reputation,
                accuracy_score=agent.accuracy_score,
                speed_score=agent.speed_score,
                reliability_score=agent.reliability_score,
                consistency_score=agent.consistency_score,
                innovation_score=agent.innovation_score,
                collaboration_score=agent.collaboration_score,
                specializations=dict(agent.specializations)
            ))
            
            return agent.overall_reputation
    
    def apply_reputation_penalty(self, agent_id: str, penalty_percent: float, reason: str):
        """Apply a reputation penalty."""
        self.register_agent(agent_id)
        
        with self.lock:
            agent = self.agents[agent_id]
            penalty = agent.overall_reputation * (penalty_percent / 100)
            agent.overall_reputation = max(0, agent.overall_reputation - penalty)
            agent.penalties.append((reason, penalty, datetime.now()))
    
    def apply_reputation_bonus(self, agent_id: str, bonus_percent: float, reason: str):
        """Apply a reputation bonus."""
        self.register_agent(agent_id)
        
        with self.lock:
            agent = self.agents[agent_id]
            bonus = agent.overall_reputation * (bonus_percent / 100)
            agent.overall_reputation = min(100, agent.overall_reputation + bonus)
            agent.bonuses.append((reason, bonus, datetime.now()))
    
    def apply_decay(self):
        """Apply reputation decay to all agents (should be called periodically)."""
        with self.lock:
            for agent in self.agents.values():
                agent.accuracy_score *= self.decay_factor
                agent.speed_score *= self.decay_factor
                agent.reliability_score *= self.decay_factor
                agent.consistency_score *= self.decay_factor
                agent.innovation_score *= self.decay_factor
                agent.collaboration_score *= self.decay_factor
                
                for domain in agent.specializations:
                    agent.specializations[domain] *= self.decay_factor
                
                agent.calculate_overall_reputation()
    
    def get_agent_reputation(self, agent_id: str) -> Optional[Dict]:
        """Get reputation data for an agent."""
        with self.lock:
            if agent_id not in self.agents:
                return None
            
            agent = self.agents[agent_id]
            return {
                "agent_id": agent_id,
                "overall_reputation": agent.overall_reputation,
                "accuracy_score": agent.accuracy_score,
                "speed_score": agent.speed_score,
                "reliability_score": agent.reliability_score,
                "consistency_score": agent.consistency_score,
                "innovation_score": agent.innovation_score,
                "collaboration_score": agent.collaboration_score,
                "specializations": dict(agent.specializations),
                "last_update": agent.last_update.isoformat(),
                "performance_count": len([p for p in self.performance_history if p.agent_id == agent_id])
            }
    
    def get_agent_ranking(self) -> List[Tuple[str, float]]:
        """Get agents ranked by reputation (highest first)."""
        with self.lock:
            ranking = [(agent_id, agent.overall_reputation) 
                      for agent_id, agent in self.agents.items()]
            return sorted(ranking, key=lambda x: x[1], reverse=True)
    
    def get_best_agent_for_domain(self, domain: str) -> Optional[Tuple[str, float]]:
        """Get agent with highest specialization in a domain."""
        with self.lock:
            best = None
            best_score = -1
            
            for agent_id, agent in self.agents.items():
                score = agent.specializations.get(domain, 0)
                if score > best_score:
                    best_score = score
                    best = (agent_id, score)
            
            return best
    
    def get_agent_trend(self, agent_id: str, metric: ReputationMetric, periods: int = 10) -> List[float]:
        """Get recent trend of a metric (for visualization)."""
        with self.lock:
            if agent_id not in self.agents:
                return []
            
            agent = self.agents[agent_id]
            
            # Get recent reputation snapshots
            snapshots = agent.reputation_history[-periods:]
            
            if metric == ReputationMetric.ACCURACY:
                return [s.accuracy_score for s in snapshots]
            elif metric == ReputationMetric.SPEED:
                return [s.speed_score for s in snapshots]
            elif metric == ReputationMetric.RELIABILITY:
                return [s.reliability_score for s in snapshots]
            elif metric == ReputationMetric.CONSISTENCY:
                return [s.consistency_score for s in snapshots]
            elif metric == ReputationMetric.INNOVATION:
                return [s.innovation_score for s in snapshots]
            elif metric == ReputationMetric.COLLABORATION:
                return [s.collaboration_score for s in snapshots]
            
            return []
    
    def get_all_statistics(self) -> Dict:
        """Get comprehensive statistics for all agents."""
        with self.lock:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "total_agents": len(self.agents),
                "agents": {}
            }
            
            for agent_id, agent in self.agents.items():
                stats["agents"][agent_id] = {
                    "overall_reputation": agent.overall_reputation,
                    "accuracy": agent.accuracy_score,
                    "speed": agent.speed_score,
                    "reliability": agent.reliability_score,
                    "specializations": dict(agent.specializations),
                    "performance_count": len([p for p in self.performance_history if p.agent_id == agent_id])
                }
            
            return stats


@dataclass
class AgentReputation:
    """Internal representation of an agent's reputation."""
    agent_id: str
    overall_reputation: float = 50.0
    accuracy_score: float = 50.0
    speed_score: float = 50.0
    reliability_score: float = 50.0
    consistency_score: float = 50.0
    innovation_score: float = 50.0
    collaboration_score: float = 50.0
    specializations: Dict[str, float] = field(default_factory=dict)  # Domain -> score
    reputation_history: List[ReputationSnapshot] = field(default_factory=list)
    penalties: List[Tuple[str, float, datetime]] = field(default_factory=list)  # (reason, amount, time)
    bonuses: List[Tuple[str, float, datetime]] = field(default_factory=list)    # (reason, amount, time)
    decay_factor: float = 0.98
    last_update: datetime = field(default_factory=datetime.now)
    
    def calculate_overall_reputation(self):
        """Recalculate overall reputation from component scores."""
        scores = [
            self.accuracy_score * 0.25,
            self.speed_score * 0.15,
            self.reliability_score * 0.30,
            self.consistency_score * 0.15,
            self.innovation_score * 0.10,
            self.collaboration_score * 0.05
        ]
        self.overall_reputation = sum(scores)
        self.last_update = datetime.now()
