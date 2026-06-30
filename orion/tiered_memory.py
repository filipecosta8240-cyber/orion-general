"""
ORION Tiered Memory System
===========================
Advanced memory architecture inspired by Letta/MemGPT and Mem0 (2026 patterns).

Memory Tiers:
- Working Memory: Current context (RAM-like, always in context)
- Episodic Memory: Specific past events (cache-like, retrieved as needed)
- Semantic Memory: Extracted facts and preferences (vector store)
- Procedural Memory: Learned skills and workflows (long-term storage)

Features:
- OS-inspired tiered architecture (Letta pattern)
- Automatic fact extraction (Mem0 pattern)
- Memory consolidation and forgetting
- Temporal awareness
- Knowledge graph integration
"""

import json
import time
import uuid
import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger("orion.tiered_memory")


class MemoryTier(str, Enum):
    WORKING = "working"      # Current context (RAM)
    EPISODIC = "episodic"    # Past events (Cache)
    SEMANTIC = "semantic"    # Facts & preferences (Vector Store)
    PROCEDURAL = "procedural"  # Skills & workflows (Long-term)


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    SKILL = "skill"
    RELATIONSHIP = "relationship"
    TEMPORAL = "temporal"


@dataclass
class MemoryItem:
    """Individual memory item with metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    content: str = ""
    memory_type: MemoryType = MemoryType.FACT
    tier: MemoryTier = MemoryTier.SEMANTIC
    agent_id: str = "system"
    confidence: float = 1.0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    relations: List[str] = field(default_factory=list)  # Related memory IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "tier": self.tier.value,
            "agent_id": self.agent_id,
            "confidence": self.confidence,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "tags": self.tags,
            "relations": self.relations,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:12]),
            content=data.get("content", ""),
            memory_type=MemoryType(data.get("memory_type", "fact")),
            tier=MemoryTier(data.get("tier", "semantic")),
            agent_id=data.get("agent_id", "system"),
            confidence=data.get("confidence", 1.0),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed", time.time()),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            tags=data.get("tags", {}),
            relations=data.get("relations", []),
            metadata=data.get("metadata", {})
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def access(self) -> None:
        self.access_count += 1
        self.last_accessed = time.time()

    def decay_score(self, decay_factor: float = 0.95) -> float:
        """Calculate relevance score with time decay"""
        time_since_access = time.time() - self.last_accessed
        hours_since = time_since_access / 3600
        return self.confidence * (decay_factor ** hours_since)


@dataclass
class FactExtraction:
    """Extracted fact from conversation"""
    fact: str
    confidence: float
    memory_type: MemoryType
    entities: List[str]
    relations: List[Tuple[str, str, str]]  # (subject, predicate, object)
    source: str = ""
    timestamp: float = field(default_factory=time.time)


class FactExtractor:
    """Extracts facts from text (Mem0-inspired pattern)"""
    
    # Patterns for fact extraction
    FACT_PATTERNS = [
        (r"(?:I|user)\s+(?:prefer|like|want|need)\s+(.+)", MemoryType.PREFERENCE),
        (r"(?:I|user)\s+(?:use|work with|develop in)\s+(.+)", MemoryType.FACT),
        (r"(?:I|user)\s+(?:am|is)\s+(?:a|an)\s+(.+)", MemoryType.FACT),
        (r"(?:project|system)\s+(?:is called|named)\s+(.+)", MemoryType.FACT),
        (r"(?:I|user)\s+(?:want to|plan to|need to)\s+(.+)", MemoryType.FACT),
    ]
    
    def extract(self, text: str, agent_id: str = "system") -> List[FactExtraction]:
        """Extract facts from text"""
        facts = []
        text_lower = text.lower()
        
        for pattern, mem_type in self.FACT_PATTERNS:
            import re
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                fact_text = match.group(1).strip()
                if len(fact_text) > 5:  # Minimum fact length
                    facts.append(FactExtraction(
                        fact=fact_text,
                        confidence=0.8,
                        memory_type=mem_type,
                        entities=self._extract_entities(fact_text),
                        relations=self._extract_relations(fact_text),
                        source=agent_id
                    ))
        
        # Extract named entities
        entities = self._extract_entities(text)
        if entities:
            facts.append(FactExtraction(
                fact=f"Entities mentioned: {', '.join(entities)}",
                confidence=0.6,
                memory_type=MemoryType.FACT,
                entities=entities,
                relations=[],
                source=agent_id
            ))
        
        return facts
    
    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction"""
        import re
        # Capitalized words that might be entities
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        # Common entity patterns
        tech_entities = re.findall(r'\b(?:Python|JavaScript|TypeScript|React|Node|Docker|Kubernetes|AI|ML|LLM|GPT|Claude|ORION)\b', text, re.IGNORECASE)
        return list(set(entities + tech_entities))
    
    def _extract_relations(self, text: str) -> List[Tuple[str, str, str]]:
        """Extract relations from text"""
        import re
        relations = []
        # Simple relation patterns
        patterns = [
            (r'(\w+)\s+uses\s+(\w+)', "uses"),
            (r'(\w+)\s+depends on\s+(\w+)', "depends_on"),
            (r'(\w+)\s+implements\s+(\w+)', "implements"),
        ]
        for pattern, predicate in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                relations.append((match.group(1), predicate, match.group(2)))
        return relations


class TieredMemorySystem:
    """
    Advanced tiered memory system inspired by Letta/MemGPT and Mem0.
    
    Architecture:
    - Working Memory: Current context (always in prompt)
    - Episodic Memory: Past events (retrieved by similarity)
    - Semantic Memory: Facts & preferences (vector search)
    - Procedural Memory: Skills & workflows (long-term)
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("orion_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Memory tiers
        self.working_memory: List[MemoryItem] = []  # Always in context
        self.episodic_memory: List[MemoryItem] = []  # Past events
        self.semantic_memory: List[MemoryItem] = []  # Facts & preferences
        self.procedural_memory: List[MemoryItem] = []  # Skills & workflows
        
        # Fact extractor
        self.fact_extractor = FactExtractor()
        
        # Configuration
        self.max_working_items = 20  # Max items in working memory
        self.max_episodic_items = 1000  # Max items in episodic memory
        self.similarity_threshold = 0.7  # Minimum similarity for retrieval
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load existing memory
        self._load_memory()
        
        logger.info(f"Tiered Memory System initialized with {self._total_items()} items")
    
    def _total_items(self) -> int:
        return (len(self.working_memory) + len(self.episodic_memory) + 
                len(self.semantic_memory) + len(self.procedural_memory))
    
    def _load_memory(self) -> None:
        """Load memory from storage"""
        try:
            memory_file = self.storage_path / "tiered_memory.json"
            if memory_file.exists():
                data = json.loads(memory_file.read_text(encoding="utf-8"))
                self.working_memory = [MemoryItem.from_dict(m) for m in data.get("working", [])]
                self.episodic_memory = [MemoryItem.from_dict(m) for m in data.get("episodic", [])]
                self.semantic_memory = [MemoryItem.from_dict(m) for m in data.get("semantic", [])]
                self.procedural_memory = [MemoryItem.from_dict(m) for m in data.get("procedural", [])]
                logger.info(f"Loaded {self._total_items()} memory items")
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
    
    def _save_memory(self) -> None:
        """Save memory to storage"""
        try:
            memory_file = self.storage_path / "tiered_memory.json"
            data = {
                "working": [m.to_dict() for m in self.working_memory],
                "episodic": [m.to_dict() for m in self.episodic_memory],
                "semantic": [m.to_dict() for m in self.semantic_memory],
                "procedural": [m.to_dict() for m in self.procedural_memory],
                "last_saved": time.time()
            }
            memory_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        tier: MemoryTier = MemoryTier.SEMANTIC,
        agent_id: str = "system",
        confidence: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
        expires_in_hours: Optional[int] = None,
        auto_extract: bool = True
    ) -> MemoryItem:
        """Add a new memory item"""
        with self._lock:
            # Create memory item
            item = MemoryItem(
                content=content,
                memory_type=memory_type,
                tier=tier,
                agent_id=agent_id,
                confidence=confidence,
                tags=tags or {},
                expires_at=time.time() + (expires_in_hours * 3600) if expires_in_hours else None
            )
            
            # Add to appropriate tier
            if tier == MemoryTier.WORKING:
                self.working_memory.append(item)
                # Enforce max working memory
                if len(self.working_memory) > self.max_working_items:
                    # Move oldest to episodic
                    oldest = self.working_memory.pop(0)
                    oldest.tier = MemoryTier.EPISODIC
                    self.episodic_memory.append(oldest)
            elif tier == MemoryTier.EPISODIC:
                self.episodic_memory.append(item)
                # Enforce max episodic memory
                if len(self.episodic_memory) > self.max_episodic_items:
                    # Remove oldest expired items
                    self.episodic_memory = [m for m in self.episodic_memory if not m.is_expired()]
                    # If still over limit, remove lowest confidence
                    if len(self.episodic_memory) > self.max_episodic_items:
                        self.episodic_memory.sort(key=lambda m: m.confidence)
                        self.episodic_memory = self.episodic_memory[-self.max_episodic_items:]
            elif tier == MemoryTier.SEMANTIC:
                self.semantic_memory.append(item)
            elif tier == MemoryTier.PROCEDURAL:
                self.procedural_memory.append(item)
            
            # Auto-extract facts if enabled
            if auto_extract and tier == MemoryTier.EPISODIC:
                facts = self.fact_extractor.extract(content, agent_id)
                for fact in facts:
                    self.add_memory(
                        content=fact.fact,
                        memory_type=fact.memory_type,
                        tier=MemoryTier.SEMANTIC,
                        agent_id=agent_id,
                        confidence=fact.confidence,
                        auto_extract=False
                    )
            
            # Save memory
            self._save_memory()
            
            logger.debug(f"Added memory: {item.id} to {tier.value}")
            return item
    
    def recall(
        self,
        query: str,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> List[MemoryItem]:
        """Recall memories matching query"""
        with self._lock:
            # Select tiers to search
            if tier:
                tiers = [self._get_tier_list(tier)]
            else:
                tiers = [self.working_memory, self.episodic_memory, 
                        self.semantic_memory, self.procedural_memory]
            
            results = []
            query_lower = query.lower()
            
            for tier_list in tiers:
                for item in tier_list:
                    if item.is_expired():
                        continue
                    
                    # Simple text matching (in production, use vector similarity)
                    if query_lower in item.content.lower():
                        if item.confidence >= min_confidence:
                            item.access()  # Update access count
                            results.append(item)
            
            # Sort by relevance (decay score)
            results.sort(key=lambda m: m.decay_score(), reverse=True)
            
            return results[:limit]
    
    def get_working_context(self) -> str:
        """Get current working memory as context string"""
        with self._lock:
            context_parts = []
            for item in self.working_memory:
                context_parts.append(f"[{item.memory_type.value}] {item.content}")
            return "\n".join(context_parts)
    
    def consolidate_memories(self) -> int:
        """Consolidate memories: merge similar, promote frequent, demote infrequent"""
        with self._lock:
            consolidated = 0
            
            # Promote frequent episodic memories to semantic
            for item in self.episodic_memory[:]:
                if item.access_count > 5 and item.confidence > 0.7:
                    item.tier = MemoryTier.SEMANTIC
                    self.semantic_memory.append(item)
                    self.episodic_memory.remove(item)
                    consolidated += 1
            
            # Demote infrequent semantic memories to episodic
            for item in self.semantic_memory[:]:
                if item.access_count == 0 and item.decay_score() < 0.3:
                    item.tier = MemoryTier.EPISODIC
                    self.episodic_memory.append(item)
                    self.semantic_memory.remove(item)
                    consolidated += 1
            
            # Remove expired memories
            for tier_list in [self.working_memory, self.episodic_memory, 
                            self.semantic_memory, self.procedural_memory]:
                tier_list[:] = [m for m in tier_list if not m.is_expired()]
            
            if consolidated > 0:
                self._save_memory()
                logger.info(f"Consolidated {consolidated} memories")
            
            return consolidated
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "working": len(self.working_memory),
            "episodic": len(self.episodic_memory),
            "semantic": len(self.semantic_memory),
            "procedural": len(self.procedural_memory),
            "total": self._total_items(),
            "working_capacity": self.max_working_items,
            "episodic_capacity": self.max_episodic_items
        }
    
    def _get_tier_list(self, tier: MemoryTier) -> List[MemoryItem]:
        """Get list for specified tier"""
        if tier == MemoryTier.WORKING:
            return self.working_memory
        elif tier == MemoryTier.EPISODIC:
            return self.episodic_memory
        elif tier == MemoryTier.SEMANTIC:
            return self.semantic_memory
        elif tier == MemoryTier.PROCEDURAL:
            return self.procedural_memory
        return []
    
    def search_by_type(self, memory_type: MemoryType, limit: int = 50) -> List[MemoryItem]:
        """Search memories by type"""
        results = []
        for tier_list in [self.working_memory, self.episodic_memory, 
                        self.semantic_memory, self.procedural_memory]:
            for item in tier_list:
                if item.memory_type == memory_type:
                    results.append(item)
                    if len(results) >= limit:
                        return results
        return results
    
    def search_by_agent(self, agent_id: str, limit: int = 50) -> List[MemoryItem]:
        """Search memories by agent"""
        results = []
        for tier_list in [self.working_memory, self.episodic_memory, 
                        self.semantic_memory, self.procedural_memory]:
            for item in tier_list:
                if item.agent_id == agent_id:
                    results.append(item)
                    if len(results) >= limit:
                        return results
        return results
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        with self._lock:
            for tier_list in [self.working_memory, self.episodic_memory, 
                            self.semantic_memory, self.procedural_memory]:
                for i, item in enumerate(tier_list):
                    if item.id == memory_id:
                        tier_list.pop(i)
                        self._save_memory()
                        return True
            return False
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[MemoryItem]:
        """Update a memory item"""
        with self._lock:
            for tier_list in [self.working_memory, self.episodic_memory, 
                            self.semantic_memory, self.procedural_memory]:
                for item in tier_list:
                    if item.id == memory_id:
                        for key, value in updates.items():
                            if hasattr(item, key):
                                setattr(item, key, value)
                        self._save_memory()
                        return item
            return None
    
    def get_temporal_memories(self, hours: int = 24) -> List[MemoryItem]:
        """Get memories from the last N hours"""
        cutoff = time.time() - (hours * 3600)
        results = []
        for tier_list in [self.working_memory, self.episodic_memory, 
                        self.semantic_memory, self.procedural_memory]:
            for item in tier_list:
                if item.created_at >= cutoff:
                    results.append(item)
        return results
    
    def get_recent_memories(self, limit: int = 20) -> List[MemoryItem]:
        """Get most recent memories"""
        all_items = []
        for tier_list in [self.working_memory, self.episodic_memory, 
                        self.semantic_memory, self.procedural_memory]:
            all_items.extend(tier_list)
        
        all_items.sort(key=lambda m: m.created_at, reverse=True)
        return all_items[:limit]
    
    def get_important_memories(self, limit: int = 20) -> List[MemoryItem]:
        """Get most important memories (by confidence and access)"""
        all_items = []
        for tier_list in [self.working_memory, self.episodic_memory, 
                        self.semantic_memory, self.procedural_memory]:
            all_items.extend(tier_list)
        
        all_items.sort(key=lambda m: m.confidence * (1 + m.access_count), reverse=True)
        return all_items[:limit]


class MemoryConsolidator:
    """Background memory consolidation process"""
    
    def __init__(self, memory_system: TieredMemorySystem):
        self.memory_system = memory_system
        self.consolidation_interval = 3600  # 1 hour
        self.last_consolidation = time.time()
    
    def should_consolidate(self) -> bool:
        """Check if consolidation should run"""
        return time.time() - self.last_consolidation >= self.consolidation_interval
    
    def run_consolidation(self) -> Dict[str, Any]:
        """Run memory consolidation"""
        if not self.should_consolidate():
            return {"status": "skipped", "reason": "too_soon"}
        
        start_time = time.time()
        consolidated = self.memory_system.consolidate_memories()
        duration = time.time() - start_time
        
        self.last_consolidation = time.time()
        
        return {
            "status": "completed",
            "consolidated": consolidated,
            "duration_seconds": duration,
            "stats": self.memory_system.get_memory_stats()
        }


# Global instance
_tiered_memory_instance: Optional[TieredMemorySystem] = None

def get_tiered_memory(storage_path: Optional[Path] = None) -> TieredMemorySystem:
    """Get or create global tiered memory instance"""
    global _tiered_memory_instance
    if _tiered_memory_instance is None:
        _tiered_memory_instance = TieredMemorySystem(storage_path)
    return _tiered_memory_instance
