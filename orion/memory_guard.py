from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("orion.memory_guard")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
GUARD_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "MEMORY_GUARD"


@dataclass
class ThreatEvent:
    id: str
    timestamp: str
    threat_type: str
    source: str
    content: str
    action_taken: str
    severity: str = "medium"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class MemoryGuard:
    """Protects memory against injection attacks and poisoning."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?prior\s+instructions",
        r"disregard\s+(all\s+)?previous",
        r"you\s+are\s+now\s+(?:a|an)\s+",
        r"act\s+as\s+if\s+you\s+(?:are|were)",
        r"pretend\s+(?:you\s+are|to\s+be)",
        r"new\s+instructions?:",
        r"system\s*:\s*",
        r"override\s+(?:all\s+)?(?:previous|prior|existing)",
        r"forget\s+(?:all\s+)?(?:previous|prior|everything)",
        r"from\s+now\s+on\s+you\s+(?:will|must|should|are)",
        r"IMPORTANT:\s*new\s+rules",
        r"ADMIN\s*(?:MODE|ACCESS|Override)",
        r"\[SYSTEM\]",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"###\s*(?:System|Instruction|New)\s*(?:Message|Prompt|Rule)",
    ]

    SUSPICIOUS_CONTENT = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r"subprocess\.",
        r"os\.system\(",
    ]

    def __init__(self, root: Optional[Path] = None):
        self.root = root or GUARD_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._threats: List[ThreatEvent] = []
        self._load()

    def _load(self) -> None:
        index_file = self.root / "threats.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                self._threats = [ThreatEvent(**t) for t in data]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        index_file = self.root / "threats.json"
        data = [t.to_dict() for t in self._threats]
        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"th_{ts[:20]}"

    def scan_text(self, text: str, source: str = "unknown") -> Dict[str, object]:
        threats_found = []
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats_found.append(("injection", pattern))
        for pattern in self.SUSPICIOUS_CONTENT:
            if re.search(pattern, text, re.IGNORECASE):
                threats_found.append(("suspicious_code", pattern))

        if threats_found:
            for threat_type, pattern in threats_found:
                event = ThreatEvent(
                    id=self._new_id(),
                    timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    threat_type=threat_type,
                    source=source,
                    content=text[:200],
                    action_taken="blocked",
                    severity="high" if threat_type == "injection" else "medium",
                )
                self._threats.append(event)
                logger.warning("Ameaça detetada: %s de %s", threat_type, source)
            self._save()
            return {
                "safe": False,
                "threats": [{"type": t, "pattern": p} for t, p in threats_found],
                "action": "blocked",
            }
        return {"safe": True, "threats": [], "action": "allowed"}

    def sanitize_input(self, text: str) -> str:
        sanitized = text
        for pattern in self.INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[BLOCKED]", sanitized, flags=re.IGNORECASE)
        for pattern in self.SUSPICIOUS_CONTENT:
            sanitized = re.sub(pattern, "[SANITIZED]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def get_threats(self, limit: int = 50) -> List[ThreatEvent]:
        return self._threats[-limit:]

    def get_stats(self) -> Dict[str, object]:
        total = len(self._threats)
        by_type = {}
        for t in self._threats:
            by_type[t.threat_type] = by_type.get(t.threat_type, 0) + 1
        return {
            "total_threats": total,
            "by_type": by_type,
            "recent_threats": self._threats[-5:] if self._threats else [],
        }
