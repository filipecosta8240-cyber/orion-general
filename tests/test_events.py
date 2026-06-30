import unittest
from unittest.mock import Mock

from orion.events import EventBus, Event, EventType


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus(max_history=100)

    def test_publish_and_subscribe(self):
        callback = Mock()
        self.bus.subscribe([EventType.SYSTEM_STARTED], callback, subscriber_id="test")
        event = Event(type=EventType.SYSTEM_STARTED, source="test", payload={"msg": "hello"})
        self.bus.publish(event)
        callback.assert_called_once_with(event)

    def test_no_callback_for_unsubscribed_type(self):
        callback = Mock()
        self.bus.subscribe([EventType.SYSTEM_STARTED], callback, subscriber_id="test")
        event = Event(type=EventType.SYSTEM_ERROR, source="test")
        self.bus.publish(event)
        callback.assert_not_called()

    def test_unsubscribe(self):
        callback = Mock()
        sub_id = self.bus.subscribe([EventType.SYSTEM_STARTED], callback)
        self.bus.unsubscribe(sub_id)
        event = Event(type=EventType.SYSTEM_STARTED, source="test")
        self.bus.publish(event)
        callback.assert_not_called()

    def test_event_history(self):
        e1 = Event(type=EventType.SYSTEM_STARTED, source="a")
        e2 = Event(type=EventType.SYSTEM_STOPPED, source="b")
        self.bus.publish(e1)
        self.bus.publish(e2)
        history = self.bus.get_history()
        self.assertEqual(len(history), 2)

    def test_event_history_filter_by_type(self):
        self.bus.publish(Event(type=EventType.SYSTEM_STARTED, source="a"))
        self.bus.publish(Event(type=EventType.SYSTEM_STOPPED, source="b"))
        self.bus.publish(Event(type=EventType.SYSTEM_STARTED, source="c"))
        started = self.bus.get_history(event_type=EventType.SYSTEM_STARTED)
        self.assertEqual(len(started), 2)

    def test_event_history_limit(self):
        for i in range(10):
            self.bus.publish(Event(type=EventType.SYSTEM_STARTED, source=f"s{i}"))
        limited = self.bus.get_history(limit=3)
        self.assertEqual(len(limited), 3)

    def test_max_history_enforced(self):
        small_bus = EventBus(max_history=5)
        for i in range(10):
            small_bus.publish(Event(type=EventType.SYSTEM_STARTED, source=f"s{i}"))
        self.assertEqual(len(small_bus.event_history), 5)

    def test_statistics(self):
        self.bus.publish(Event(type=EventType.SYSTEM_STARTED, source="a"))
        self.bus.publish(Event(type=EventType.SYSTEM_STOPPED, source="b"))
        stats = self.bus.get_statistics()
        self.assertEqual(stats["total_events"], 2)


class TestEvent(unittest.TestCase):
    def test_event_creation(self):
        event = Event(
            type=EventType.SYSTEM_STARTED,
            source="test",
            payload={"key": "value"},
            priority="high",
        )
        self.assertEqual(event.type, EventType.SYSTEM_STARTED)
        self.assertEqual(event.priority, "high")
        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.timestamp)

    def test_to_dict(self):
        event = Event(type=EventType.AGENT_ACTION_STARTED, source="agent_x")
        d = event.to_dict()
        self.assertEqual(d["type"], "agent.action.started")
        self.assertEqual(d["source"], "agent_x")
        self.assertIn("event_id", d)
        self.assertIn("timestamp", d)


if __name__ == "__main__":
    unittest.main()
