"""
ORION Advanced Security System
===============================
7-layer defense architecture for AI agents.

Inspired by: OWASP Agentic Top 10 (2026), LLM Guard, NeMo Guardrails
Layers:
1. Input Sanitization
2. Prompt Injection Detection
3. Output Validation
4. Tool Permission Control
5. Audit Trail
6. Anomaly Detection
7. Rate Limiting & Quotas
"""

import re
import time
import uuid
import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger("orion.security")


class SecurityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    ESCALATE = "escalate"
    LOG_ONLY = "log_only"


class ThreatType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_EXFILTRATION = "data_exfiltration"
    TOOL_MISUSE = "tool_misuse"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MEMORY_POISONING = "memory_poisoning"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityEvent:
    """Security event record"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    threat_type: ThreatType = ThreatType.PROMPT_INJECTION
    severity: SecurityLevel = SecurityLevel.MEDIUM
    action_taken: SecurityAction = SecurityAction.ALLOW
    details: Dict[str, Any] = field(default_factory=dict)
    source: str = "input"
    agent_id: str = "system"
    timestamp: float = field(default_factory=time.time)
    blocked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "threat_type": self.threat_type.value,
            "severity": self.severity.value,
            "action_taken": self.action_taken.value,
            "details": self.details,
            "source": self.source,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "blocked": self.blocked
        }


@dataclass
class ToolPermission:
    """Tool permission configuration"""
    tool_name: str = ""
    allowed_agents: List[str] = field(default_factory=list)
    max_calls_per_minute: int = 10
    max_calls_per_hour: int = 100
    requires_approval: bool = False
    risk_level: SecurityLevel = SecurityLevel.LOW


@dataclass
class RateLimitEntry:
    """Rate limit tracking"""
    calls_this_minute: int = 0
    calls_this_hour: int = 0
    last_minute_reset: float = field(default_factory=time.time)
    last_hour_reset: float = field(default_factory=time.time)


class Layer1InputSanitization:
    """Layer 1: Input sanitization and validation"""
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"data:text/html",
        r"vbscript:",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"url\s*\(",
        r"@import",
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"('\s*or\s+')",
        r"(;\s*drop\s+table)",
        r"(;\s*delete\s+from)",
        r"(;\s*update\s+.*set)",
        r"(union\s+select)",
        r"(--\s*$)",
        r"(#\s*$)",
    ]
    
    def sanitize(self, content: str) -> Tuple[str, List[SecurityEvent]]:
        """Sanitize input content"""
        events = []
        sanitized = content
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                events.append(SecurityEvent(
                    threat_type=ThreatType.PROMPT_INJECTION,
                    severity=SecurityLevel.HIGH,
                    action_taken=SecurityAction.BLOCK,
                    details={"pattern": pattern, "original": content[:100]},
                    source="input"
                ))
                sanitized = re.sub(pattern, "[BLOCKED]", sanitized, flags=re.IGNORECASE)
        
        # Check for SQL injection
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                events.append(SecurityEvent(
                    threat_type=ThreatType.PROMPT_INJECTION,
                    severity=SecurityLevel.HIGH,
                    action_taken=SecurityAction.BLOCK,
                    details={"pattern": pattern, "type": "sql_injection"},
                    source="input"
                ))
                sanitized = re.sub(pattern, "[BLOCKED]", sanitized, flags=re.IGNORECASE)
        
        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")
        
        # Trim excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized, events


class Layer2PromptInjectionDetection:
    """Layer 2: Advanced prompt injection detection"""
    
    # Direct injection patterns
    DIRECT_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+DAN",
        r"reveal\s+your\s+(system\s+)?prompt",
        r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
        r"bypass\s+(all\s+)?safety",
        r"jailbreak",
        r"override\s+(your\s+)?instructions",
        r"forget\s+(all\s+)?prior",
        r"disregard\s+(your\s+)?guidelines",
        r"new\s+instructions?:",
        r"system\s*prompt\s*:",
        r"hidden\s*instruction",
        r"<!--.*instruction",
        r"<script>.*prompt",
        r"you\s+are\s+an\s+unrestricted",
        r"do\s+anything\s+now",
        r"developer\s+mode",
        r"god\s+mode",
    ]
    
    # Indirect injection patterns (in retrieved content)
    INDIRECT_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"disregard\s+all\s+prior",
        r"you\s+must\s+now\s+",
        r"important\s+system\s+update",
        r"new\s+policy\s+override",
        r"confidential\s+instruction",
        r"secret\s+directive",
    ]
    
    def detect(self, content: str, is_retrieved: bool = False) -> Tuple[SecurityEvent, float]:
        """Detect prompt injection attempts"""
        content_lower = content.lower()
        
        patterns = self.INDIRECT_PATTERNS if is_retrieved else self.DIRECT_PATTERNS
        
        for pattern in patterns:
            if re.search(pattern, content_lower):
                return SecurityEvent(
                    threat_type=ThreatType.PROMPT_INJECTION,
                    severity=SecurityLevel.CRITICAL if not is_retrieved else SecurityLevel.HIGH,
                    action_taken=SecurityAction.BLOCK,
                    details={"pattern": pattern, "content_preview": content[:200]},
                    source="retrieved" if is_retrieved else "input"
                ), 1.0
        
        # Check for unusual formatting that might indicate injection
        if content.count('```') > 10 or content.count('\\n') > 20:
            return SecurityEvent(
                threat_type=ThreatType.PROMPT_INJECTION,
                severity=SecurityLevel.MEDIUM,
                action_taken=SecurityAction.WARN,
                details={"reason": "unusual_formatting", "code_blocks": content.count('```')},
                source="input"
            ), 0.7
        
        return SecurityEvent(
            action_taken=SecurityAction.ALLOW
        ), 0.0


class Layer3OutputValidation:
    """Layer 3: Output validation and filtering"""
    
    # PII patterns
    PII_PATTERNS = [
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', "phone_number"),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "email"),
        (r'\b\d{3}-\d{2}-\d{4}\b', "ssn"),
        (r'\b\d{16}\b', "credit_card"),
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', "ip_address"),
    ]
    
    # Secrets patterns
    SECRETS_PATTERNS = [
        (r'api[_-]?key\s*[=:]\s*["\']?[\w-]+', "api_key"),
        (r'secret\s*[=:]\s*["\']?[\w-]+', "secret"),
        (r'password\s*[=:]\s*["\']?[\w-]+', "password"),
        (r'token\s*[=:]\s*["\']?[\w-]+', "token"),
        (r'aws[_-]?(?:access|secret)[_-]?(?:key)?\s*[=:]\s*["\']?[\w-]+', "aws_key"),
    ]
    
    def validate(self, content: str) -> Tuple[str, List[SecurityEvent]]:
        """Validate and filter output content"""
        events = []
        filtered = content
        
        # Check for PII
        for pattern, pii_type in self.PII_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                events.append(SecurityEvent(
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    severity=SecurityLevel.HIGH,
                    action_taken=SecurityAction.WARN,
                    details={"pii_type": pii_type, "position": match.start()},
                    source="output"
                ))
                # Mask PII
                masked = match.group()[:3] + "***" + match.group()[-2:]
                filtered = filtered.replace(match.group(), masked)
        
        # Check for secrets
        for pattern, secret_type in self.SECRETS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                events.append(SecurityEvent(
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    severity=SecurityLevel.CRITICAL,
                    action_taken=SecurityAction.BLOCK,
                    details={"secret_type": secret_type},
                    source="output"
                ))
                filtered = re.sub(pattern, "[SECRET REDACTED]", filtered, flags=re.IGNORECASE)
        
        return filtered, events


class Layer4ToolPermissionControl:
    """Layer 4: Tool permission and access control"""
    
    def __init__(self):
        self.permissions: Dict[str, ToolPermission] = {}
        self.call_counts: Dict[str, Dict[str, RateLimitEntry]] = defaultdict(
            lambda: defaultdict(RateLimitEntry)
        )
        self._lock = threading.Lock()
    
    def register_tool(self, permission: ToolPermission) -> None:
        """Register tool permission"""
        self.permissions[permission.tool_name] = permission
    
    def check_permission(
        self,
        tool_name: str,
        agent_id: str,
        call_count_key: Optional[str] = None
    ) -> Tuple[SecurityAction, str]:
        """Check if agent can call tool"""
        with self._lock:
            # Check if tool exists
            if tool_name not in self.permissions:
                return SecurityAction.ALLOW, "tool_not_registered"
            
            permission = self.permissions[tool_name]
            
            # Check agent permission
            if permission.allowed_agents and agent_id not in permission.allowed_agents:
                return SecurityAction.BLOCK, "agent_not_authorized"
            
            # Check rate limits
            key = call_count_key or agent_id
            entry = self.call_counts[tool_name][key]
            now = time.time()
            
            # Reset minute counter
            if now - entry.last_minute_reset >= 60:
                entry.calls_this_minute = 0
                entry.last_minute_reset = now
            
            # Reset hour counter
            if now - entry.last_hour_reset >= 3600:
                entry.calls_this_hour = 0
                entry.last_hour_reset = now
            
            # Check limits
            if entry.calls_this_minute >= permission.max_calls_per_minute:
                return SecurityAction.BLOCK, "minute_rate_limit_exceeded"
            
            if entry.calls_this_hour >= permission.max_calls_per_hour:
                return SecurityAction.BLOCK, "hour_rate_limit_exceeded"
            
            # Update counters
            entry.calls_this_minute += 1
            entry.calls_this_hour += 1
            
            # Check if approval required
            if permission.requires_approval:
                return SecurityAction.ESCALATE, "approval_required"
            
            return SecurityAction.ALLOW, "ok"
    
    def get_usage_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get tool usage statistics"""
        with self._lock:
            if tool_name not in self.call_counts:
                return {"tool": tool_name, "agents": {}}
            
            stats = {"tool": tool_name, "agents": {}}
            for agent_id, entry in self.call_counts[tool_name].items():
                stats["agents"][agent_id] = {
                    "calls_this_minute": entry.calls_this_minute,
                    "calls_this_hour": entry.calls_this_hour
                }
            return stats


class Layer5AuditTrail:
    """Layer 5: Comprehensive audit trail"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("orion_audit")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.events: List[SecurityEvent] = []
        self._lock = threading.Lock()
        
        # Load existing events
        self._load_events()
    
    def _load_events(self) -> None:
        """Load audit events from storage"""
        try:
            audit_file = self.storage_path / "audit_trail.json"
            if audit_file.exists():
                data = json.loads(audit_file.read_text(encoding="utf-8"))
                self.events = [SecurityEvent(**e) for e in data.get("events", [])]
        except Exception as e:
            logger.error(f"Error loading audit trail: {e}")
    
    def _save_events(self) -> None:
        """Save audit events to storage"""
        try:
            audit_file = self.storage_path / "audit_trail.json"
            # Keep only last 10000 events
            if len(self.events) > 10000:
                self.events = self.events[-10000:]
            
            data = {
                "events": [e.to_dict() for e in self.events],
                "last_saved": time.time()
            }
            audit_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving audit trail: {e}")
    
    def log_event(self, event: SecurityEvent) -> None:
        """Log a security event"""
        with self._lock:
            self.events.append(event)
            if len(self.events) % 100 == 0:  # Save every 100 events
                self._save_events()
    
    def get_events(
        self,
        threat_type: Optional[ThreatType] = None,
        severity: Optional[SecurityLevel] = None,
        agent_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get filtered audit events"""
        cutoff = time.time() - (hours * 3600)
        results = []
        
        for event in reversed(self.events):  # Most recent first
            if event.timestamp < cutoff:
                continue
            
            if threat_type and event.threat_type != threat_type:
                continue
            
            if severity and event.severity != severity:
                continue
            
            if agent_id and event.agent_id != agent_id:
                continue
            
            results.append(event)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get audit statistics"""
        cutoff = time.time() - (hours * 3600)
        recent_events = [e for e in self.events if e.timestamp >= cutoff]
        
        # Count by threat type
        threat_counts = defaultdict(int)
        for event in recent_events:
            threat_counts[event.threat_type.value] += 1
        
        # Count by severity
        severity_counts = defaultdict(int)
        for event in recent_events:
            severity_counts[event.severity.value] += 1
        
        # Count blocked
        blocked_count = sum(1 for e in recent_events if e.blocked)
        
        return {
            "total_events": len(recent_events),
            "blocked_events": blocked_count,
            "threat_counts": dict(threat_counts),
            "severity_counts": dict(severity_counts),
            "period_hours": hours
        }


class Layer6AnomalyDetection:
    """Layer 6: Anomaly detection for unusual patterns"""
    
    def __init__(self):
        self.baselines: Dict[str, Dict[str, float]] = {}
        self.alerts: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def update_baseline(self, agent_id: str, metrics: Dict[str, float]) -> None:
        """Update baseline metrics for agent"""
        with self._lock:
            if agent_id not in self.baselines:
                self.baselines[agent_id] = metrics
            else:
                # Exponential moving average
                for key, value in metrics.items():
                    if key in self.baselines[agent_id]:
                        self.baselines[agent_id][key] = (
                            0.7 * self.baselines[agent_id][key] + 0.3 * value
                        )
                    else:
                        self.baselines[agent_id][key] = value
    
    def detect_anomaly(
        self,
        agent_id: str,
        metric: str,
        value: float,
        threshold: float = 2.0
    ) -> bool:
        """Detect if metric is anomalous"""
        with self._lock:
            if agent_id not in self.baselines:
                return False
            
            baseline = self.baselines[agent_id].get(metric)
            if baseline is None:
                return False
            
            # Simple z-score detection
            # In production, use more sophisticated methods
            if abs(value - baseline) > threshold * baseline:
                self.alerts.append({
                    "agent_id": agent_id,
                    "metric": metric,
                    "value": value,
                    "baseline": baseline,
                    "timestamp": time.time()
                })
                return True
            
            return False
    
    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent anomaly alerts"""
        cutoff = time.time() - (hours * 3600)
        return [a for a in self.alerts if a["timestamp"] >= cutoff]


class Layer7RateLimiting:
    """Layer 7: Rate limiting and quotas"""
    
    def __init__(self):
        self.quotas: Dict[str, Dict[str, int]] = {
            "default": {
                "requests_per_minute": 30,
                "requests_per_hour": 500,
                "tokens_per_minute": 100000,
                "tokens_per_hour": 2000000
            }
        }
        self.usage: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._lock = threading.Lock()
    
    def set_quota(self, agent_id: str, quota: Dict[str, int]) -> None:
        """Set quota for agent"""
        with self._lock:
            self.quotas[agent_id] = quota
    
    def check_quota(
        self,
        agent_id: str,
        quota_type: str = "requests_per_minute"
    ) -> Tuple[bool, int, int]:
        """Check if agent is within quota"""
        with self._lock:
            # Get quota
            quota = self.quotas.get(agent_id, self.quotas["default"])
            limit = quota.get(quota_type, 0)
            
            # Get usage
            now = time.time()
            if quota_type == "requests_per_minute":
                cutoff = now - 60
            elif quota_type == "requests_per_hour":
                cutoff = now - 3600
            elif quota_type == "tokens_per_minute":
                cutoff = now - 60
            elif quota_type == "tokens_per_hour":
                cutoff = now - 3600
            else:
                cutoff = now - 60
            
            usage_count = sum(1 for t in self.usage[agent_id][quota_type] if t >= cutoff)
            
            return usage_count < limit, usage_count, limit
    
    def record_usage(self, agent_id: str, quota_type: str, count: int = 1) -> None:
        """Record usage"""
        with self._lock:
            now = time.time()
            for _ in range(count):
                self.usage[agent_id][quota_type].append(now)
            
            # Cleanup old entries
            cutoff = now - 7200  # Keep 2 hours
            self.usage[agent_id][quota_type] = [
                t for t in self.usage[agent_id][quota_type] if t >= cutoff
            ]


class AdvancedSecuritySystem:
    """
    Advanced 7-layer security system for AI agents.
    
    Layers:
    1. Input Sanitization
    2. Prompt Injection Detection
    3. Output Validation
    4. Tool Permission Control
    5. Audit Trail
    6. Anomaly Detection
    7. Rate Limiting & Quotas
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("orion_security")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize layers
        self.layer1 = Layer1InputSanitization()
        self.layer2 = Layer2PromptInjectionDetection()
        self.layer3 = Layer3OutputValidation()
        self.layer4 = Layer4ToolPermissionControl()
        self.layer5 = Layer5AuditTrail(self.storage_path / "audit")
        self.layer6 = Layer6AnomalyDetection()
        self.layer7 = Layer7RateLimiting()
        
        # Security state
        self.security_events: List[SecurityEvent] = []
        self.blocked_ips: Set[str] = set()
        self.blocked_agents: Set[str] = set()
        
        # Configuration
        self.enabled = True
        self.strict_mode = False  # Block on warnings in strict mode
        
        logger.info("Advanced Security System initialized with 7 layers")
    
    def scan_input(
        self,
        content: str,
        agent_id: str = "system",
        is_retrieved: bool = False
    ) -> Tuple[str, bool, List[SecurityEvent]]:
        """
        Scan input through all security layers.
        Returns: (sanitized_content, allowed, events)
        """
        if not self.enabled:
            return content, True, []
        
        all_events = []
        sanitized = content
        
        # Layer 1: Input Sanitization
        sanitized, layer1_events = self.layer1.sanitize(sanitized)
        all_events.extend(layer1_events)
        
        # Layer 2: Prompt Injection Detection
        injection_event, confidence = self.layer2.detect(sanitized, is_retrieved)
        if confidence > 0.5:
            all_events.append(injection_event)
        
        # Check if should block
        blocked = any(e.action_taken == SecurityAction.BLOCK for e in all_events)
        
        # Log events
        for event in all_events:
            event.agent_id = agent_id
            self.layer5.log_event(event)
        
        # Layer 6: Anomaly Detection
        self.layer6.update_baseline(agent_id, {
            "input_length": len(content),
            "security_events": len(all_events)
        })
        
        # Layer 7: Rate Limiting
        within_quota, current, limit = self.layer7.check_quota(agent_id)
        if not within_quota:
            blocked = True
            all_events.append(SecurityEvent(
                threat_type=ThreatType.TOOL_MISUSE,
                severity=SecurityLevel.HIGH,
                action_taken=SecurityAction.BLOCK,
                details={"quota_exceeded": True, "current": current, "limit": limit},
                source="rate_limiter",
                agent_id=agent_id
            ))
        
        return sanitized, not blocked, all_events
    
    def scan_output(
        self,
        content: str,
        agent_id: str = "system"
    ) -> Tuple[str, bool, List[SecurityEvent]]:
        """
        Scan output through security layers.
        Returns: (filtered_content, allowed, events)
        """
        if not self.enabled:
            return content, True, []
        
        all_events = []
        
        # Layer 3: Output Validation
        filtered, layer3_events = self.layer3.validate(content)
        all_events.extend(layer3_events)
        
        # Check if should block
        blocked = any(e.action_taken == SecurityAction.BLOCK for e in all_events)
        
        # Log events
        for event in all_events:
            event.agent_id = agent_id
            event.source = "output"
            self.layer5.log_event(event)
        
        return filtered, not blocked, all_events
    
    def check_tool_permission(
        self,
        tool_name: str,
        agent_id: str
    ) -> Tuple[SecurityAction, str]:
        """Check tool permission"""
        return self.layer4.check_permission(tool_name, agent_id)
    
    def register_tool_permission(self, permission: ToolPermission) -> None:
        """Register tool permission"""
        self.layer4.register_tool(permission)
    
    def block_agent(self, agent_id: str, reason: str) -> None:
        """Block an agent"""
        self.blocked_agents.add(agent_id)
        logger.warning(f"Blocked agent {agent_id}: {reason}")
    
    def unblock_agent(self, agent_id: str) -> None:
        """Unblock an agent"""
        self.blocked_agents.discard(agent_id)
    
    def is_agent_blocked(self, agent_id: str) -> bool:
        """Check if agent is blocked"""
        return agent_id in self.blocked_agents
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        return {
            "enabled": self.enabled,
            "strict_mode": self.strict_mode,
            "blocked_agents": list(self.blocked_agents),
            "audit_statistics": self.layer5.get_statistics(),
            "recent_alerts": self.layer6.get_alerts(),
            "tool_usage": {
                tool: self.layer4.get_usage_stats(tool)
                for tool in self.layer4.permissions
            }
        }
    
    def get_events(
        self,
        threat_type: Optional[ThreatType] = None,
        severity: Optional[SecurityLevel] = None,
        agent_id: Optional[str] = None,
        hours: int = 24
    ) -> List[SecurityEvent]:
        """Get security events"""
        return self.layer5.get_events(threat_type, severity, agent_id, hours)
    
    def set_strict_mode(self, strict: bool) -> None:
        """Enable/disable strict mode"""
        self.strict_mode = strict
        logger.info(f"Strict mode {'enabled' if strict else 'disabled'}")


# Global instance
_security_system_instance: Optional[AdvancedSecuritySystem] = None

def get_security_system(storage_path: Optional[Path] = None) -> AdvancedSecuritySystem:
    """Get or create global security system instance"""
    global _security_system_instance
    if _security_system_instance is None:
        _security_system_instance = AdvancedSecuritySystem(storage_path)
    return _security_system_instance
