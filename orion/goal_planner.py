from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .memory import ObsidianMemoryBridge

logger = logging.getLogger("orion.goal_planner")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLANS_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "PLANS"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class Task:
    id: str
    title: str
    description: str
    status: str
    priority: str
    dependencies: List[str]
    assigned_to: str
    created_at: str
    due_at: str = ""
    completed_at: str = ""
    result: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Goal:
    id: str
    title: str
    description: str
    tasks: List[str]
    status: str
    created_at: str
    target_date: str = ""
    progress: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class GoalPlanner:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self._root = PLANS_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._goals: Dict[str, Goal] = {}
        self._tasks: Dict[str, Task] = {}
        self._load_plans()

    def _load_plans(self) -> None:
        goals_file = self._root / "goals.json"
        tasks_file = self._root / "tasks.json"
        if goals_file.exists():
            try:
                data = json.loads(goals_file.read_text(encoding="utf-8"))
                for gid, gdata in data.items():
                    self._goals[gid] = Goal(**gdata)
            except (json.JSONDecodeError, TypeError):
                pass
        if tasks_file.exists():
            try:
                data = json.loads(tasks_file.read_text(encoding="utf-8"))
                for tid, tdata in data.items():
                    self._tasks[tid] = Task(**tdata)
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_plans(self) -> None:
        goals_file = self._root / "goals.json"
        tasks_file = self._root / "tasks.json"
        goals_data = {gid: g.to_dict() for gid, g in self._goals.items()}
        tasks_data = {tid: t.to_dict() for tid, t in self._tasks.items()}
        goals_file.write_text(json.dumps(goals_data, indent=2, ensure_ascii=False), encoding="utf-8")
        tasks_file.write_text(json.dumps(tasks_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:20]}"

    def create_goal(self, title: str, description: str, target_date: str = "") -> Goal:
        gid = self._new_id("goal")
        goal = Goal(
            id=gid,
            title=title,
            description=description,
            tasks=[],
            status="active",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            target_date=target_date,
        )
        self._goals[gid] = goal
        self._save_plans()
        logger.info("Objetivo criado: %s", title)
        return goal

    def add_task(
        self,
        goal_id: str,
        title: str,
        description: str,
        assigned_to: str = "",
        priority: str = "normal",
        dependencies: Optional[List[str]] = None,
    ) -> Optional[Task]:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        tid = self._new_id("task")
        task = Task(
            id=tid,
            title=title,
            description=description,
            status=TaskStatus.PENDING.value,
            priority=priority,
            dependencies=dependencies or [],
            assigned_to=assigned_to,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self._tasks[tid] = task
        goal.tasks.append(tid)
        self._save_plans()
        logger.info("Tarefa adicionada: %s ao objetivo %s", title, goal.title)
        return task

    def decompose_goal(self, goal_id: str, subtasks: List[Dict[str, str]]) -> List[Task]:
        goal = self._goals.get(goal_id)
        if not goal:
            return []
        created = []
        prev_id = None
        for i, st in enumerate(subtasks):
            deps = [prev_id] if prev_id else []
            task = self.add_task(
                goal_id=goal_id,
                title=st.get("title", f"Subtarefa {i+1}"),
                description=st.get("description", ""),
                assigned_to=st.get("assigned_to", ""),
                priority=st.get("priority", "normal"),
                dependencies=deps,
            )
            if task:
                created.append(task)
                prev_id = task.id
        return created

    def complete_task(self, task_id: str, result: str = "") -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.COMPLETED.value
        task.result = result
        task.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self._update_goal_progress(task_id)
        self._save_plans()
        logger.info("Tarefa concluída: %s", task.title)
        return task

    def fail_task(self, task_id: str, reason: str = "") -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.FAILED.value
        task.result = reason
        self._save_plans()
        logger.info("Tarefa falhou: %s", task.title)
        return task

    def _update_goal_progress(self, completed_task_id: str) -> None:
        for goal in self._goals.values():
            if completed_task_id in goal.tasks:
                total = len(goal.tasks)
                completed = sum(1 for tid in goal.tasks if self._tasks.get(tid, Task(id="", title="", description="", status="", priority="", dependencies=[], assigned_to="", created_at="")).status == TaskStatus.COMPLETED.value)
                goal.progress = completed / max(total, 1)
                if goal.progress >= 1.0:
                    goal.status = "completed"
                self._save_plans()

    def get_ready_tasks(self) -> List[Task]:
        ready = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING.value:
                continue
            deps_met = all(
                self._tasks.get(dep, Task(id="", title="", description="", status="", priority="", dependencies=[], assigned_to="", created_at="")).status == TaskStatus.COMPLETED.value
                for dep in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return sorted(ready, key=lambda t: {"critical": 0, "high": 1, "normal": 2, "low": 3}.get(t.priority, 2))

    def get_goal_status(self, goal_id: str) -> Optional[Dict[str, object]]:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        tasks_detail = []
        for tid in goal.tasks:
            task = self._tasks.get(tid)
            if task:
                tasks_detail.append({
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                    "assigned_to": task.assigned_to,
                })
        return {
            "goal": goal.title,
            "status": goal.status,
            "progress": goal.progress,
            "tasks": tasks_detail,
        }

    def list_goals(self, status: Optional[str] = None) -> List[Goal]:
        if status:
            return [g for g in self._goals.values() if g.status == status]
        return list(self._goals.values())

    def create_research_plan(self, topic: str) -> Goal:
        goal = self.create_goal(
            title=f"Pesquisa: {topic}",
            description=f"Plano completo de pesquisa sobre {topic}",
        )
        subtasks = [
            {"title": f"Levantamento bibliográfico: {topic}", "description": "Identificar fontes principais", "assigned_to": "elias", "priority": "high"},
            {"title": f"Análise de dados: {topic}", "description": "Processar e analisar informações coletadas", "assigned_to": "pesquisador", "priority": "high"},
            {"title": f"Síntese: {topic}", "description": "Compilar achados em relatório estruturado", "assigned_to": "documentalista", "priority": "normal"},
            {"title": f"Validação: {topic}", "description": "Verificar consistência e precisão", "assigned_to": "pesquisador", "priority": "normal"},
            {"title": f"Estratégia: {topic}", "description": "Definir próximos passos e ações", "assigned_to": "estratega", "priority": "normal"},
        ]
        self.decompose_goal(goal.id, subtasks)
        return goal
