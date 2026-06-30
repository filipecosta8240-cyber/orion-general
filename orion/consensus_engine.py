"""
Multi-Agent Consensus Engine
============================
Provides multiple strategies for reaching consensus among agents when making
collective decisions. Enables intelligent decision-making without centralized control.

Strategies:
- VOTING: Majority vote wins
- EVIDENCE_BASED: Decision weighted by strength of evidence
- COLLABORATIVE_SYNTHESIS: Agents create joint solution
- ITERATIVE_REFINEMENT: Iterative improvement toward agreement
- EMERGENT_AGREEMENT: Natural consensus emerges
- HYBRID_ADAPTIVE: Adaptive combination based on context
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import threading


class ConsensusStrategy(str, Enum):
    """Available consensus strategies."""
    VOTING = "voting"
    EVIDENCE_BASED = "evidence_based"
    COLLABORATIVE_SYNTHESIS = "collaborative_synthesis"
    ITERATIVE_REFINEMENT = "iterative_refinement"
    EMERGENT_AGREEMENT = "emergent_agreement"
    HYBRID_ADAPTIVE = "hybrid_adaptive"


@dataclass
class AgentProposal:
    """A proposal from an agent for a decision."""
    agent_id: str
    proposal: Any
    confidence: float  # 0-100, how confident is agent in proposal
    evidence: str  # Justification
    domain: str  # Domain of decision
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusVote:
    """A vote by an agent on a proposal."""
    agent_id: str
    proposal_id: str
    vote: float  # -1 to 1 (disagree to agree)
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusResult:
    """Result of a consensus process."""
    consensus_id: str
    decision: Any
    strategy_used: ConsensusStrategy
    agreement_level: float  # 0-100
    participating_agents: List[str]
    dissenting_agents: List[str]
    confidence: float  # 0-100, how confident in decision
    rationale: str
    timestamp: datetime = field(default_factory=datetime.now)
    iterations: int = 0


class ConsensusEngine:
    """
    Manages consensus building among agents.
    
    Features:
    - Multiple consensus strategies
    - Adaptive strategy selection
    - Multi-round consensus
    - Agreement tracking
    - Dissent recording
    """
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.consensus_history: List[ConsensusResult] = []
        self.lock = threading.RLock()
        self.on_consensus_reached: List[Callable[[ConsensusResult], None]] = []
    
    def build_consensus(self, proposals: Dict[str, AgentProposal], 
                       strategy: ConsensusStrategy = ConsensusStrategy.HYBRID_ADAPTIVE) -> Optional[ConsensusResult]:
        """
        Build consensus from proposals.
        
        Args:
            proposals: Dict of agent_id -> proposal
            strategy: Consensus strategy to use
            
        Returns:
            ConsensusResult if consensus reached, None otherwise
        """
        with self.lock:
            import uuid
            consensus_id = str(uuid.uuid4())
            
            if strategy == ConsensusStrategy.VOTING:
                return self._voting_consensus(proposals, consensus_id)
            elif strategy == ConsensusStrategy.EVIDENCE_BASED:
                return self._evidence_based_consensus(proposals, consensus_id)
            elif strategy == ConsensusStrategy.COLLABORATIVE_SYNTHESIS:
                return self._collaborative_synthesis(proposals, consensus_id)
            elif strategy == ConsensusStrategy.ITERATIVE_REFINEMENT:
                return self._iterative_refinement(proposals, consensus_id)
            elif strategy == ConsensusStrategy.EMERGENT_AGREEMENT:
                return self._emergent_agreement(proposals, consensus_id)
            elif strategy == ConsensusStrategy.HYBRID_ADAPTIVE:
                return self._hybrid_adaptive(proposals, consensus_id)
            
            return None
    
    def _voting_consensus(self, proposals: Dict[str, AgentProposal], consensus_id: str) -> Optional[ConsensusResult]:
        """Simple majority vote."""
        if not proposals:
            return None
        
        # Group by proposal value
        proposal_votes: Dict[str, int] = {}
        for agent_id, proposal in proposals.items():
            prop_str = str(proposal.proposal)
            if prop_str not in proposal_votes:
                proposal_votes[prop_str] = 0
            proposal_votes[prop_str] += 1
        
        # Find winner
        if not proposal_votes:
            return None
        
        winning_proposal = max(proposal_votes.items(), key=lambda x: x[1])
        winner_votes = winning_proposal[1]
        total_votes = len(proposals)
        agreement_level = (winner_votes / total_votes) * 100
        
        return ConsensusResult(
            consensus_id=consensus_id,
            decision=winning_proposal[0],
            strategy_used=ConsensusStrategy.VOTING,
            agreement_level=agreement_level,
            participating_agents=list(proposals.keys()),
            dissenting_agents=[agent_id for agent_id, prop in proposals.items() 
                             if str(prop.proposal) != winning_proposal[0]],
            confidence=agreement_level,
            rationale=f"Majority vote: {winner_votes}/{total_votes} agents agreed"
        )
    
    def _evidence_based_consensus(self, proposals: Dict[str, AgentProposal], consensus_id: str) -> Optional[ConsensusResult]:
        """Decision based on strength of evidence."""
        if not proposals:
            return None
        
        # Score each proposal by agent confidence
        proposal_scores: Dict[str, float] = {}
        for agent_id, proposal in proposals.items():
            prop_str = str(proposal.proposal)
            if prop_str not in proposal_scores:
                proposal_scores[prop_str] = 0
            proposal_scores[prop_str] += proposal.confidence
        
        if not proposal_scores:
            return None
        
        best_proposal = max(proposal_scores.items(), key=lambda x: x[1])
        total_confidence = sum(proposal_scores.values())
        agreement_level = (best_proposal[1] / total_confidence) * 100 if total_confidence > 0 else 0
        
        return ConsensusResult(
            consensus_id=consensus_id,
            decision=best_proposal[0],
            strategy_used=ConsensusStrategy.EVIDENCE_BASED,
            agreement_level=agreement_level,
            participating_agents=list(proposals.keys()),
            dissenting_agents=[],
            confidence=agreement_level,
            rationale=f"Evidence-based: Combined confidence score {best_proposal[1]:.1f}"
        )
    
    def _collaborative_synthesis(self, proposals: Dict[str, AgentProposal], consensus_id: str) -> Optional[ConsensusResult]:
        """Agents synthesize joint solution."""
        if not proposals:
            return None
        
        # Simple synthesis: combine all proposals
        evidences = [p.evidence for p in proposals.values()]
        synthesis = f"Synthesis from {len(proposals)} agents: {'; '.join(evidences[:3])}"
        avg_confidence = sum(p.confidence for p in proposals.values()) / len(proposals) if proposals else 0
        
        return ConsensusResult(
            consensus_id=consensus_id,
            decision=synthesis,
            strategy_used=ConsensusStrategy.COLLABORATIVE_SYNTHESIS,
            agreement_level=avg_confidence,
            participating_agents=list(proposals.keys()),
            dissenting_agents=[],
            confidence=avg_confidence,
            rationale=f"Collaborative synthesis of {len(proposals)} proposals"
        )
    
    def _iterative_refinement(self, proposals: Dict[str, AgentProposal], consensus_id: str) -> Optional[ConsensusResult]:
        """Iterative improvement toward agreement."""
        if not proposals:
            return None
        
        # Multiple rounds of refinement
        current_proposals = dict(proposals)
        iterations = 0
        max_iterations = 5
        
        while iterations < max_iterations and len(set(str(p.proposal) for p in current_proposals.values())) > 1:
            # Find most common proposal
            common = max(set(str(p.proposal) for p in current_proposals.values()),
                        key=lambda p: sum(1 for x in current_proposals.values() if str(x.proposal) == p))
            
            # Agents adjust confidence toward common proposal
            for agent_id, proposal in current_proposals.items():
                if str(proposal.proposal) == common:
                    proposal.confidence = min(100, proposal.confidence + 5)
                else:
                    proposal.confidence = max(0, proposal.confidence - 3)
            
            iterations += 1
        
        final_decision = max(current_proposals.values(), key=lambda p: p.confidence).proposal
        avg_confidence = sum(p.confidence for p in current_proposals.values()) / len(current_proposals)
        
        return ConsensusResult(
            consensus_id=consensus_id,
            decision=final_decision,
            strategy_used=ConsensusStrategy.ITERATIVE_REFINEMENT,
            agreement_level=avg_confidence,
            participating_agents=list(proposals.keys()),
            dissenting_agents=[],
            confidence=avg_confidence,
            rationale=f"Converged after {iterations} refinement iterations",
            iterations=iterations
        )
    
    def _emergent_agreement(self, proposals: Dict[str, AgentProposal], consensus_id: str) -> Optional[ConsensusResult]:
        """Natural emergence of consensus through interaction."""
        if not proposals:
            return None
        
        # Find the proposal that appears most across domains
        proposal_frequencies: Dict[str, int] = {}
        for proposal in proposals.values():
            key = str(proposal.proposal)
            proposal_frequencies[key] = proposal_frequencies.get(key, 0) + 1
        
        if not proposal_frequencies:
            return None
        
        emergent = max(proposal_frequencies.items(), key=lambda x: x[1])
        emergence_strength = (emergent[1] / len(proposals)) * 100
        
        return ConsensusResult(
            consensus_id=consensus_id,
            decision=emergent[0],
            strategy_used=ConsensusStrategy.EMERGENT_AGREEMENT,
            agreement_level=emergence_strength,
            participating_agents=list(proposals.keys()),
            dissenting_agents=[],
            confidence=emergence_strength,
            rationale=f"Emergent agreement from natural interaction patterns"
        )
    
    def _hybrid_adaptive(self, proposals: Dict[str, AgentProposal], consensus_id: str) -> Optional[ConsensusResult]:
        """Adaptively select best strategy based on context."""
        if not proposals:
            return None
        
        # Analyze proposal diversity
        unique_proposals = len(set(str(p.proposal) for p in proposals.values()))
        avg_confidence = sum(p.confidence for p in proposals.values()) / len(proposals)
        
        # Choose strategy based on context
        if unique_proposals == 1:
            # Already unanimous
            strategy = ConsensusStrategy.VOTING
        elif avg_confidence > 80:
            # High confidence - use evidence-based
            strategy = ConsensusStrategy.EVIDENCE_BASED
        elif unique_proposals <= 2:
            # Few proposals - use voting
            strategy = ConsensusStrategy.VOTING
        else:
            # Diverse proposals - use iterative refinement
            strategy = ConsensusStrategy.ITERATIVE_REFINEMENT
        
        # Recursively call with selected strategy
        result = self.build_consensus(proposals, strategy)
        if result:
            result.strategy_used = ConsensusStrategy.HYBRID_ADAPTIVE
            result.rationale = f"Adaptive selection of {strategy.value} strategy"
        
        return result
    
    def get_consensus_history(self) -> List[Dict]:
        """Get history of consensus processes."""
        with self.lock:
            return [
                {
                    "consensus_id": c.consensus_id,
                    "decision": str(c.decision),
                    "strategy": c.strategy_used.value,
                    "agreement_level": c.agreement_level,
                    "confidence": c.confidence,
                    "timestamp": c.timestamp.isoformat()
                }
                for c in self.consensus_history[-50:]
            ]
