import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from orion.scheduler import ORIONProductionScheduler, ScheduledJob


class TestScheduledJob(unittest.TestCase):
    def test_interval_should_run_when_last_run_is_none(self):
        job = ScheduledJob(name="test", callback=lambda: None, interval_seconds=60)
        self.assertTrue(job.should_run(datetime.now(timezone.utc)))

    def test_interval_should_not_run_before_interval(self):
        job = ScheduledJob(name="test", callback=lambda: None, interval_seconds=60)
        job.last_run = datetime.now(timezone.utc)
        self.assertFalse(job.should_run(datetime.now(timezone.utc)))

    def test_interval_should_run_after_interval(self):
        job = ScheduledJob(name="test", callback=lambda: None, interval_seconds=60)
        job.last_run = datetime.now(timezone.utc) - timedelta(seconds=120)
        self.assertTrue(job.should_run(datetime.now(timezone.utc)))

    def test_schedule_times_exact_match(self):
        job = ScheduledJob(
            name="test",
            callback=lambda: None,
            schedule_times=["12:00", "15:30"],
        )
        now = datetime(2026, 1, 1, 15, 30)
        self.assertTrue(job.should_run(now))

    def test_schedule_times_no_match(self):
        job = ScheduledJob(
            name="test",
            callback=lambda: None,
            schedule_times=["12:00"],
        )
        now = datetime(2026, 1, 1, 14, 0)
        self.assertFalse(job.should_run(now))

    def test_weekday_filter(self):
        job = ScheduledJob(
            name="test",
            callback=lambda: None,
            schedule_times=["12:00"],
            weekdays=[0],  # Monday
        )
        # Monday
        monday = datetime(2026, 1, 5, 12, 0)
        self.assertTrue(job.should_run(monday))
        # Tuesday
        tuesday = datetime(2026, 1, 6, 12, 0)
        self.assertFalse(job.should_run(tuesday))


class TestORIONProductionScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = ORIONProductionScheduler()

    def test_add_job(self):
        job = ScheduledJob(name="test", callback=lambda: None, interval_seconds=60)
        self.scheduler.add_job(job)
        self.assertEqual(len(self.scheduler.jobs), 1)

    def test_start_stop(self):
        self.scheduler.start()
        self.assertTrue(self.scheduler.running)
        self.scheduler.stop()
        self.assertFalse(self.scheduler.running)

    def test_dispatch_calls_job(self):
        callback = Mock()
        job = ScheduledJob(name="test", callback=callback, interval_seconds=60)
        self.scheduler._dispatch(job)
        # Give thread time to execute
        import time
        time.sleep(0.1)
        callback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
