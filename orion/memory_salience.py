from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

from .memory import MemoryEntry, ObsidianMemoryBridge

logger = logging.getLogger("orion.memory_salience")


class MemorySalienceEngine:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self._access_counts: Dict[str, int] = defaultdict(int)
        self._reference_counts: Dict[str, int] = defaultdict(int)

    def _age_factor(self, entry: MemoryEntry) -> float:
        try:
            created = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created).days
            return math.exp(-age_days / 30.0)
        except (ValueError, TypeError):
            return 0.5

    def _source_factor(self, entry: MemoryEntry) -> float:
        source_weights = {
            "self_evolution": 0.9,
            "reflection_engine": 0.85,
            "skill_crystallizer": 0.8,
            "consolidation_engine": 0.7,
            "research": 0.75,
            "agent": 0.7,
            "orion": 0.6,
        }
        return source_weights.get(entry.source, 0.5)

    def _domain_factor(self, entry: MemoryEntry) -> float:
        domain = entry.tags.get("domain", "geral")
        priority = entry.tags.get("priority", "normal")
        domain_base = {
            "self_evolution": 0.8,
            "reflection": 0.85,
            "skill_crystallization": 0.75,
            "research": 0.7,
            "system": 0.6,
        }.get(domain, 0.5)
        priority_bonus = {
            "critico": 0.3,
            "alto": 0.2,
            "normal": 0.0,
            "baixo": -0.1,
        }.get(priority, 0.0)
        return min(1.0, domain_base + priority_bonus)

    def _content_factor(self, entry: MemoryEntry) -> float:
        content_len = len(entry.content)
        if content_len < 50:
            return 0.3
        elif content_len < 200:
            return 0.5
        elif content_len < 500:
            return 0.7
        elif content_len < 1000:
            return 0.85
        else:
            return 1.0

    def _freshness_factor(self, entry: MemoryEntry) -> float:
        freshness = entry.tags.get("freshness", "")
        if freshness == "today":
            return 1.0
        elif freshness == "consolidated":
            return 0.6
        return 0.5

    def calculate_salience(self, entry: MemoryEntry) -> float:
        age = self._age_factor(entry)
        source = self._source_factor(entry)
        domain = self._domain_factor(entry)
        content = self._content_factor(entry)
        freshness = self._freshness_factor(entry)
        salience = (age * 0.25 + source * 0.2 + domain * 0.25 + content * 0.15 + freshness * 0.15)
        access_bonus = min(0.2, self._access_counts.get(entry.id, 0) * 0.02)
        reference_bonus = min(0.15, self._reference_counts.get(entry.id, 0) * 0.03)
        return min(1.0, salience + access_bonus + reference_bonus)

    def score_all_entries(self) -> List[Tuple[MemoryEntry, float]]:
        entries = self.memory.list_entries()
        scored = [(e, self.calculate_salience(e)) for e in entries]
        return sorted(scored, key=lambda x: -x[1])

    def get_top_entries(self, limit: int = 10) -> List[Tuple[MemoryEntry, float]]:
        return self.score_all_entries()[:limit]

    def get_low_salience_entries(self, threshold: float = 0.3) -> List[Tuple[MemoryEntry, float]]:
        return [(e, s) for e, s in self.score_all_entries() if s < threshold]

    def record_access(self, entry_id: str) -> None:
        self._access_counts[entry_id] += 1

    def record_reference(self, entry_id: str) -> None:
        self._reference_counts[entry_id] += 1

    def get_stats(self) -> Dict[str, object]:
        scored = self.score_all_entries()
        if not scored:
            return {"total": 0, "avg_salience": 0, "high_salience": 0, "low_salience": 0}
        scores = [s for _, s in scored]
        return {
            "total": len(scored),
            "avg_salience": sum(scores) / len(scores),
            "high_salience": sum(1 for s in scores if s >= 0.7),
            "medium_salience": sum(1 for s in scores if 0.3 <= s < 0.7),
            "low_salience": sum(1 for s in scores if s < 0.3),
            "top_5": [(e.title[:50], round(s, 2)) for e, s in scored[:5]],
        }
