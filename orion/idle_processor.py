from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("orion.idle_processor")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
IDLE_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "IDLE_PROCESSOR"


@dataclass
class IdleTask:
    id: str
    name: str
    description: str
    priority: int
    action: str
    last_run: Optional[str] = None
    run_count: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class IdleResult:
    task_id: str
    task_name: str
    timestamp: str
    result: str
    success: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class IdleProcessor:
    """Self-improvement processor that runs when user is idle."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or IDLE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._tasks: List[IdleTask] = []
        self._results: List[IdleResult] = []
        self._last_activity: Optional[datetime] = None
        self._idle_threshold_minutes: int = 30
        self._action_handlers: Dict[str, Callable] = {}
        self._load()
        self._register_default_tasks()

    def _load(self) -> None:
        tasks_file = self.root / "tasks.json"
        if tasks_file.exists():
            try:
                data = json.loads(tasks_file.read_text(encoding="utf-8"))
                self._tasks = [IdleTask(**t) for t in data]
            except (json.JSONDecodeError, TypeError):
                pass
        results_file = self.root / "results.json"
        if results_file.exists():
            try:
                data = json.loads(results_file.read_text(encoding="utf-8"))
                self._results = [IdleResult(**r) for r in data]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        tasks_file = self.root / "tasks.json"
        data = [t.to_dict() for t in self._tasks]
        tasks_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        results_file = self.root / "results.json"
        rdata = [r.to_dict() for r in self._results[-100:]]
        results_file.write_text(json.dumps(rdata, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"idle_{ts[:20]}"

    def _register_default_tasks(self) -> None:
        defaults = [
            IdleTask(
                id="memory_review",
                name="Revisão de Memória",
                description="Verificar e consolidar memórias antigas",
                priority=1,
                action="consolidate_memory",
            ),
            IdleTask(
                id="skill_check",
                name="Verificação de Skills",
                description="Verificar se há skills para cristalizar",
                priority=2,
                action="crystallize_skills",
            ),
            IdleTask(
                id="knowledge_sync",
                name="Sincronização de Conhecimento",
                description="Atualizar o grafo de conhecimento",
                priority=3,
                action="sync_knowledge_graph",
            ),
            IdleTask(
                id="health_check",
                name="Verificação de Saúde",
                description="Verificar estado do sistema",
                priority=4,
                action="system_health_check",
            ),
        ]
        for task in defaults:
            if not any(t.id == task.id for t in self._tasks):
                self._tasks.append(task)
        self._save()

    def register_action(self, action_name: str, handler: Callable) -> None:
        self._action_handlers[action_name] = handler

    def update_activity(self) -> None:
        self._last_activity = datetime.now(timezone.utc)

    def is_idle(self) -> bool:
        if self._last_activity is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_activity).total_seconds() / 60
        return elapsed >= self._idle_threshold_minutes

    def get_pending_tasks(self) -> List[IdleTask]:
        return [t for t in self._tasks if t.enabled]

    def run_next_task(self) -> Optional[IdleResult]:
        if not self.is_idle():
            return None
        tasks = sorted(self.get_pending_tasks(), key=lambda t: t.priority)
        if not tasks:
            return None
        task = tasks[0]
        handler = self._action_handlers.get(task.action)
        if handler:
            try:
                result_text = handler()
                success = True
            except Exception as e:
                result_text = f"Erro: {e}"
                success = False
        else:
            result_text = f"Tarefa '{task.name}' registada (handler não configurado)"
            success = True
        task.last_run = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        task.run_count += 1
        result = IdleResult(
            task_id=task.id,
            task_name=task.name,
            timestamp=task.last_run,
            result=result_text,
            success=success,
        )
        self._results.append(result)
        self._save()
        logger.info("Tarefa de inatividade executada: %s", task.name)
        return result

    def get_stats(self) -> Dict[str, object]:
        total_tasks = len(self._tasks)
        enabled = sum(1 for t in self._tasks if t.enabled)
        total_results = len(self._results)
        successes = sum(1 for r in self._results if r.success)
        return {
            "total_tasks": total_tasks,
            "enabled_tasks": enabled,
            "total_runs": total_results,
            "successes": successes,
            "success_rate": successes / total_results if total_results > 0 else 0,
            "is_idle": self.is_idle(),
            "idle_threshold_minutes": self._idle_threshold_minutes,
        }
