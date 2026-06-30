from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("orion.episodic_memory")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
EPISODIC_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "EPISODIC_MEMORY"


@dataclass
class Episode:
    id: str
    timestamp: str
    event_type: str
    agent: str
    action: str
    result: str
    outcome: str
    context: Dict[str, str] = field(default_factory=dict)
    duration_seconds: float = 0.0
    success: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class EpisodicMemory:
    """Stores past events with outcomes for learning from experience."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or EPISODIC_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._episodes: List[Episode] = []
        self._load()

    def _load(self) -> None:
        index_file = self.root / "episodes.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                self._episodes = [Episode(**ep) for ep in data]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        index_file = self.root / "episodes.json"
        data = [ep.to_dict() for ep in self._episodes]
        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"ep_{ts[:20]}"

    def record(self, event_type: str, agent: str, action: str, result: str,
               outcome: str = "success", context: Optional[Dict[str, str]] = None,
               duration_seconds: float = 0.0, tags: Optional[List[str]] = None) -> Episode:
        episode = Episode(
            id=self._new_id(),
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            event_type=event_type,
            agent=agent,
            action=action,
            result=result,
            outcome=outcome,
            context=context or {},
            duration_seconds=duration_seconds,
            success=outcome == "success",
            tags=tags or [],
        )
        self._episodes.append(episode)
        self._save()
        logger.info("Episódio registado: %s por %s", action, agent)
        return episode

    def query(self, event_type: Optional[str] = None, agent: Optional[str] = None,
              success_only: bool = False, limit: int = 20) -> List[Episode]:
        results = self._episodes
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if agent:
            results = [e for e in results if e.agent == agent]
        if success_only:
            results = [e for e in results if e.success]
        return results[-limit:]

    def get_stats(self) -> Dict[str, object]:
        total = len(self._episodes)
        successes = sum(1 for e in self._episodes if e.success)
        failures = total - successes
        agents = {}
        for e in self._episodes:
            agents[e.agent] = agents.get(e.agent, 0) + 1
        return {
            "total_episodes": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0,
            "agents": agents,
        }

    def get_recent_failures(self, limit: int = 10) -> List[Episode]:
        failures = [e for e in self._episodes if not e.success]
        return failures[-limit:]

    def get_patterns(self) -> Dict[str, int]:
        patterns = {}
        for e in self._episodes:
            key = f"{e.event_type}:{e.action}"
            patterns[key] = patterns.get(key, 0) + 1
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:20])
