from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, List, Optional

import logging

...

logger = logging.getLogger("orion.scheduler")


class ScheduledJob:
    def __init__(self, name: str, callback: Callable[[], None], interval_seconds: Optional[int] = None, schedule_times: Optional[List[str]] = None, weekdays: Optional[List[int]] = None):
        if interval_seconds is None and not schedule_times:
            raise ValueError("At least one of interval_seconds or schedule_times must be provided")
        self.name = name
        self.callback = callback
        self.interval_seconds = interval_seconds
        self.schedule_times = schedule_times or []
        self.weekdays = weekdays
        self.last_run = None

    def should_run(self, now: datetime) -> bool:
        if self.interval_seconds is not None:
            if self.last_run is None:
                return True
            return (now - self.last_run).total_seconds() >= self.interval_seconds

        if self.schedule_times:
            if self.weekdays is not None and now.weekday() not in self.weekdays:
                return False
            current_time = now.strftime("%H:%M")
            if self.last_run is not None and self.last_run.strftime("%H:%M") == current_time:
                return False
            return current_time in self.schedule_times

        return False

class ORIONProductionScheduler:
    def __init__(self) -> None:
        self.jobs: List[ScheduledJob] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def add_job(self, job: ScheduledJob) -> None:
        self.jobs.append(job)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _run_loop(self) -> None:
        while not self.stop_event.is_set():
            now = datetime.now(timezone.utc)
            for job in self.jobs:
                if job.should_run(now):
                    self._dispatch(job)
            self.stop_event.wait(30)

    def _dispatch(self, job: ScheduledJob) -> None:
        job.last_run = datetime.now(timezone.utc)
        thread = threading.Thread(target=self._safe_execute, args=(job,), daemon=True)
        thread.start()

    def _safe_execute(self, job: ScheduledJob) -> None:
        try:
            job.callback()
        except Exception as error:
            logger.exception("Erro no job %s: %s", job.name, error)
