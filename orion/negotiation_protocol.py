"""
Negotiation Protocol
====================
Formal protocol for agents to negotiate with each other, enabling autonomy
and collaborative problem-solving without centralized control.

Phases: PROPOSAL -> DISCUSSION -> NEGOTIATION -> AGREEMENT -> EXECUTION
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import threading

logger = logging.getLogger("orion.negotiation_protocol")


class NegotiationPhase(str, Enum):
    """Phases of negotiation."""
    PROPOSAL = "proposal"
    DISCUSSION = "discussion"
    NEGOTIATION = "negotiation"
    AGREEMENT = "agreement"
    EXECUTION = "execution"
    FAILED = "failed"


@dataclass
class NegotiationMessage:
    """A message in negotiation."""
    from_agent: str
    to_agent: str
    message_type: str  # "PROPOSAL", "COUNTER_OFFER", "ACCEPT", "REJECT", "QUESTION"
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: str = ""


@dataclass
class NegotiationSession:
    """Represents an active negotiation."""
    session_id: str
    initiator: str
    responder: str
    subject: str
    phase: NegotiationPhase = NegotiationPhase.PROPOSAL
    messages: List[NegotiationMessage] = field(default_factory=list)
    initiated_at: datetime = field(default_factory=datetime.now)
    agreement: Optional[Any] = None
    agreement_time: Optional[datetime] = None
    max_rounds: int = 5
    current_round: int = 0


class NegotiationProtocol:
    """
    Manages negotiation between agents.
    
    Features:
    - Multi-round negotiation
    - Phase-based protocol
    - Counter-offers and refinement
    - Agreement recording
    - Learning from negotiations
    """
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.active_sessions: Dict[str, NegotiationSession] = {}
        self.completed_negotiations: List[NegotiationSession] = []
        self.lock = threading.RLock()
    
    def initiate_negotiation(self, initiator: str, responder: str, subject: str, 
                            initial_proposal: Any) -> NegotiationSession:
        """Start a negotiation."""
        with self.lock:
            import uuid
            session_id = str(uuid.uuid4())
            
            session = NegotiationSession(
                session_id=session_id,
                initiator=initiator,
                responder=responder,
                subject=subject,
                phase=NegotiationPhase.PROPOSAL
            )
            
            # Add initial proposal
            msg = NegotiationMessage(
                from_agent=initiator,
                to_agent=responder,
                message_type="PROPOSAL",
                content=initial_proposal,
                reasoning=f"Initial proposal for {subject}"
            )
            session.messages.append(msg)
            
            self.active_sessions[session_id] = session
            
            if self.event_bus:
                try:
                    from .events import Event, EventType
                    ev = Event(
                        type=EventType.AGENT_NEGOTIATION_STARTED,
                        source="NegotiationProtocol",
                        payload={
                            "session_id": session_id,
                            "initiator": initiator,
                            "responder": responder,
                            "subject": subject
                        }
                    )
                    self.event_bus.publish(ev)
                except Exception:
                    logger.warning("Erro ao publicar evento de sessão de negociação", exc_info=True)

            return session
    
    def send_message(self, session_id: str, from_agent: str, message_type: str,
                    content: Any, reasoning: str = "") -> bool:
        """Send a message in negotiation."""
        with self.lock:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Verify sender is one of the parties
            if from_agent not in [session.initiator, session.responder]:
                return False
            
            # Update phase based on message type
            if message_type == "PROPOSAL" and session.phase == NegotiationPhase.PROPOSAL:
                session.phase = NegotiationPhase.DISCUSSION
            elif message_type == "COUNTER_OFFER":
                session.phase = NegotiationPhase.NEGOTIATION
                session.current_round += 1
            elif message_type == "ACCEPT":
                session.phase = NegotiationPhase.AGREEMENT
                session.agreement = content
                session.agreement_time = datetime.now()
            elif message_type == "REJECT":
                session.phase = NegotiationPhase.FAILED
            
            # Add message
            msg = NegotiationMessage(
                from_agent=from_agent,
                to_agent=session.responder if from_agent == session.initiator else session.initiator,
                message_type=message_type,
                content=content,
                reasoning=reasoning
            )
            session.messages.append(msg)
            
            # Check if negotiation is complete
            if session.phase in [NegotiationPhase.AGREEMENT, NegotiationPhase.FAILED]:
                self._finalize_negotiation(session_id)
            elif session.current_round >= session.max_rounds:
                session.phase = NegotiationPhase.FAILED
                self._finalize_negotiation(session_id)
            
            return True
    
    def _finalize_negotiation(self, session_id: str):
        """Move negotiation to completed list."""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            self.completed_negotiations.append(session)
            
            if self.event_bus:
                try:
                    from .events import Event, EventType
                    if session.phase == NegotiationPhase.AGREEMENT:
                        ev_type = EventType.AGENT_NEGOTIATION_SUCCESS
                    else:
                        ev_type = EventType.AGENT_NEGOTIATION_FAILED
                    
                    ev = Event(
                        type=ev_type,
                        source="NegotiationProtocol",
                        payload={
                            "session_id": session_id,
                            "initiator": session.initiator,
                            "responder": session.responder,
                            "agreement": str(session.agreement) if session.agreement else None
                        }
                    )
                    self.event_bus.publish(ev)
                except Exception:
                    logger.warning("Erro ao publicar evento de finalização de negociação", exc_info=True)
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get status of a negotiation session."""
        with self.lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return None
            
            return {
                "session_id": session_id,
                "initiator": session.initiator,
                "responder": session.responder,
                "subject": session.subject,
                "phase": session.phase.value,
                "current_round": session.current_round,
                "max_rounds": session.max_rounds,
                "message_count": len(session.messages),
                "agreement": str(session.agreement) if session.agreement else None
            }
    
    def get_negotiation_history(self, agent_id: str) -> List[Dict]:
        """Get negotiation history for an agent."""
        with self.lock:
            history = []
            for session in self.completed_negotiations:
                if agent_id in [session.initiator, session.responder]:
                    history.append({
                        "session_id": session.session_id,
                        "role": "initiator" if agent_id == session.initiator else "responder",
                        "other_party": session.responder if agent_id == session.initiator else session.initiator,
                        "subject": session.subject,
                        "phase": session.phase.value,
                        "rounds": session.current_round,
                        "agreement": str(session.agreement) if session.agreement else None,
                        "success": session.phase == NegotiationPhase.AGREEMENT
                    })
            
            return sorted(history, key=lambda x: x["success"], reverse=True)
    
    def get_negotiation_statistics(self) -> Dict:
        """Get statistics about negotiations."""
        with self.lock:
            total = len(self.completed_negotiations)
            successful = sum(1 for s in self.completed_negotiations if s.phase == NegotiationPhase.AGREEMENT)
            
            subjects = {}
            for session in self.completed_negotiations:
                subjects[session.subject] = subjects.get(session.subject, 0) + 1
            
            return {
                "total_negotiations": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "active_sessions": len(self.active_sessions),
                "avg_rounds": sum(s.current_round for s in self.completed_negotiations) / total if total > 0 else 0,
                "subjects": subjects
            }
