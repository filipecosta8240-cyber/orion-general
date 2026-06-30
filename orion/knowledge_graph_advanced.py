"""
ORION Advanced Knowledge Graph
===============================
Graph-based knowledge system with entities, relations, and reasoning.

Inspired by: Mem0 Pro, Neo4j, knowledge graph patterns (2026)
Features:
- Entity-relationship modeling
- Graph traversal and reasoning
- Temporal knowledge tracking
- Community detection
- Graph embeddings
"""

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger("orion.knowledge_graph")


class EntityType(str, Enum):
    CONCEPT = "concept"
    PERSON = "person"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    PROJECT = "project"
    EVENT = "event"
    LOCATION = "location"
    DOCUMENT = "document"
    SKILL = "skill"
    AGENT = "agent"


class RelationType(str, Enum):
    USES = "uses"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    CREATED_BY = "created_by"
    PART_OF = "part_of"
    CAUSED_BY = "caused_by"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"


@dataclass
class Entity:
    """Knowledge graph entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confidence: float = 1.0
    agent_id: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "agent_id": self.agent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:12]),
            name=data.get("name", ""),
            entity_type=EntityType(data.get("entity_type", "concept")),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            confidence=data.get("confidence", 1.0),
            agent_id=data.get("agent_id", "system")
        )


@dataclass
class Relation:
    """Knowledge graph relation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    agent_id: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "properties": self.properties,
            "created_at": self.created_at,
            "agent_id": self.agent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:12]),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relation_type=RelationType(data.get("relation_type", "related_to")),
            weight=data.get("weight", 1.0),
            properties=data.get("properties", {}),
            created_at=data.get("created_at", time.time()),
            agent_id=data.get("agent_id", "system")
        )


@dataclass
class GraphPath:
    """Path between two entities"""
    entities: List[Entity]
    relations: List[Relation]
    total_weight: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "total_weight": self.total_weight
        }


@dataclass
class GraphCommunity:
    """Detected community in graph"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entity_ids: List[str] = field(default_factory=list)
    label: str = ""
    density: float = 0.0
    centrality: Dict[str, float] = field(default_factory=dict)


class AdvancedKnowledgeGraph:
    """
    Advanced knowledge graph with reasoning capabilities.
    
    Features:
    - Entity-relationship modeling
    - Graph traversal (BFS, DFS, shortest path)
    - Community detection
    - Temporal reasoning
    - Confidence propagation
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("orion_knowledge")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Graph storage
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        
        # Adjacency lists for efficient traversal
        self.outgoing: Dict[str, List[str]] = defaultdict(list)  # entity_id -> [relation_ids]
        self.incoming: Dict[str, List[str]] = defaultdict(list)  # entity_id -> [relation_ids]
        
        # Load existing graph
        self._load_graph()
        
        logger.info(f"Advanced Knowledge Graph initialized with {len(self.entities)} entities, {len(self.relations)} relations")
    
    def _load_graph(self) -> None:
        """Load graph from storage"""
        try:
            graph_file = self.storage_path / "knowledge_graph.json"
            if graph_file.exists():
                data = json.loads(graph_file.read_text(encoding="utf-8"))
                
                # Load entities
                for entity_data in data.get("entities", []):
                    entity = Entity.from_dict(entity_data)
                    self.entities[entity.id] = entity
                
                # Load relations
                for relation_data in data.get("relations", []):
                    relation = Relation.from_dict(relation_data)
                    self.relations[relation.id] = relation
                    self.outgoing[relation.source_id].append(relation.id)
                    self.incoming[relation.target_id].append(relation.id)
                
                logger.info(f"Loaded {len(self.entities)} entities, {len(self.relations)} relations")
        except Exception as e:
            logger.error(f"Error loading graph: {e}")
    
    def _save_graph(self) -> None:
        """Save graph to storage"""
        try:
            graph_file = self.storage_path / "knowledge_graph.json"
            data = {
                "entities": [e.to_dict() for e in self.entities.values()],
                "relations": [r.to_dict() for r in self.relations.values()],
                "last_saved": time.time()
            }
            graph_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving graph: {e}")
    
    def add_entity(
        self,
        name: str,
        entity_type: EntityType = EntityType.CONCEPT,
        description: str = "",
        properties: Optional[Dict[str, Any]] = None,
        agent_id: str = "system",
        confidence: float = 1.0
    ) -> Entity:
        """Add a new entity to the graph"""
        # Check if entity already exists
        for entity in self.entities.values():
            if entity.name.lower() == name.lower() and entity.entity_type == entity_type:
                # Update existing entity
                entity.description = description or entity.description
                entity.properties.update(properties or {})
                entity.updated_at = time.time()
                entity.confidence = max(entity.confidence, confidence)
                self._save_graph()
                return entity
        
        # Create new entity
        entity = Entity(
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties or {},
            agent_id=agent_id,
            confidence=confidence
        )
        
        self.entities[entity.id] = entity
        self._save_graph()
        
        logger.debug(f"Added entity: {entity.name} ({entity.entity_type.value})")
        return entity
    
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType = RelationType.RELATED_TO,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        agent_id: str = "system"
    ) -> Optional[Relation]:
        """Add a relation between two entities"""
        if source_id not in self.entities or target_id not in self.entities:
            logger.warning(f"Invalid entity IDs: {source_id}, {target_id}")
            return None
        
        # Check if relation already exists
        for rel_id in self.outgoing.get(source_id, []):
            rel = self.relations.get(rel_id)
            if rel and rel.target_id == target_id and rel.relation_type == relation_type:
                # Update existing relation
                rel.weight = max(rel.weight, weight)
                rel.properties.update(properties or {})
                self._save_graph()
                return rel
        
        # Create new relation
        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            properties=properties or {},
            agent_id=agent_id
        )
        
        self.relations[relation.id] = relation
        self.outgoing[source_id].append(relation.id)
        self.incoming[target_id].append(relation.id)
        
        self._save_graph()
        
        logger.debug(f"Added relation: {source_id} -> {target_id} ({relation_type.value})")
        return relation
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        return self.entities.get(entity_id)
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name"""
        for entity in self.entities.values():
            if entity.name.lower() == name.lower():
                return entity
        return None
    
    def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation by ID"""
        return self.relations.get(relation_id)
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "both"
    ) -> List[Tuple[Entity, Relation]]:
        """Get neighboring entities"""
        neighbors = []
        
        # Outgoing relations
        if direction in ["outgoing", "both"]:
            for rel_id in self.outgoing.get(entity_id, []):
                rel = self.relations.get(rel_id)
                if rel and (relation_type is None or rel.relation_type == relation_type):
                    target = self.entities.get(rel.target_id)
                    if target:
                        neighbors.append((target, rel))
        
        # Incoming relations
        if direction in ["incoming", "both"]:
            for rel_id in self.incoming.get(entity_id, []):
                rel = self.relations.get(rel_id)
                if rel and (relation_type is None or rel.relation_type == relation_type):
                    source = self.entities.get(rel.source_id)
                    if source:
                        neighbors.append((source, rel))
        
        return neighbors
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[GraphPath]:
        """Find shortest path between two entities (BFS)"""
        if source_id not in self.entities or target_id not in self.entities:
            return None
        
        # BFS
        queue = [(source_id, [])]
        visited = {source_id}
        
        while queue:
            current_id, path_relations = queue.pop(0)
            
            if current_id == target_id:
                # Build path
                entities = [self.entities[source_id]]
                for rel in path_relations:
                    entities.append(self.entities[rel.target_id])
                return GraphPath(
                    entities=entities,
                    relations=path_relations,
                    total_weight=sum(r.weight for r in path_relations)
                )
            
            if len(path_relations) >= max_depth:
                continue
            
            # Explore neighbors
            for rel_id in self.outgoing.get(current_id, []):
                rel = self.relations.get(rel_id)
                if rel and rel.target_id not in visited:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, path_relations + [rel]))
        
        return None
    
    def bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        relation_type: Optional[RelationType] = None
    ) -> List[Tuple[Entity, int]]:
        """Breadth-first search from start entity"""
        if start_id not in self.entities:
            return []
        
        results = []
        queue = [(start_id, 0)]
        visited = {start_id}
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth > max_depth:
                continue
            
            entity = self.entities.get(current_id)
            if entity:
                results.append((entity, depth))
            
            # Explore neighbors
            for rel_id in self.outgoing.get(current_id, []):
                rel = self.relations.get(rel_id)
                if rel and rel.target_id not in visited:
                    if relation_type is None or rel.relation_type == relation_type:
                        visited.add(rel.target_id)
                        queue.append((rel.target_id, depth + 1))
        
        return results
    
    def dfs(
        self,
        start_id: str,
        max_depth: int = 3,
        relation_type: Optional[RelationType] = None
    ) -> List[Tuple[Entity, int]]:
        """Depth-first search from start entity"""
        if start_id not in self.entities:
            return []
        
        results = []
        stack = [(start_id, 0)]
        visited = set()
        
        while stack:
            current_id, depth = stack.pop()
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            entity = self.entities.get(current_id)
            if entity:
                results.append((entity, depth))
            
            # Explore neighbors
            for rel_id in self.outgoing.get(current_id, []):
                rel = self.relations.get(rel_id)
                if rel and rel.target_id not in visited:
                    if relation_type is None or rel.relation_type == relation_type:
                        stack.append((rel.target_id, depth + 1))
        
        return results
    
    def calculate_centrality(self) -> Dict[str, float]:
        """Calculate betweenness centrality for all entities"""
        centrality = {eid: 0.0 for eid in self.entities}
        
        # Simple approximation: count shortest paths through each node
        for source_id in self.entities:
            for target_id in self.entities:
                if source_id == target_id:
                    continue
                
                path = self.find_path(source_id, target_id, max_depth=3)
                if path:
                    for entity in path.entities[1:-1]:  # Exclude source and target
                        centrality[entity.id] += 1.0
        
        # Normalize
        max_centrality = max(centrality.values()) if centrality else 1.0
        if max_centrality > 0:
            for eid in centrality:
                centrality[eid] /= max_centrality
        
        return centrality
    
    def detect_communities(self) -> List[GraphCommunity]:
        """Detect communities using simple connected components"""
        visited = set()
        communities = []
        
        for entity_id in self.entities:
            if entity_id in visited:
                continue
            
            # BFS to find connected component
            component = []
            queue = [entity_id]
            
            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                
                visited.add(current_id)
                component.append(current_id)
                
                # Add neighbors
                for rel_id in self.outgoing.get(current_id, []):
                    rel = self.relations.get(rel_id)
                    if rel and rel.target_id not in visited:
                        queue.append(rel.target_id)
                
                for rel_id in self.incoming.get(current_id, []):
                    rel = self.relations.get(rel_id)
                    if rel and rel.source_id not in visited:
                        queue.append(rel.source_id)
            
            if len(component) > 1:  # Only non-trivial communities
                community = GraphCommunity(
                    entity_ids=component,
                    label=f"Community {len(communities) + 1}"
                )
                communities.append(community)
        
        return communities
    
    def get_entity_context(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get comprehensive context for an entity"""
        entity = self.entities.get(entity_id)
        if not entity:
            return {}
        
        neighbors = self.get_neighbors(entity_id)
        subgraph = self.bfs(entity_id, max_depth=depth)
        
        return {
            "entity": entity.to_dict(),
            "neighbors": [(e.to_dict(), r.to_dict()) for e, r in neighbors],
            "subgraph": [(e.to_dict(), d) for e, d in subgraph],
            "statistics": {
                "neighbor_count": len(neighbors),
                "subgraph_size": len(subgraph)
            }
        }
    
    def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 10
    ) -> List[Entity]:
        """Search entities by name or description"""
        results = []
        query_lower = query.lower()
        
        for entity in self.entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            
            if (query_lower in entity.name.lower() or 
                query_lower in entity.description.lower()):
                results.append(entity)
        
        # Sort by confidence
        results.sort(key=lambda e: e.confidence, reverse=True)
        return results[:limit]
    
    def get_temporal_entities(self, hours: int = 24) -> List[Entity]:
        """Get entities created in the last N hours"""
        cutoff = time.time() - (hours * 3600)
        return [e for e in self.entities.values() if e.created_at >= cutoff]
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        # Count entity types
        entity_types = defaultdict(int)
        for entity in self.entities.values():
            entity_types[entity.entity_type.value] += 1
        
        # Count relation types
        relation_types = defaultdict(int)
        for relation in self.relations.values():
            relation_types[relation.relation_type.value] += 1
        
        # Calculate average degree
        total_degree = sum(len(neighbors) for neighbors in self.outgoing.values())
        avg_degree = total_degree / len(self.entities) if self.entities else 0
        
        return {
            "entity_count": len(self.entities),
            "relation_count": len(self.relations),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "average_degree": avg_degree,
            "density": len(self.relations) / (len(self.entities) * (len(self.entities) - 1)) if len(self.entities) > 1 else 0
        }
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and all its relations"""
        if entity_id not in self.entities:
            return False
        
        # Remove all relations involving this entity
        rel_ids_to_remove = []
        for rel_id, rel in self.relations.items():
            if rel.source_id == entity_id or rel.target_id == entity_id:
                rel_ids_to_remove.append(rel_id)
        
        for rel_id in rel_ids_to_remove:
            rel = self.relations.pop(rel_id)
            self.outgoing[rel.source_id].remove(rel_id)
            self.incoming[rel.target_id].remove(rel_id)
        
        # Remove entity
        del self.entities[entity_id]
        self._save_graph()
        
        return True
    
    def delete_relation(self, relation_id: str) -> bool:
        """Delete a relation"""
        if relation_id not in self.relations:
            return False
        
        rel = self.relations.pop(relation_id)
        self.outgoing[rel.source_id].remove(relation_id)
        self.incoming[rel.target_id].remove(relation_id)
        
        self._save_graph()
        return True
    
    def export_graph(self) -> Dict[str, Any]:
        """Export graph as JSON"""
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
            "statistics": self.get_graph_statistics()
        }
    
    def import_graph(self, data: Dict[str, Any]) -> int:
        """Import graph from JSON"""
        imported = 0
        
        for entity_data in data.get("entities", []):
            entity = Entity.from_dict(entity_data)
            if entity.id not in self.entities:
                self.entities[entity.id] = entity
                imported += 1
        
        for relation_data in data.get("relations", []):
            relation = Relation.from_dict(relation_data)
            if relation.id not in self.relations:
                self.relations[relation.id] = relation
                self.outgoing[relation.source_id].append(relation.id)
                self.incoming[relation.target_id].append(relation.id)
                imported += 1
        
        self._save_graph()
        return imported


class KnowledgeGraphReasoner:
    """Reasoning engine over knowledge graph"""
    
    def __init__(self, graph: AdvancedKnowledgeGraph):
        self.graph = graph
    
    def infer_relations(self, entity_id: str) -> List[Tuple[Entity, RelationType, float]]:
        """Infer potential relations for an entity"""
        inferences = []
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return inferences
        
        # Get neighbors
        neighbors = self.graph.get_neighbors(entity_id)
        
        # Simple inference rules
        for neighbor, relation in neighbors:
            # If A uses B and B depends on C, A might depend on C
            if relation.relation_type == RelationType.USES:
                for rel_id in self.graph.outgoing.get(neighbor.id, []):
                    rel = self.graph.relations.get(rel_id)
                    if rel and rel.relation_type == RelationType.DEPENDS_ON:
                        target = self.graph.get_entity(rel.target_id)
                        if target:
                            inferences.append((target, RelationType.DEPENDS_ON, 0.6))
        
        return inferences
    
    def calculate_similarity(self, entity_id1: str, entity_id2: str) -> float:
        """Calculate similarity between two entities based on graph structure"""
        neighbors1 = set(e.id for e, _ in self.graph.get_neighbors(entity_id1))
        neighbors2 = set(e.id for e, _ in self.graph.get_neighbors(entity_id2))
        
        if not neighbors1 or not neighbors2:
            return 0.0
        
        intersection = len(neighbors1 & neighbors2)
        union = len(neighbors1 | neighbors2)
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_entities(
        self,
        entity_id: str,
        limit: int = 5
    ) -> List[Tuple[Entity, float]]:
        """Find similar entities based on graph structure"""
        similarities = []
        
        for other_id in self.graph.entities:
            if other_id == entity_id:
                continue
            
            similarity = self.calculate_similarity(entity_id, other_id)
            if similarity > 0.1:  # Minimum threshold
                other = self.graph.get_entity(other_id)
                if other:
                    similarities.append((other, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]


# Global instance
_knowledge_graph_instance: Optional[AdvancedKnowledgeGraph] = None

def get_knowledge_graph(storage_path: Optional[Path] = None) -> AdvancedKnowledgeGraph:
    """Get or create global knowledge graph instance"""
    global _knowledge_graph_instance
    if _knowledge_graph_instance is None:
        _knowledge_graph_instance = AdvancedKnowledgeGraph(storage_path)
    return _knowledge_graph_instance
