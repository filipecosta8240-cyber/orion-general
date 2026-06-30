from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("orion.performance_metrics")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
METRICS_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "PERFORMANCE_METRICS"


@dataclass
class MetricPoint:
    timestamp: str
    agent: str
    metric_name: str
    value: float
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class AgentStats:
    agent: str
    total_actions: int = 0
    successes: int = 0
    failures: int = 0
    avg_duration_ms: float = 0.0
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class PerformanceMetrics:
    """Tracks agent performance metrics."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or METRICS_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._metrics: List[MetricPoint] = []
        self._agent_stats: Dict[str, AgentStats] = {}
        self._load()

    def _load(self) -> None:
        index_file = self.root / "metrics.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                self._metrics = [MetricPoint(**m) for m in data[-5000:]]
            except (json.JSONDecodeError, TypeError):
                pass
        stats_file = self.root / "agent_stats.json"
        if stats_file.exists():
            try:
                data = json.loads(stats_file.read_text(encoding="utf-8"))
                self._agent_stats = {k: AgentStats(**v) for k, v in data.items()}
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        index_file = self.root / "metrics.json"
        data = [m.to_dict() for m in self._metrics[-5000:]]
        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        stats_file = self.root / "agent_stats.json"
        stats_data = {k: v.to_dict() for k, v in self._agent_stats.items()}
        stats_file.write_text(json.dumps(stats_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def record_action(self, agent: str, action: str, duration_ms: float,
                      success: bool = True, tags: Optional[Dict[str, str]] = None) -> None:
        metric = MetricPoint(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            agent=agent,
            metric_name=action,
            value=duration_ms,
            unit="ms",
            tags=tags or {},
        )
        self._metrics.append(metric)

        if agent not in self._agent_stats:
            self._agent_stats[agent] = AgentStats(agent=agent)
        stats = self._agent_stats[agent]
        stats.total_actions += 1
        stats.total_duration_ms += duration_ms
        stats.avg_duration_ms = stats.total_duration_ms / stats.total_actions
        if success:
            stats.successes += 1
        else:
            stats.failures += 1

        self._save()
        logger.debug("Métrica: %s %s %.1fms %s", agent, action, duration_ms, "OK" if success else "FALHA")

    def get_agent_stats(self, agent: Optional[str] = None) -> Dict[str, AgentStats]:
        if agent:
            return {agent: self._agent_stats.get(agent, AgentStats(agent=agent))}
        return self._agent_stats

    def get_action_stats(self, action: str) -> Dict[str, object]:
        action_metrics = [m for m in self._metrics if m.metric_name == action]
        if not action_metrics:
            return {"action": action, "count": 0}
        durations = [m.value for m in action_metrics]
        return {
            "action": action,
            "count": len(action_metrics),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
        }

    def get_slowest_actions(self, limit: int = 10) -> List[Dict[str, object]]:
        action_counts = defaultdict(list)
        for m in self._metrics:
            action_counts[m.metric_name].append(m.value)
        result = []
        for action, durations in action_counts.items():
            result.append({
                "action": action,
                "count": len(durations),
                "avg_ms": sum(durations) / len(durations),
            })
        return sorted(result, key=lambda x: x["avg_ms"], reverse=True)[:limit]

    def get_busiest_agents(self, limit: int = 10) -> List[Dict[str, object]]:
        return sorted(
            [v.to_dict() for v in self._agent_stats.values()],
            key=lambda x: x["total_actions"],
            reverse=True,
        )[:limit]

    def get_summary(self) -> Dict[str, object]:
        total = len(self._metrics)
        agents = len(self._agent_stats)
        durations = [m.value for m in self._metrics] if self._metrics else [0]
        return {
            "total_metrics": total,
            "total_agents": agents,
            "avg_duration_ms": sum(durations) / len(durations),
            "slowest_action": self._slowest_action(),
        }

    def _slowest_action(self) -> str:
        if not self._metrics:
            return "nenhuma"
        return max(self._metrics, key=lambda m: m.value).metric_name
