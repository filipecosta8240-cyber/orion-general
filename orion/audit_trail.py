from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("orion.audit_trail")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "AUDIT_TRAIL"


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    agent: str
    action: str
    target: str
    result: str
    success: bool
    duration_ms: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class AuditTrail:
    """Tracks all agent actions for debugging and accountability."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or AUDIT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []
        self._load()

    def _load(self) -> None:
        index_file = self.root / "audit.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                self._entries = [AuditEntry(**e) for e in data[-1000:]]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        index_file = self.root / "audit.json"
        data = [e.to_dict() for e in self._entries[-1000:]]
        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"aud_{ts[:20]}"

    def log(self, agent: str, action: str, target: str, result: str,
            success: bool = True, duration_ms: float = 0.0,
            metadata: Optional[Dict[str, str]] = None) -> AuditEntry:
        entry = AuditEntry(
            id=self._new_id(),
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            agent=agent,
            action=action,
            target=target,
            result=result,
            success=success,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        self._save()
        logger.debug("Audit: %s %s por %s", action, target, agent)
        return entry

    def query(self, agent: Optional[str] = None, action: Optional[str] = None,
              success_only: Optional[bool] = None, limit: int = 50) -> List[AuditEntry]:
        results = self._entries
        if agent:
            results = [e for e in results if e.agent == agent]
        if action:
            results = [e for e in results if e.action == action]
        if success_only is not None:
            results = [e for e in results if e.success == success_only]
        return results[-limit:]

    def get_stats(self) -> Dict[str, object]:
        total = len(self._entries)
        successes = sum(1 for e in self._entries if e.success)
        failures = total - successes
        agents = {}
        for e in self._entries:
            agents[e.agent] = agents.get(e.agent, 0) + 1
        actions = {}
        for e in self._entries:
            actions[e.action] = actions.get(e.action, 0) + 1
        return {
            "total_entries": total,
            "successes": successes,
            "failures": failures,
            "agents": agents,
            "actions": actions,
        }

    def get_recent(self, limit: int = 20) -> List[AuditEntry]:
        return self._entries[-limit:]
