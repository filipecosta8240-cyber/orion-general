"""Tests for advanced knowledge graph"""
import pytest
from orion.knowledge_graph_advanced import AdvancedKnowledgeGraph, EntityType, RelationType, get_knowledge_graph


class TestAdvancedKnowledgeGraph:
    def test_add_entity(self):
        kg = AdvancedKnowledgeGraph()
        entity = kg.add_entity("Python", EntityType.TECHNOLOGY, "Programming language")
        assert entity is not None
        assert entity.name == "Python"

    def test_add_relation(self):
        kg = AdvancedKnowledgeGraph()
        e1 = kg.add_entity("Python", EntityType.TECHNOLOGY)
        e2 = kg.add_entity("Django", EntityType.TECHNOLOGY)
        rel = kg.add_relation(e1.id, e2.id, RelationType.USES)
        assert rel is not None
        assert rel.relation_type == RelationType.USES

    def test_get_neighbors(self):
        kg = AdvancedKnowledgeGraph()
        e1 = kg.add_entity("A", EntityType.CONCEPT)
        e2 = kg.add_entity("B", EntityType.CONCEPT)
        kg.add_relation(e1.id, e2.id, RelationType.RELATED_TO)
        neighbors = kg.get_neighbors(e1.id)
        assert len(neighbors) > 0

    def test_search_entities(self):
        kg = AdvancedKnowledgeGraph()
        kg.add_entity("Machine Learning", EntityType.TECHNOLOGY)
        kg.add_entity("Deep Learning", EntityType.TECHNOLOGY)
        results = kg.search_entities("learning")
        assert len(results) >= 2

    def test_get_statistics(self):
        kg = AdvancedKnowledgeGraph()
        kg.add_entity("Test", EntityType.CONCEPT)
        stats = kg.get_graph_statistics()
        assert stats["entity_count"] > 0
