"""
ORION Guardrails System
=======================
Security and safety guardrails for AI agents.

Inspired by: LLM Guard, NeMo Guardrails, Guardrails AI (2026)
Features:
- Input validation and sanitization
- Prompt injection detection
- Output filtering (toxicity, PII, secrets)
- Policy enforcement
- Audit trail
"""

import re
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanResult(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class ScanEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    scanner: str = ""
    result: ScanResult = ScanResult.PASS
    risk_level: RiskLevel = RiskLevel.LOW
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PolicyRule:
    rule_id: str = ""
    name: str = ""
    description: str = ""
    pattern: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    action: str = "warn"  # warn, block, escalate
    enabled: bool = True


@dataclass
class GuardrailsResult:
    allowed: bool
    scans: List[ScanEvent]
    risk_level: RiskLevel
    message: str = ""
    sanitized_content: str = ""
    duration_ms: float = 0.0


class PromptInjectionScanner:
    """Detects prompt injection attempts"""
    
    INJECTION_PATTERNS = [
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
    ]
    
    def scan(self, content: str) -> ScanEvent:
        content_lower = content.lower()
        
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, content_lower):
                return ScanEvent(
                    scanner="prompt_injection",
                    result=ScanResult.BLOCK,
                    risk_level=RiskLevel.HIGH,
                    message=f"Prompt injection detected: {pattern}",
                    details={"pattern": pattern, "content_preview": content[:100]}
                )
        
        if self._has_suspicious_encoding(content):
            return ScanEvent(
                scanner="prompt_injection",
                result=ScanResult.WARN,
                risk_level=RiskLevel.MEDIUM,
                message="Suspicious encoding detected",
                details={"content_preview": content[:100]}
            )
        
        return ScanEvent(
            scanner="prompt_injection",
            result=ScanResult.PASS,
            message="No injection patterns detected"
        )
    
    def _has_suspicious_encoding(self, content: str) -> bool:
        suspicious_chars = sum(1 for c in content if ord(c) > 0xFFFF)
        return suspicious_chars > len(content) * 0.1


class PIIScanner:
    """Detects personally identifiable information"""
    
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b',
        "ssn": r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b',
        "credit_card": r'\b(?:[0-9]{4}[-\s]?){3}[0-9]{4}\b',
        "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    }
    
    def scan(self, content: str) -> ScanEvent:
        findings = {}
        
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                findings[pii_type] = len(matches)
        
        if findings:
            total_pii = sum(findings.values())
            return ScanEvent(
                scanner="pii",
                result=ScanResult.WARN,
                risk_level=RiskLevel.MEDIUM if total_pii <= 2 else RiskLevel.HIGH,
                message=f"PII detected: {findings}",
                details=findings
            )
        
        return ScanEvent(
            scanner="pii",
            result=ScanResult.PASS,
            message="No PII detected"
        )


class ToxicityScanner:
    """Detects toxic or harmful content"""
    
    TOXIC_KEYWORDS = [
        "hate", "violence", "harmful", "dangerous", "illegal",
        "malicious", "attack", "exploit", "vulnerability", "hack"
    ]
    
    def scan(self, content: str) -> ScanEvent:
        content_lower = content.lower()
        found_keywords = [kw for kw in self.TOXIC_KEYWORDS if kw in content_lower]
        
        if found_keywords:
            return ScanEvent(
                scanner="toxicity",
                result=ScanResult.WARN,
                risk_level=RiskLevel.LOW if len(found_keywords) <= 2 else RiskLevel.MEDIUM,
                message=f"Potentially toxic content: {found_keywords}",
                details={"keywords": found_keywords}
            )
        
        return ScanEvent(
            scanner="toxicity",
            result=ScanResult.PASS,
            message="No toxic content detected"
        )


class SecretsScanner:
    """Detects secrets and credentials"""
    
    SECRET_PATTERNS = {
        "api_key": r'(?i)(api[_-]?key|apikey)[\s:=]+["\']?([a-zA-Z0-9_\-]{20,})',
        "password": r'(?i)(password|passwd|pwd)[\s:=]+["\']?([^\s"\']{8,})',
        "token": r'(?i)(token|bearer)[\s:=]+["\']?([a-zA-Z0-9_\-\.]{20,})',
        "private_key": r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
    }
    
    def scan(self, content: str) -> ScanEvent:
        findings = {}
        
        for secret_type, pattern in self.SECRET_PATTERNS.items():
            if re.search(pattern, content):
                findings[secret_type] = True
        
        if findings:
            return ScanEvent(
                scanner="secrets",
                result=ScanResult.BLOCK,
                risk_level=RiskLevel.CRITICAL,
                message=f"Secrets detected: {list(findings.keys())}",
                details=findings
            )
        
        return ScanEvent(
            scanner="secrets",
            result=ScanResult.PASS,
            message="No secrets detected"
        )


class ContentLengthScanner:
    """Validates content length"""
    
    def __init__(self, max_length: int = 100000):
        self.max_length = max_length
    
    def scan(self, content: str) -> ScanEvent:
        length = len(content)
        
        if length > self.max_length:
            return ScanEvent(
                scanner="content_length",
                result=ScanResult.BLOCK,
                risk_level=RiskLevel.MEDIUM,
                message=f"Content too long: {length} > {self.max_length}",
                details={"length": length, "max": self.max_length}
            )
        
        return ScanEvent(
            scanner="content_length",
            result=ScanResult.PASS,
            message=f"Content length OK: {length}"
        )


class PolicyEngine:
    """Enforces custom policy rules"""
    
    def __init__(self):
        self.rules: List[PolicyRule] = []
    
    def add_rule(self, rule: PolicyRule):
        self.rules.append(rule)
    
    def evaluate(self, content: str) -> ScanEvent:
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if re.search(rule.pattern, content, re.IGNORECASE):
                return ScanEvent(
                    scanner=f"policy_{rule.rule_id}",
                    result=ScanResult.BLOCK if rule.action == "block" else ScanResult.WARN,
                    risk_level=rule.risk_level,
                    message=f"Policy violation: {rule.name}",
                    details={"rule_id": rule.rule_id, "action": rule.action}
                )
        
        return ScanEvent(
            scanner="policy",
            result=ScanResult.PASS,
            message="No policy violations"
        )


class AuditTrail:
    """Immutable audit trail for all guardrails decisions"""
    
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
    
    def log(self, content_hash: str, scans: List[ScanEvent], decision: ScanResult):
        entry = {
            "id": str(uuid.uuid4())[:12],
            "content_hash": content_hash,
            "scans": [
                {
                    "scanner": s.scanner,
                    "result": s.result.value,
                    "risk_level": s.risk_level.value,
                    "message": s.message
                }
                for s in scans
            ],
            "decision": decision.value,
            "timestamp": time.time()
        }
        self.entries.append(entry)
        return entry["id"]
    
    def get_recent(self, count: int = 100) -> List[Dict[str, Any]]:
        return self.entries[-count:]


class GuardrailsSystem:
    """Main guardrails system orchestrating all scanners"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.scanners = [
            PromptInjectionScanner(),
            PIIScanner(),
            ToxicityScanner(),
            SecretsScanner(),
            ContentLengthScanner(max_length=config.get("max_content_length", 100000)),
        ]
        
        self.policy_engine = PolicyEngine()
        self.audit = AuditTrail()
        
        self.block_on_critical = config.get("block_on_critical", True)
        self.block_on_high = config.get("block_on_high", True)
        self.warn_on_medium = config.get("warn_on_medium", True)
    
    def scan_input(self, content: str) -> GuardrailsResult:
        start_time = time.time()
        all_scans: List[ScanEvent] = []
        
        for scanner in self.scanners:
            scan = scanner.scan(content)
            all_scans.append(scan)
        
        policy_scan = self.policy_engine.evaluate(content)
        all_scans.append(policy_scan)
        
        decision, risk_level = self._make_decision(all_scans)
        sanitized = self._sanitize(content, all_scans)
        
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        self.audit.log(content_hash, all_scans, decision)
        
        duration = (time.time() - start_time) * 1000
        
        return GuardrailsResult(
            allowed=decision == ScanResult.PASS,
            scans=all_scans,
            risk_level=risk_level,
            message=self._format_message(all_scans),
            sanitized_content=sanitized,
            duration_ms=duration
        )
    
    def scan_output(self, content: str) -> GuardrailsResult:
        return self.scan_input(content)
    
    def _make_decision(self, scans: List[ScanEvent]) -> Tuple[ScanResult, RiskLevel]:
        has_critical = any(s.risk_level == RiskLevel.CRITICAL for s in scans)
        has_high = any(s.risk_level == RiskLevel.HIGH for s in scans)
        has_medium = any(s.risk_level == RiskLevel.MEDIUM for s in scans)
        has_block = any(s.result == ScanResult.BLOCK for s in scans)
        has_warn = any(s.result == ScanResult.WARN for s in scans)
        
        if has_critical and self.block_on_critical:
            return ScanResult.BLOCK, RiskLevel.CRITICAL
        if has_high and self.block_on_high:
            return ScanResult.BLOCK, RiskLevel.HIGH
        if has_block:
            return ScanResult.BLOCK, RiskLevel.HIGH
        if has_medium and self.warn_on_medium:
            return ScanResult.WARN, RiskLevel.MEDIUM
        if has_warn:
            return ScanResult.WARN, RiskLevel.LOW
        
        return ScanResult.PASS, RiskLevel.LOW
    
    def _sanitize(self, content: str, scans: List[ScanEvent]) -> str:
        sanitized = content
        
        pii_scan = next((s for s in scans if s.scanner == "pii"), None)
        if pii_scan and pii_scan.result == ScanResult.WARN:
            for pii_type in ["email", "phone", "ssn", "credit_card"]:
                pattern = PIIScanner.PII_PATTERNS.get(pii_type, "")
                if pattern:
                    sanitized = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", sanitized)
        
        return sanitized
    
    def _format_message(self, scans: List[ScanEvent]) -> str:
        issues = [s for s in scans if s.result != ScanResult.PASS]
        if not issues:
            return "All scans passed"
        
        return "; ".join(f"{s.scanner}: {s.message}" for s in issues)
    
    def add_policy_rule(self, rule: PolicyRule):
        self.policy_engine.add_rule(rule)
    
    def get_audit_trail(self, count: int = 100) -> List[Dict[str, Any]]:
        return self.audit.get_recent(count)
    
    def get_stats(self) -> Dict[str, Any]:
        total = len(self.audit.entries)
        blocked = sum(1 for e in self.audit.entries if e["decision"] == "block")
        warned = sum(1 for e in self.audit.entries if e["decision"] == "warn")
        
        return {
            "total_scans": total,
            "blocked": blocked,
            "warned": warned,
            "pass_rate": round((total - blocked - warned) / total, 3) if total > 0 else 1.0
        }
