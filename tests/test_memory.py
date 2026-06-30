import json
import tempfile
import unittest
from pathlib import Path

from orion.memory import ObsidianMemoryBridge, MemoryEntry


class TestMemoryEntry(unittest.TestCase):
    def test_to_dict(self):
        entry = MemoryEntry(
            id="test123",
            created_at="2026-01-01T00:00:00Z",
            title="Test",
            content="Test content",
            tags={"domain": "test"},
            source="test",
        )
        d = entry.to_dict()
        self.assertEqual(d["id"], "test123")
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["source"], "test")

    def test_to_markdown(self):
        entry = MemoryEntry(
            id="test456",
            created_at="2026-01-01T00:00:00Z",
            title="Test Entry",
            content="Line 1\nLine 2",
            tags={"agent": "TEST", "domain": "test", "priority": "normal"},
            source="unittest",
        )
        md = entry.to_markdown()
        self.assertIn("agent: TEST", md)
        self.assertIn("source: unittest", md)
        self.assertIn("# Test Entry", md)
        self.assertIn("Line 1\nLine 2", md)


class TestObsidianMemoryBridge(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.bridge = ObsidianMemoryBridge(vault_root=self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmpdir))

    def test_create_and_read_entry(self):
        entry = self.bridge.create_entry(
            title="Test Memory",
            content="This is a test",
            tags={"domain": "test", "priority": "normal"},
            source="unittest",
        )
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.title, "Test Memory")
        self.assertEqual(entry.source, "unittest")

        # Read back
        read = self.bridge.read_entry(entry.id)
        self.assertIsNotNone(read)
        self.assertEqual(read.content, "This is a test")

    def test_list_entries(self):
        self.bridge.create_entry(title="A", content="a", tags={}, source="t")
        self.bridge.create_entry(title="B", content="b", tags={}, source="t")
        entries = self.bridge.list_entries()
        self.assertEqual(len(entries), 2)

    def test_search(self):
        self.bridge.create_entry(
            title="Test",
            content="data",
            tags={"agent": "ELIAS", "domain": "avicultura"},
            source="t",
        )
        results = self.bridge.search({"agent": "ELIAS"})
        self.assertEqual(len(results), 1)
        results = self.bridge.search({"agent": "DRAGAO"})
        self.assertEqual(len(results), 0)

    def test_index_persistence(self):
        e1 = self.bridge.create_entry(title="Persist", content="test", tags={}, source="t")
        # Create a new bridge pointing to same dir
        bridge2 = ObsidianMemoryBridge(vault_root=self.tmpdir)
        self.assertIsNotNone(bridge2.read_entry(e1.id))

    def test_sanitize_filename(self):
        # Access private method for testing
        safe = self.bridge._sanitize_filename("Test: Entry/With Special!Chars?", "abc123")
        self.assertNotIn(":", safe)
        self.assertNotIn("/", safe)
        self.assertTrue(safe.startswith("abc123"))


if __name__ == "__main__":
    unittest.main()
