"""
Social Dynamics & Relationships
===============================
Models relationships and social interactions between agents including trust,
cooperation history, communication preferences, and attachment patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading


@dataclass
class AgentRelationship:
    """Represents relationship between two agents."""
    agent_1: str
    agent_2: str
    trust_level: float = 50.0  # 0-100
    cooperation_success_rate: float = 0.0  # 0-1
    communication_count: int = 0
    last_interaction: Optional[datetime] = None
    attachment_strength: float = 0.0  # How much they prefer working together
    conflict_history: List[Tuple[datetime, str]] = field(default_factory=list)
    collaboration_history: List[Tuple[datetime, str]] = field(default_factory=list)


class SocialDynamicsManager:
    """
    Manages social relationships between agents.
    
    Features:
    - Trust tracking between agent pairs
    - Cooperation success metrics
    - Communication preferences
    - Attachment patterns
    - Conflict/collaboration history
    """
    
    def __init__(self):
        self.relationships: Dict[Tuple[str, str], AgentRelationship] = {}
        self.lock = threading.RLock()
        self.social_graph: Dict[str, List[str]] = {}  # Adjacency list
    
    def _get_relationship_key(self, agent_1: str, agent_2: str) -> Tuple[str, str]:
        """Get normalized relationship key."""
        return tuple(sorted([agent_1, agent_2]))
    
    def get_or_create_relationship(self, agent_1: str, agent_2: str) -> AgentRelationship:
        """Get or create relationship between two agents."""
        with self.lock:
            key = self._get_relationship_key(agent_1, agent_2)
            
            if key not in self.relationships:
                self.relationships[key] = AgentRelationship(agent_1=agent_1, agent_2=agent_2)
                
                # Add to social graph
                if agent_1 not in self.social_graph:
                    self.social_graph[agent_1] = []
                if agent_2 not in self.social_graph:
                    self.social_graph[agent_2] = []
                
                self.social_graph[agent_1].append(agent_2)
                self.social_graph[agent_2].append(agent_1)
            
            return self.relationships[key]
    
    def record_successful_collaboration(self, agent_1: str, agent_2: str, context: str):
        """Record successful collaboration."""
        with self.lock:
            rel = self.get_or_create_relationship(agent_1, agent_2)
            
            # Increase trust
            rel.trust_level = min(100, rel.trust_level + 5)
            
            # Increase attachment
            rel.attachment_strength = min(100, rel.attachment_strength + 3)
            
            # Update cooperation success rate
            total = len(rel.collaboration_history) + 1
            successes = len([h for h in rel.collaboration_history if "success" in h[1].lower()]) + 1
            rel.cooperation_success_rate = successes / total if total > 0 else 0
            
            # Record collaboration
            rel.collaboration_history.append((datetime.now(), context))
            rel.communication_count += 1
            rel.last_interaction = datetime.now()
    
    def record_conflict(self, agent_1: str, agent_2: str, context: str):
        """Record conflict between agents."""
        with self.lock:
            rel = self.get_or_create_relationship(agent_1, agent_2)
            
            # Decrease trust
            rel.trust_level = max(0, rel.trust_level - 10)
            
            # Decrease attachment
            rel.attachment_strength = max(0, rel.attachment_strength - 5)
            
            # Record conflict
            rel.conflict_history.append((datetime.now(), context))
            rel.communication_count += 1
            rel.last_interaction = datetime.now()
    
    def get_trust_level(self, agent_1: str, agent_2: str) -> float:
        """Get trust level between two agents."""
        with self.lock:
            rel = self.get_or_create_relationship(agent_1, agent_2)
            return rel.trust_level
    
    def get_preferred_collaborators(self, agent_id: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """Get agents that work best with given agent."""
        with self.lock:
            collaborators = []
            
            for agent_2 in self.social_graph.get(agent_id, []):
                rel = self.get_or_create_relationship(agent_id, agent_2)
                score = (rel.trust_level * 0.5 + rel.attachment_strength * 0.5)
                collaborators.append((agent_2, score))
            
            return sorted(collaborators, key=lambda x: x[1], reverse=True)[:top_n]
    
    def get_conflict_history(self, agent_1: str, agent_2: str) -> List[Tuple[datetime, str]]:
        """Get conflict history between two agents."""
        with self.lock:
            rel = self.get_or_create_relationship(agent_1, agent_2)
            return list(rel.conflict_history)
    
    def get_social_network_status(self) -> Dict:
        """Get overview of social network."""
        with self.lock:
            total_relationships = len(self.relationships)
            high_trust = sum(1 for r in self.relationships.values() if r.trust_level > 70)
            low_trust = sum(1 for r in self.relationships.values() if r.trust_level < 30)
            
            return {
                "total_relationships": total_relationships,
                "high_trust_pairs": high_trust,
                "low_trust_pairs": low_trust,
                "avg_trust": sum(r.trust_level for r in self.relationships.values()) / total_relationships if total_relationships > 0 else 0,
                "total_interactions": sum(r.communication_count for r in self.relationships.values()),
                "network_density": len(self.social_graph)  # Number of agents
            }
