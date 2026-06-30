from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("orion.prospective_memory")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROSPECTIVE_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "PROSPECTIVE_MEMORY"


@dataclass
class Intention:
    id: str
    created_at: str
    description: str
    intended_action: str
    trigger: str
    deadline: Optional[str] = None
    priority: int = 5
    status: str = "pending"
    completed_at: Optional[str] = None
    context: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class ProspectiveMemory:
    """Tracks future intentions and scheduled goals."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or PROSPECTIVE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._intentions: List[Intention] = []
        self._load()

    def _load(self) -> None:
        index_file = self.root / "intentions.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                self._intentions = [Intention(**item) for item in data]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        index_file = self.root / "intentions.json"
        data = [item.to_dict() for item in self._intentions]
        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"int_{ts[:20]}"

    def add_intention(self, description: str, intended_action: str, trigger: str,
                      deadline: Optional[str] = None, priority: int = 5,
                      context: Optional[Dict[str, str]] = None,
                      tags: Optional[List[str]] = None) -> Intention:
        intention = Intention(
            id=self._new_id(),
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            description=description,
            intended_action=intended_action,
            trigger=trigger,
            deadline=deadline,
            priority=priority,
            context=context or {},
            tags=tags or [],
        )
        self._intentions.append(intention)
        self._save()
        logger.info("Intenção registada: %s", description)
        return intention

    def complete(self, intention_id: str) -> bool:
        for item in self._intentions:
            if item.id == intention_id:
                item.status = "completed"
                item.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                self._save()
                logger.info("Intenção concluída: %s", item.description)
                return True
        return False

    def cancel(self, intention_id: str) -> bool:
        for item in self._intentions:
            if item.id == intention_id:
                item.status = "cancelled"
                self._save()
                return True
        return False

    def get_pending(self) -> List[Intention]:
        return [i for i in self._intentions if i.status == "pending"]

    def get_by_trigger(self, trigger: str) -> List[Intention]:
        return [i for i in self._intentions if i.trigger == trigger and i.status == "pending"]

    def get_overdue(self) -> List[Intention]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        return [i for i in self._intentions if i.deadline and i.deadline < now and i.status == "pending"]

    def get_stats(self) -> Dict[str, object]:
        total = len(self._intentions)
        pending = sum(1 for i in self._intentions if i.status == "pending")
        completed = sum(1 for i in self._intentions if i.status == "completed")
        cancelled = sum(1 for i in self._intentions if i.status == "cancelled")
        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "cancelled": cancelled,
            "completion_rate": completed / total if total > 0 else 0,
        }
