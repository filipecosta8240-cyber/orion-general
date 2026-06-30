from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from collections import Counter, defaultdict
from dataclasses import dataclass, field

@dataclass
class CacheEntry:
    """Entrada de cache com TTL"""
    key: str
    value: Any
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    ttl_seconds: int = 3600  # 1 hora default
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Verifica se cache expirou"""
        created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        expiry = created + timedelta(seconds=self.ttl_seconds)
        return datetime.now(created.tzinfo) > expiry

@dataclass
class MemoryIndex:
    """Índice para retrieval rápido"""
    index_name: str
    index_type: str  # "tag", "domain", "agent", "content"
    entries: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    def add(self, key: str, entry_id: str) -> None:
        """Adiciona entrada ao índice"""
        self.entries[key].add(entry_id)
    
    def remove(self, key: str, entry_id: str) -> None:
        """Remove entrada do índice"""
        if key in self.entries:
            self.entries[key].discard(entry_id)
            if not self.entries[key]:
                del self.entries[key]
    
    def get(self, key: str) -> Set[str]:
        """Retorna IDs de entradas para uma chave"""
        return self.entries.get(key, set())

class AdvancedMemoryManager:
    """Manager avançado de memória com caching e indexing"""
    
    def __init__(self, memory_bridge, max_cache_size: int = 1000):
        self.memory = memory_bridge
        self.cache: Dict[str, CacheEntry] = {}
        self.max_cache_size = max_cache_size
        
        # Índices para retrieval rápido
        self.tag_index = MemoryIndex("tags", "tag")
        self.domain_index = MemoryIndex("domains", "domain")
        self.agent_index = MemoryIndex("agents", "agent")
        self.source_index = MemoryIndex("sources", "source")
        
        # Índices de conteúdo para busca full-text
        self.content_keywords: Dict[str, Set[str]] = defaultdict(set)
        
        self._initialize_indices()
    
    def _initialize_indices(self) -> None:
        """Inicializa índices com dados existentes"""
        for entry in self.memory.list_entries():
            self._index_entry(entry)
    
    def _index_entry(self, entry) -> None:
        """Indexa uma entrada de memória"""
        entry_id = entry.id
        
        # Index por tags
        for tag_key, tag_value in entry.tags.items():
            index_key = f"{tag_key}:{tag_value}"
            self.tag_index.add(index_key, entry_id)
        
        # Index por domain (tag especial)
        if "domain" in entry.tags:
            domain = entry.tags["domain"]
            self.domain_index.add(domain, entry_id)
        
        # Index por agent
        if "agent" in entry.tags:
            agent = entry.tags["agent"]
            self.agent_index.add(agent, entry_id)
        
        # Index por source
        self.source_index.add(entry.source, entry_id)
        
        # Index de keywords do conteúdo
        keywords = self._extract_keywords(entry.content)
        for keyword in keywords:
            self.content_keywords[keyword].add(entry_id)
    
    def _extract_keywords(self, content: str, top_n: int = 10) -> Set[str]:
        """Extrai keywords principais do conteúdo"""
        # Simples tokenização e filtragem
        words = content.lower().split()
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        
        keywords = []
        for word in words:
            clean_word = word.strip('.,!?;:')
            if len(clean_word) > 3 and clean_word not in stop_words:
                keywords.append(clean_word)
        
        # Retorna top keywords por frequência
        word_freq = Counter(keywords)
        return set(word[0] for word in word_freq.most_common(top_n))
    
    def get_cached(self, key: str) -> Optional[Any]:
        """Recupera entrada de cache"""
        entry = self.cache.get(key)
        if not entry:
            return None
        
        if entry.is_expired():
            del self.cache[key]
            return None
        
        entry.hit_count += 1
        return entry.value
    
    def set_cached(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600
    ) -> None:
        """Guarda entrada em cache com TTL"""
        if len(self.cache) >= self.max_cache_size:
            # Remove entry menos usada (LRU)
            least_used = min(self.cache.items(), key=lambda x: x[1].hit_count)
            del self.cache[least_used[0]]
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds
        )
    
    def search_by_domain(self, domain: str) -> List[Any]:
        """Busca rápida por domain"""
        entry_ids = self.domain_index.get(domain)
        results = []
        
        for entry_id in entry_ids:
            cached = self.get_cached(f"entry:{entry_id}")
            if cached:
                results.append(cached)
            else:
                entry = self.memory.read_entry(entry_id)
                if entry:
                    self.set_cached(f"entry:{entry_id}", entry, ttl_seconds=7200)
                    results.append(entry)
        
        return results
    
    def search_by_agent(self, agent_name: str) -> List[Any]:
        """Busca rápida por agent"""
        entry_ids = self.agent_index.get(agent_name)
        results = []
        
        for entry_id in entry_ids:
            entry = self.memory.read_entry(entry_id)
            if entry:
                results.append(entry)
        
        return results
    
    def search_by_tags(self, tag_filters: Dict[str, str]) -> List[Any]:
        """Busca por múltiplas tags"""
        # Começa com primeira tag
        tag_keys = list(tag_filters.items())
        if not tag_keys:
            return []
        
        first_key, first_value = tag_keys[0]
        index_key = f"{first_key}:{first_value}"
        matching_ids = self.tag_index.get(index_key).copy()
        
        # Intersecção com outras tags
        for key, value in tag_keys[1:]:
            index_key = f"{key}:{value}"
            matching_ids &= self.tag_index.get(index_key)
        
        results = []
        for entry_id in matching_ids:
            entry = self.memory.read_entry(entry_id)
            if entry:
                results.append(entry)
        
        return results
    
    def full_text_search(self, query: str, limit: int = 20) -> List[Any]:
        """Busca full-text por keywords"""
        query_keywords = self._extract_keywords(query)
        
        # Encontra entradas que contêm qualquer keyword
        matching_ids = set()
        for keyword in query_keywords:
            matching_ids |= self.content_keywords.get(keyword, set())
        
        results = []
        for entry_id in list(matching_ids)[:limit]:
            entry = self.memory.read_entry(entry_id)
            if entry:
                results.append(entry)
        
        return results
    
    def get_recent_entries(
        self,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Any]:
        """Retorna entradas recentes opcionalmente filtradas por domain"""
        if domain:
            entries = self.search_by_domain(domain)
        else:
            entries = self.memory.list_entries()
        
        # Ordena por criação descendente
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]
    
    def clear_expired_cache(self) -> int:
        """Remove entradas expiradas do cache"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        total_hits = sum(entry.hit_count for entry in self.cache.values())
        
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "total_hits": total_hits,
            "avg_hits_per_entry": total_hits / len(self.cache) if self.cache else 0,
            "indices": {
                "tags": len(self.tag_index.entries),
                "domains": len(self.domain_index.entries),
                "agents": len(self.agent_index.entries),
                "keywords": len(self.content_keywords)
            }
        }
    
    def rebuild_indices(self) -> None:
        """Reconstrói todos os índices do zero"""
        self.tag_index = MemoryIndex("tags", "tag")
        self.domain_index = MemoryIndex("domains", "domain")
        self.agent_index = MemoryIndex("agents", "agent")
        self.source_index = MemoryIndex("sources", "source")
        self.content_keywords.clear()
        
        self._initialize_indices()
    
    def optimize_storage(self) -> Dict[str, Any]:
        """Otimiza storage limpando cache e consolidando"""
        stats = {
            "cache_cleared": self.clear_expired_cache(),
            "indices_rebuilt": False
        }
        
        # Se cache muito grande, rebuild índices
        if len(self.cache) > self.max_cache_size * 0.9:
            self.rebuild_indices()
            stats["indices_rebuilt"] = True
        
        return stats
