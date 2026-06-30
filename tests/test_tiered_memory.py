"""Tests for tiered memory system"""
import pytest
from orion.tiered_memory import (
    TieredMemorySystem, MemoryTier, MemoryType, FactExtractor, get_tiered_memory
)


class TestTieredMemorySystem:
    def test_add_memory(self):
        memory = TieredMemorySystem()
        item = memory.add_memory("test fact", MemoryType.FACT, MemoryTier.SEMANTIC)
        assert item is not None
        assert item.content == "test fact"

    def test_recall_memory(self):
        memory = TieredMemorySystem()
        memory.add_memory("python programming", MemoryType.FACT, MemoryTier.SEMANTIC)
        results = memory.recall("python")
        assert len(results) > 0
        assert "python" in results[0].content.lower()

    def test_recall_no_match(self):
        memory = TieredMemorySystem()
        results = memory.recall("nonexistent_term_x789")
        assert len(results) == 0

    def test_working_memory_limit(self):
        memory = TieredMemorySystem()
        memory.max_working_items = 3
        for i in range(5):
            memory.add_memory(f"item {i}", MemoryType.FACT, MemoryTier.WORKING)
        assert len(memory.working_memory) <= 3

    def test_get_stats(self):
        memory = TieredMemorySystem()
        memory.add_memory("test", MemoryType.FACT, MemoryTier.SEMANTIC)
        stats = memory.get_memory_stats()
        assert "total" in stats
        assert stats["total"] > 0


class TestFactExtractor:
    def test_extract_preference(self):
        extractor = FactExtractor()
        facts = extractor.extract("I prefer Python for coding")
        assert len(facts) > 0
        types = [f.memory_type for f in facts]
        assert MemoryType.PREFERENCE in types or MemoryType.FACT in types

    def test_extract_empty(self):
        extractor = FactExtractor()
        facts = facts = extractor.extract("")
        assert len(facts) == 0 or all(len(f.fact) <= 5 for f in facts)
