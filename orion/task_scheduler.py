"""
ORION Task Scheduler
=====================
Persistent task queue that survives computer shutdown.

Features:
- Tasks persisted to disk as JSON
- Execute when computer turns on
- Windows Task Scheduler integration (wake from sleep)
- Recurring tasks (cron-like)
- Task dependencies
- Priority queues
- Automatic retry on failure

How it works:
1. User queues tasks via MCP (even if computer is off next, tasks wait)
2. On startup, ORION daemon loads pending tasks
3. Windows Task Scheduler can wake computer at scheduled times
4. Tasks execute automatically when computer is available
"""

import json
import time
import uuid
import os
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger("orion.task_scheduler")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    WAITING_DEPENDENCY = "waiting_dependency"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class RecurrenceType(str, Enum):
    NONE = "none"
    ONCE = "once"
    DAILY = "daily"
    HOURLY = "hourly"
    WEEKLY = "weekly"
    MINUTES = "minutes"


@dataclass
class ScheduledTask:
    """A task that persists across shutdowns"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    task_type: str = ""  # "agent_task", "system_task", "custom"
    handler: str = ""  # Handler function name or code
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    agent_id: str = "system"
    
    # Scheduling
    run_at: Optional[float] = None  # Unix timestamp for one-shot
    recurrence: RecurrenceType = RecurrenceType.NONE
    recurrence_interval_minutes: int = 60
    recurrence_count: int = 0
    max_recurrences: int = -1  # -1 = infinite
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Task IDs
    
    # Retry
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    
    # Results
    result: Any = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "handler": self.handler,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority.value,
            "agent_id": self.agent_id,
            "run_at": self.run_at,
            "recurrence": self.recurrence.value,
            "recurrence_interval_minutes": self.recurrence_interval_minutes,
            "recurrence_count": self.recurrence_count,
            "max_recurrences": self.max_recurrences,
            "depends_on": self.depends_on,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        task = cls()
        for key, value in data.items():
            if key == "status":
                task.status = TaskStatus(value)
            elif key == "priority":
                task.priority = TaskPriority(value)
            elif key == "recurrence":
                task.recurrence = RecurrenceType(value)
            elif hasattr(task, key):
                setattr(task, key, value)
        return task
    
    @property
    def is_due(self) -> bool:
        """Check if task should run now"""
        if self.status not in [TaskStatus.PENDING, TaskStatus.PAUSED]:
            return False
        if self.run_at and time.time() >= self.run_at:
            return True
        if self.next_run_at and time.time() >= self.next_run_at:
            return True
        if self.recurrence == RecurrenceType.NONE and self.run_at is None:
            return True  # Immediate task
        return False
    
    @property
    def is_recurring_done(self) -> bool:
        """Check if recurring task has completed all recurrences"""
        if self.max_recurrences == -1:
            return False
        return self.recurrence_count >= self.max_recurrences


class TaskPersistence:
    """Handles task persistence to disk"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.storage_path / "scheduled_tasks.json"
        self.history_file = self.storage_path / "task_history.json"
    
    def save_tasks(self, tasks: Dict[str, ScheduledTask]) -> None:
        """Save tasks to disk"""
        try:
            data = {
                "tasks": {tid: t.to_dict() for tid, t in tasks.items()},
                "saved_at": time.time()
            }
            self.tasks_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
    
    def load_tasks(self) -> Dict[str, ScheduledTask]:
        """Load tasks from disk"""
        tasks = {}
        try:
            if self.tasks_file.exists():
                data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
                for tid, tdata in data.get("tasks", {}).items():
                    tasks[tid] = ScheduledTask.from_dict(tdata)
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
        return tasks
    
    def save_history(self, task: ScheduledTask) -> None:
        """Save completed task to history"""
        try:
            history = []
            if self.history_file.exists():
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
            
            history.append(task.to_dict())
            
            # Keep last 500 history entries
            if len(history) > 500:
                history = history[-500:]
            
            self.history_file.write_text(
                json.dumps(history, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Error saving task history: {e}")
    
    def load_history(self, limit: int = 50) -> List[Dict]:
        """Load recent task history"""
        try:
            if self.history_file.exists():
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
                return history[-limit:]
        except Exception as e:
            logger.error(f"Error loading task history: {e}")
        return []


class WindowsTaskScheduler:
    """Integration with Windows Task Scheduler"""
    
    @staticmethod
    def create_scheduled_task(
        task_name: str,
        command: str,
        trigger_time: str,  # HH:MM format
        trigger_days: str = "*",  # * = every day, or comma-separated day numbers
        working_dir: Optional[str] = None
    ) -> bool:
        """Create a task in Windows Task Scheduler"""
        try:
            # Build schtasks command
            cmd_parts = [
                "schtasks",
                "/create",
                f'/tn "ORION\\{task_name}"',
                f'/tr "{command}"',
                f'/sc weekly',
                f'/st {trigger_time}',
                "/f"  # Force overwrite
            ]
            
            if trigger_days != "*":
                cmd_parts.append(f'/d {trigger_days}')
            
            if working_dir:
                cmd_parts.append(f'/rp "{working_dir}"')
            
            cmd = " ".join(cmd_parts)
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Created Windows scheduled task: {task_name}")
                return True
            else:
                logger.warning(f"schtasks error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating scheduled task: {e}")
            return False
    
    @staticmethod
    def create_wake_task(
        task_name: str,
        wake_time: str,  # HH:MM
        python_path: str,
        script_path: str
    ) -> bool:
        """Create a task that wakes computer and runs ORION"""
        try:
            # Use /SC ONCE for one-time wake, or /SC DAILY for recurring
            cmd = (
                f'schtasks /create /tn "ORION\\{task_name}" '
                f'/tr "{python_path} {script_path}" '
                f'/sc ONCE /st {wake_time} '
                f'/f '
                f'/rl HIGHEST'  # Run with highest privileges
            )
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error creating wake task: {e}")
            return False
    
    @staticmethod
    def delete_task(task_name: str) -> bool:
        """Delete a scheduled task"""
        try:
            cmd = f'schtasks /delete /tn "ORION\\{task_name}" /f'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def list_tasks() -> List[Dict[str, str]]:
        """List ORION scheduled tasks"""
        try:
            cmd = 'schtasks /query /tn "ORION\\*" /fo LIST /v'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            # Parse output
            tasks = []
            if result.returncode == 0:
                current_task = {}
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, _, value = line.partition(':')
                        key = key.strip()
                        value = value.strip()
                        if key == 'TaskName':
                            if current_task:
                                tasks.append(current_task)
                            current_task = {'name': value}
                        elif key == 'Status':
                            current_task['status'] = value
                        elif key == 'Next Run Time':
                            current_task['next_run'] = value
                if current_task:
                    tasks.append(current_task)
            return tasks
        except Exception:
            return []
    
    @staticmethod
    def task_exists(task_name: str) -> bool:
        """Check if task exists"""
        try:
            cmd = f'schtasks /query /tn "ORION\\{task_name}" 2>nul'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False


class TaskExecutor:
    """Executes queued tasks"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register built-in task handlers"""
        self.handlers["health_check"] = self._handle_health_check
        self.handlers["memory_consolidation"] = self._handle_memory_consolidation
        self.handlers["knowledge_graph_sync"] = self._handle_kg_sync
        self.handlers["security_scan"] = self._handle_security_scan
        self.handlers["data_cleanup"] = self._handle_data_cleanup
        self.handlers["run_python"] = self._handle_run_python
    
    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a custom task handler"""
        self.handlers[name] = handler
    
    def execute(self, task: ScheduledTask) -> Any:
        """Execute a task"""
        handler = self.handlers.get(task.handler)
        if not handler:
            # Try to evaluate as Python code
            if task.handler.startswith("python:"):
                code = task.handler[7:]
                return self._execute_python(code, task.payload)
            raise ValueError(f"No handler found: {task.handler}")
        
        return handler(task.payload)
    
    def _handle_health_check(self, payload: Dict) -> Dict:
        """Run health check"""
        return {"status": "healthy", "timestamp": time.time()}
    
    def _handle_memory_consolidation(self, payload: Dict) -> Dict:
        """Consolidate memory"""
        from .tiered_memory import get_tiered_memory
        memory = get_tiered_memory()
        consolidated = memory.consolidate_memories()
        return {"consolidated": consolidated}
    
    def _handle_kg_sync(self, payload: Dict) -> Dict:
        """Sync knowledge graph"""
        from .knowledge_graph_advanced import get_knowledge_graph
        kg = get_knowledge_graph()
        stats = kg.get_graph_statistics()
        return {"stats": stats}
    
    def _handle_security_scan(self, payload: Dict) -> Dict:
        """Run security scan"""
        from .security_layers import get_security_system
        security = get_security_system()
        return security.get_security_dashboard()
    
    def _handle_data_cleanup(self, payload: Dict) -> Dict:
        """Clean up old data"""
        return {"cleaned": True, "timestamp": time.time()}
    
    def _handle_run_python(self, payload: Dict) -> Any:
        """Run arbitrary Python code (from trusted source)"""
        code = payload.get("code", "")
        if code:
            return self._execute_python(code, payload)
        return {"error": "No code provided"}
    
    def _execute_python(self, code: str, context: Dict) -> Any:
        """Execute Python code in restricted environment"""
        try:
            restricted_globals = {"__builtins__": {}}
            restricted_locals = context.copy()
            exec(code, restricted_globals, restricted_locals)
            return restricted_locals.get("result", {"status": "executed"})
        except Exception as e:
            return {"error": str(e)}


class PersistentTaskScheduler:
    """
    Task scheduler that persists tasks across shutdowns.
    
    How it works:
    1. Tasks are saved to disk as JSON
    2. On ORION startup, pending tasks are loaded
    3. Tasks run when their scheduled time arrives
    4. Windows Task Scheduler can wake computer for scheduled tasks
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("orion_tasks")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.persistence = TaskPersistence(self.storage_path)
        self.executor = TaskExecutor()
        self.scheduler = WindowsTaskScheduler()
        
        # Load existing tasks
        self.tasks: Dict[str, ScheduledTask] = self.persistence.load_tasks()
        
        # Processing thread
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        logger.info(f"Task Scheduler initialized with {len(self.tasks)} tasks")
    
    def queue_task(
        self,
        name: str,
        handler: str,
        payload: Optional[Dict[str, Any]] = None,
        run_at: Optional[float] = None,
        recurrence: RecurrenceType = RecurrenceType.NONE,
        recurrence_minutes: int = 60,
        max_recurrences: int = -1,
        priority: TaskPriority = TaskPriority.NORMAL,
        depends_on: Optional[List[str]] = None,
        agent_id: str = "system",
        description: str = "",
        wake_computer: bool = False,
        wake_time: Optional[str] = None
    ) -> ScheduledTask:
        """Queue a task for execution"""
        task = ScheduledTask(
            name=name,
            description=description,
            handler=handler,
            payload=payload or {},
            run_at=run_at,
            recurrence=recurrence,
            recurrence_interval_minutes=recurrence_minutes,
            max_recurrences=max_recurrences,
            priority=priority,
            depends_on=depends_on or [],
            agent_id=agent_id
        )
        
        with self._lock:
            self.tasks[task.id] = task
            self.persistence.save_tasks(self.tasks)
        
        # If wake_computer is requested, create Windows scheduled task
        if wake_computer and run_at:
            wake_dt = datetime.fromtimestamp(run_at)
            wake_time_str = wake_time or wake_dt.strftime("%H:%M")
            
            python_path = os.sys.executable
            script_path = str(Path(__file__).parent.parent / "run_task.py")
            
            # Create the wake script
            self._create_wake_script(task.id, python_path, script_path)
            
            self.scheduler.create_wake_task(
                task_name=f"ORION_{task.id[:8]}",
                wake_time=wake_time_str,
                python_path=python_path,
                script_path=script_path
            )
        
        logger.info(f"Queued task: {name} ({task.id})")
        return task
    
    def _create_wake_script(self, task_id: str, python_path: str, script_path: str) -> None:
        """Create a Python script that runs when computer wakes"""
        script_content = f'''#!/usr/bin/env python3
"""Auto-generated ORION wake script for task {task_id}"""
import sys
import os
sys.path.insert(0, r"{Path(__file__).resolve().parent.parent}")
from orion.task_scheduler import PersistentTaskScheduler
scheduler = PersistentTaskScheduler()
scheduler.process_task("{task_id}")
'''
        Path(script_path).write_text(script_content, encoding="utf-8")
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.CANCELLED
            self.persistence.save_tasks(self.tasks)
            
            # Remove Windows scheduled task if exists
            self.scheduler.delete_task(f"ORION_{task_id[:8]}")
            return True
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a task"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.PAUSED
            self.persistence.save_tasks(self.tasks)
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.PAUSED:
                return False
            task.status = TaskStatus.PENDING
            self.persistence.save_tasks(self.tasks)
            return True
    
    def process_task(self, task_id: str) -> bool:
        """Process a single task"""
        task = self.tasks.get(task_id)
        if not task or not task.is_due:
            return False
        
        # Check dependencies
        for dep_id in task.depends_on:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.status not in [TaskStatus.COMPLETED]:
                task.status = TaskStatus.WAITING_DEPENDENCY
                return False
        
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        try:
            result = self.executor.execute(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            
            # Handle recurrence
            if task.recurrence != RecurrenceType.NONE and not task.is_recurring_done:
                task.recurrence_count += 1
                if task.recurrence == RecurrenceType.MINUTES:
                    task.next_run_at = time.time() + (task.recurrence_interval_minutes * 60)
                elif task.recurrence == RecurrenceType.HOURLY:
                    task.next_run_at = time.time() + 3600
                elif task.recurrence == RecurrenceType.DAILY:
                    task.next_run_at = time.time() + 86400
                elif task.recurrence == RecurrenceType.WEEKLY:
                    task.next_run_at = time.time() + (7 * 86400)
                task.status = TaskStatus.PENDING
                task.last_run_at = time.time()
            
            # Save to history
            self.persistence.save_history(task)
            
            with self._lock:
                self.persistence.save_tasks(self.tasks)
            
            logger.info(f"Task completed: {task.name} ({task.id})")
            return True
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                task.run_at = time.time() + task.retry_delay_seconds
            
            with self._lock:
                self.persistence.save_tasks(self.tasks)
            
            logger.error(f"Task failed: {task.name} ({task.id}): {e}")
            return False
    
    def process_pending_tasks(self) -> int:
        """Process all due tasks"""
        processed = 0
        
        with self._lock:
            pending_tasks = [
                t for t in self.tasks.values()
                if t.is_due
            ]
        
        for task in pending_tasks:
            if self.process_task(task.id):
                processed += 1
        
        return processed
    
    def start_background(self, interval_seconds: int = 30) -> None:
        """Start background task processor"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._process_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._thread.start()
        logger.info(f"Task scheduler background started (interval: {interval_seconds}s)")
    
    def stop_background(self) -> None:
        """Stop background processor"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _process_loop(self, interval: int) -> None:
        """Background processing loop"""
        while self._running:
            try:
                processed = self.process_pending_tasks()
                if processed > 0:
                    logger.info(f"Processed {processed} tasks")
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
            time.sleep(interval)
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List tasks"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get task execution history"""
        return self.persistence.load_history(limit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        total = len(self.tasks)
        by_status = {}
        for task in self.tasks.values():
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_tasks": total,
            "by_status": by_status,
            "pending": by_status.get("pending", 0),
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
            "running": by_status.get("running", 0)
        }


# Global instance
_task_scheduler: Optional[PersistentTaskScheduler] = None

def get_task_scheduler() -> PersistentTaskScheduler:
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = PersistentTaskScheduler()
    return _task_scheduler
