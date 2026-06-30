"""
ORION Human-in-the-Loop
=======================
Approval gates and human oversight for high-stakes agent actions.

Inspired by: HumanLayer, Temporal HITL, OpenAI Agents SDK (2026)
Features:
- Risk-based approval routing
- Durable suspension and resumption
- Confidence threshold gates
- Multi-channel notifications
- Audit trail
"""

import time
import uuid
import json
import hashlib
import hmac
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class RiskTier(str, Enum):
    LOW = "low"           # Read-only, reversible
    MEDIUM = "medium"     # Write operations, external messages
    HIGH = "high"         # Financial, legal, compliance
    CRITICAL = "critical" # Irreversible, high-blast-radius


class ActionType(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEND = "send"
    EXECUTE = "execute"
    FINANCIAL = "financial"


@dataclass
class ApprovalRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    agent_id: str = ""
    action_type: ActionType = ActionType.READ
    risk_tier: RiskTier = RiskTier.LOW
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    reviewer: Optional[str] = None
    review_comment: str = ""
    payload_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type.value,
            "risk_tier": self.risk_tier.value,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "status": self.status.value,
            "created_at": self.created_at,
            "reviewer": self.reviewer,
            "review_comment": self.review_comment,
        }


@dataclass
class ApprovalDecision:
    request_id: str
    decision: ApprovalStatus
    reviewer: str
    comment: str = ""
    edited_payload: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    signature: str = ""


@dataclass
class HITLConfig:
    confidence_threshold: float = 0.85
    auto_approve_low_risk: bool = True
    timeout_seconds: float = 300.0
    require_reasoning: bool = True
    max_pending_approvals: int = 50


class RiskClassifier:
    """Classifies actions by risk level"""
    
    TOOL_RISK_MAP = {
        "read": RiskTier.LOW,
        "search": RiskTier.LOW,
        "list": RiskTier.LOW,
        "create": RiskTier.MEDIUM,
        "update": RiskTier.MEDIUM,
        "write": RiskTier.MEDIUM,
        "send_email": RiskTier.HIGH,
        "send_message": RiskTier.HIGH,
        "delete": RiskTier.HIGH,
        "execute_code": RiskTier.HIGH,
        "transfer": RiskTier.CRITICAL,
        "deploy": RiskTier.CRITICAL,
        "purchase": RiskTier.CRITICAL,
    }
    
    def classify(self, tool_name: str, parameters: Dict[str, Any]) -> Tuple[RiskTier, ActionType]:
        tool_lower = tool_name.lower()
        
        risk = self.TOOL_RISK_MAP.get(tool_lower, RiskTier.MEDIUM)
        
        if any(kw in tool_lower for kw in ["delete", "remove", "destroy"]):
            action_type = ActionType.DELETE
            risk = max(risk, RiskTier.HIGH, key=lambda r: list(RiskTier).index(r))
        elif any(kw in tool_lower for kw in ["send", "email", "message", "post"]):
            action_type = ActionType.SEND
            risk = max(risk, RiskTier.HIGH, key=lambda r: list(RiskTier).index(r))
        elif any(kw in tool_lower for kw in ["transfer", "purchase", "pay", "buy"]):
            action_type = ActionType.FINANCIAL
            risk = RiskTier.CRITICAL
        elif any(kw in tool_lower for kw in ["execute", "run", "deploy"]):
            action_type = ActionType.EXECUTE
            risk = max(risk, RiskTier.HIGH, key=lambda r: list(RiskTier).index(r))
        elif any(kw in tool_lower for kw in ["create", "add", "new"]):
            action_type = ActionType.CREATE
        elif any(kw in tool_lower for kw in ["update", "modify", "edit", "change"]):
            action_type = ActionType.UPDATE
        else:
            action_type = ActionType.READ
        
        return risk, action_type
    
    def needs_approval(self, risk_tier: RiskTier, confidence: float,
                       config: HITLConfig) -> bool:
        if risk_tier in [RiskTier.CRITICAL, RiskTier.HIGH]:
            return True
        
        if risk_tier == RiskTier.MEDIUM and confidence < config.confidence_threshold:
            return True
        
        if risk_tier == RiskTier.LOW and not config.auto_approve_low_risk:
            return True
        
        return False


class PayloadLocker:
    """Cryptographic payload locking for approved actions"""
    
    def __init__(self, secret_key: str = "orion-hitl-secret"):
        self.secret_key = secret_key
    
    def lock(self, payload: Dict[str, Any]) -> str:
        payload_str = json.dumps(payload, sort_keys=True)
        return hmac.new(
            self.secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify(self, payload: Dict[str, Any], signature: str) -> bool:
        expected = self.lock(payload)
        return hmac.compare_digest(expected, signature)


class NotificationChannel:
    """Base class for notification channels"""
    
    def send(self, request: ApprovalRequest, message: str) -> bool:
        raise NotImplementedError


class ConsoleNotification(NotificationChannel):
    """Console-based notification"""
    
    def send(self, request: ApprovalRequest, message: str) -> bool:
        print(f"\n{'='*60}")
        print(f"APPROVAL REQUIRED: {request.request_id}")
        print(f"Tool: {request.tool_name}")
        print(f"Risk: {request.risk_tier.value}")
        print(f"Confidence: {request.confidence:.2f}")
        print(f"Reasoning: {request.reasoning}")
        print(f"Parameters: {json.dumps(request.parameters, indent=2)}")
        print(f"{'='*60}\n")
        return True


class ApprovalQueue:
    """Manages pending approval requests"""
    
    def __init__(self, config: Optional[HITLConfig] = None):
        self.config = config or HITLConfig()
        self.pending: Dict[str, ApprovalRequest] = {}
        self.completed: List[ApprovalRequest] = []
        self.locker = PayloadLocker()
        self.notifications: List[NotificationChannel] = []
    
    def add_notification_channel(self, channel: NotificationChannel):
        self.notifications.append(channel)
    
    def submit(self, request: ApprovalRequest) -> str:
        if len(self.pending) >= self.config.max_pending_approvals:
            raise RuntimeError("Too many pending approvals")
        
        payload_str = json.dumps(request.parameters, sort_keys=True)
        request.payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        
        self.pending[request.request_id] = request
        
        self._notify(request)
        
        return request.request_id
    
    def decide(self, decision: ApprovalDecision) -> bool:
        request = self.pending.get(decision.request_id)
        if not request:
            return False
        
        request.status = decision.decision
        request.reviewer = decision.reviewer
        request.review_comment = decision.comment
        request.updated_at = time.time()
        
        if decision.edited_payload:
            if self.locker.verify(decision.edited_payload, decision.signature or ""):
                request.parameters = decision.edited_payload
            else:
                return False
        
        self.completed.append(request)
        del self.pending[decision.request_id]
        
        return True
    
    def approve(self, request_id: str, reviewer: str, comment: str = "") -> bool:
        return self.decide(ApprovalDecision(
            request_id=request_id,
            decision=ApprovalStatus.APPROVED,
            reviewer=reviewer,
            comment=comment
        ))
    
    def reject(self, request_id: str, reviewer: str, comment: str = "") -> bool:
        return self.decide(ApprovalDecision(
            request_id=request_id,
            decision=ApprovalStatus.REJECTED,
            reviewer=reviewer,
            comment=comment
        ))
    
    def check_timeouts(self):
        now = time.time()
        timed_out = []
        
        for request_id, request in self.pending.items():
            if now - request.created_at > self.config.timeout_seconds:
                request.status = ApprovalStatus.TIMED_OUT
                request.updated_at = now
                self.completed.append(request)
                timed_out.append(request_id)
        
        for request_id in timed_out:
            del self.pending[request_id]
    
    def _notify(self, request: ApprovalRequest):
        risk_emoji = {
            RiskTier.LOW: "🟢",
            RiskTier.MEDIUM: "🟡",
            RiskTier.HIGH: "🟠",
            RiskTier.CRITICAL: "🔴"
        }
        
        message = (
            f"{risk_emoji.get(request.risk_tier, '⚪')} "
            f"Action '{request.tool_name}' requires approval "
            f"(Risk: {request.risk_tier.value}, Confidence: {request.confidence:.2f})"
        )
        
        for channel in self.notifications:
            try:
                channel.send(request, message)
            except Exception:
                pass
    
    def get_pending(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.pending.values()]
    
    def get_completed(self, count: int = 50) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.completed[-count:]]


class HumanInTheLoop:
    """Main HITL system"""
    
    def __init__(self, config: Optional[HITLConfig] = None):
        self.config = config or HITLConfig()
        self.classifier = RiskClassifier()
        self.queue = ApprovalQueue(config)
        self.history: List[Dict[str, Any]] = []
    
    def check_action(self, agent_id: str, tool_name: str,
                     parameters: Dict[str, Any], confidence: float,
                     reasoning: str = "") -> Tuple[bool, Optional[str]]:
        risk_tier, action_type = self.classifier.classify(tool_name, parameters)
        
        if not self.classifier.needs_approval(risk_tier, confidence, self.config):
            return True, None
        
        request = ApprovalRequest(
            agent_id=agent_id,
            action_type=action_type,
            risk_tier=risk_tier,
            tool_name=tool_name,
            parameters=parameters,
            reasoning=reasoning,
            confidence=confidence
        )
        
        request_id = self.queue.submit(request)
        
        return False, request_id
    
    def approve(self, request_id: str, reviewer: str, comment: str = "") -> bool:
        success = self.queue.approve(request_id, reviewer, comment)
        if success:
            self.history.append({
                "request_id": request_id,
                "decision": "approved",
                "reviewer": reviewer,
                "timestamp": time.time()
            })
        return success
    
    def reject(self, request_id: str, reviewer: str, comment: str = "") -> bool:
        success = self.queue.reject(request_id, reviewer, comment)
        if success:
            self.history.append({
                "request_id": request_id,
                "decision": "rejected",
                "reviewer": reviewer,
                "timestamp": time.time()
            })
        return success
    
    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        if request_id in self.queue.pending:
            return self.queue.pending[request_id].to_dict()
        for req in self.queue.completed:
            if req.request_id == request_id:
                return req.to_dict()
        return None
    
    def add_notification_channel(self, channel: NotificationChannel):
        self.queue.add_notification_channel(channel)
    
    def get_stats(self) -> Dict[str, Any]:
        total = len(self.history)
        approved = sum(1 for h in self.history if h["decision"] == "approved")
        rejected = sum(1 for h in self.history if h["decision"] == "rejected")
        
        return {
            "total_decisions": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": round(approved / total, 3) if total > 0 else 0,
            "pending": len(self.queue.pending),
            "completed": len(self.queue.completed),
            "config": {
                "confidence_threshold": self.config.confidence_threshold,
                "auto_approve_low_risk": self.config.auto_approve_low_risk,
                "timeout_seconds": self.config.timeout_seconds,
            }
        }
