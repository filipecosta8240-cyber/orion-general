"""
ORION General Agent - Memória de Longo Prazo
=============================================
Sistema de memória persistente independente da memória ORION.

Capacidades:
- Armazena conhecimento persistentemente
- Indexação por temas e categorias
- Busca semântica avançada
- Compressão e resumo automático
- Memória de factos, preferências e lições aprendidas
"""

import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class MemoryType(Enum):
    """Tipos de memória"""
    FACT = "fact"
    PREFERENCE = "preference"
    LESSON = "lesson"
    INSIGHT = "insight"
    CONTEXT = "context"
    TASK = "task"


@dataclass
class MemoryEntry:
    """Entrada de memória"""
    id: str
    content: str
    memory_type: str
    category: str
    keywords: List[str]
    importance: float  # 0-1
    access_count: int
    last_accessed: str
    created_at: str
    source: str
    context: Optional[Dict] = None


@dataclass
class MemoryCluster:
    """Cluster de memórias relacionadas"""
    cluster_id: str
    name: str
    description: str
    memory_ids: List[str]
    created_at: str
    last_updated: str


class LongTermMemory:
    """
    Sistema de Memória de Longo Prazo do General
    =============================================
    
    Memória persistente:
    1. Armazena factos, preferências, lições
    2. Indexa por categorias e palavras-chave
    3. Busca por relevância e semelhança
    4. Comprime automaticamente memórias antigas
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent / "data" / "general_memory")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.memories_file = self.data_dir / "long_term_memories.json"
        self.clusters_file = self.data_dir / "memory_clusters.json"
        self.index_file = self.data_dir / "memory_index.json"
        
        self.memories: List[MemoryEntry] = []
        self.clusters: List[MemoryCluster] = []
        self.index: Dict[str, List[str]] = {}  # keyword -> memory_ids
        
        self._load_data()
    
    def _load_data(self):
        """Carrega dados do disco"""
        if self.memories_file.exists():
            with open(self.memories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.memories = [MemoryEntry(**m) for m in data]
        
        if self.clusters_file.exists():
            with open(self.clusters_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.clusters = [MemoryCluster(**c) for c in data]
        
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.index = json.load(f)
    
    def _save_data(self):
        """Guarda dados no disco"""
        with open(self.memories_file, "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.memories], f, ensure_ascii=False, indent=2)
        
        with open(self.clusters_file, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self.clusters], f, ensure_ascii=False, indent=2)
        
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, content: str) -> str:
        """Gera ID único"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extrai palavras-chave do conteúdo"""
        # Remove pontuação e converte para minúsculas
        words = content.lower().split()
        # Remove palavras curtas e comuns
        stop_words = {"o", "a", "os", "as", "um", "uma", "de", "do", "da", "em", "no", "na", "com", "por", "para", "e", "ou", "mas", "que", "se", "não", "é", "está", "tem", "foi", "ser", "ter", "como", "mais", "muito", "bem", "já", "ainda", "só", "também", "isso", "este", "esta", "esse", "essa"}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return list(set(keywords))[:10]  # Máximo 10 keywords
    
    def store(
        self,
        content: str,
        memory_type: MemoryType,
        category: str,
        importance: float = 0.5,
        source: str = "general",
        context: Dict = None
    ) -> MemoryEntry:
        """
        Armazena uma nova memória
        
        Args:
            content: Conteúdo da memória
            memory_type: Tipo de memória
            category: Categoria
            importance: Importância (0-1)
            source: Fonte da memória
            context: Contexto adicional
        
        Returns:
            Memória criada
        """
        keywords = self._extract_keywords(content)
        
        memory = MemoryEntry(
            id=self._generate_id(f"{content}{datetime.now()}"),
            content=content,
            memory_type=memory_type.value,
            category=category,
            keywords=keywords,
            importance=importance,
            access_count=0,
            last_accessed=datetime.now(timezone.utc).isoformat(),
            created_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            context=context,
        )
        
        self.memories.append(memory)
        
        # Atualiza índice
        for keyword in keywords:
            if keyword not in self.index:
                self.index[keyword] = []
            self.index[keyword].append(memory.id)
        
        # Auto-cluster: agrupa memórias da mesma categoria
        self._auto_cluster(memory)
        
        self._save_data()
        return memory
    
    def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Recupera memórias relevantes
        
        Args:
            query: Consulta de busca
            memory_type: Filtrar por tipo
            category: Filtrar por categoria
            limit: Limite de resultados
        
        Returns:
            Lista de memórias relevantes
        """
        query_keywords = self._extract_keywords(query)
        
        # Busca por palavras-chave
        matching_ids = set()
        for keyword in query_keywords:
            if keyword in self.index:
                matching_ids.update(self.index[keyword])
        
        # Filtra memórias
        candidates = []
        for memory in self.memories:
            if memory.id not in matching_ids:
                continue
            
            if memory_type and memory.memory_type != memory_type.value:
                continue
            
            if category and memory.category != category:
                continue
            
            # Calcula relevância
            relevance = self._calculate_relevance(memory, query_keywords)
            candidates.append((memory, relevance))
        
        # Ordena por relevância
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Atualiza contadores de acesso
        results = []
        for memory, relevance in candidates[:limit]:
            memory.access_count += 1
            memory.last_accessed = datetime.now(timezone.utc).isoformat()
            results.append(memory)
        
        self._save_data()
        return results
    
    def _calculate_relevance(self, memory: MemoryEntry, query_keywords: List[str]) -> float:
        """Calcula relevância de uma memória"""
        if not query_keywords:
            return 0.0
        
        # Correspondência de palavras-chave
        keyword_matches = sum(1 for kw in query_keywords if kw in memory.keywords)
        keyword_score = keyword_matches / len(query_keywords)
        
        # Bónus por importância
        importance_bonus = memory.importance * 0.3
        
        # Bónus por frequência de acesso
        access_bonus = min(0.2, memory.access_count * 0.02)
        
        # Penalidade por idade (memórias mais recentes são preferidas)
        days_old = (datetime.now(timezone.utc) - datetime.fromisoformat(memory.created_at.replace('Z', '+00:00'))).days
        age_penalty = min(0.3, days_old * 0.01)
        
        return keyword_score + importance_bonus + access_bonus - age_penalty
    
    def _auto_cluster(self, memory: MemoryEntry):
        """Agrupa automaticamente memórias da mesma categoria"""
        # Procura cluster existente para a categoria
        for cluster in self.clusters:
            if cluster.name == memory.category:
                cluster.memory_ids.append(memory.id)
                cluster.last_updated = datetime.now(timezone.utc).isoformat()
                return
        
        # Cria novo cluster
        cluster = MemoryCluster(
            cluster_id=self._generate_id(f"cluster_{memory.category}"),
            name=memory.category,
            description=f"Memórias da categoria: {memory.category}",
            memory_ids=[memory.id],
            created_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        self.clusters.append(cluster)
    
    def compress_old_memories(self, days_threshold: int = 90):
        """
        Comprime memórias antigas
        
        Args:
            days_threshold: Dias para considerar "antiga"
        """
        now = datetime.now(timezone.utc)
        
        old_memories = []
        recent_memories = []
        
        for memory in self.memories:
            created = datetime.fromisoformat(memory.created_at.replace('Z', '+00:00'))
            days_old = (now - created).days
            
            if days_old > days_threshold and memory.importance < 0.7:
                old_memories.append(memory)
            else:
                recent_memories.append(memory)
        
        # Cria resumo das memórias antigas
        if old_memories:
            summary_content = f"Resumo de {len(old_memories)} memórias antigas:\n"
            for memory in old_memories[:10]:
                summary_content += f"- {memory.content[:100]}...\n"
            
            # Armazena resumo
            self.store(
                content=summary_content,
                memory_type=MemoryType.INSIGHT,
                category="compressed_history",
                importance=0.3,
                source="compression",
            )
            
            # Remove memórias antigas
            self.memories = recent_memories
            self._rebuild_index()
            self._save_data()
    
    def _rebuild_index(self):
        """Reconstrói índice de palavras-chave"""
        self.index = {}
        for memory in self.memories:
            for keyword in memory.keywords:
                if keyword not in self.index:
                    self.index[keyword] = []
                self.index[keyword].append(memory.id)
    
    def get_facts(self, limit: int = 20) -> List[MemoryEntry]:
        """Retorna factos armazenados"""
        return [m for m in self.memories if m.memory_type == MemoryType.FACT.value][:limit]
    
    def get_lessons(self, limit: int = 20) -> List[MemoryEntry]:
        """Retorna lições aprendidas"""
        return [m for m in self.memories if m.memory_type == MemoryType.LESSON.value][:limit]
    
    def get_preferences(self) -> List[MemoryEntry]:
        """Retorna preferências do utilizador"""
        return [m for m in self.memories if m.memory_type == MemoryType.PREFERENCE.value]
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da memória"""
        type_counts = {}
        for memory in self.memories:
            t = memory.memory_type
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "total_memories": len(self.memories),
            "total_clusters": len(self.clusters),
            "total_keywords": len(self.index),
            "by_type": type_counts,
        }
    
    def get_memory_summary(self) -> str:
        """Retorna resumo da memória"""
        stats = self.get_stats()
        
        summary = f"""
🧠 **RESUMO DE MEMÓRIA DE LONGO PRAZO - GENERAL AGENT**

**Total de Memórias:** {stats['total_memories']}
**Clusters:** {stats['total_clusters']}
**Palavras-chave Indexadas:** {stats['total_keywords']}

**Por Tipo:**
"""
        
        type_names = {
            "fact": "Factos",
            "preference": "Preferências",
            "lesson": "Lixções",
            "insight": "Insights",
            "context": "Contexto",
            "task": "Tarefas",
        }
        
        for t, count in stats["by_type"].items():
            name = type_names.get(t, t)
            summary += f"- {name}: {count}\n"
        
        # Últimas memórias
        summary += "\n**Últimas Memórias:**\n"
        for memory in self.memories[-5:]:
            summary += f"- [{memory.memory_type}] {memory.content[:80]}...\n"
        
        return summary


# Instância global
_memory = None


def get_long_term_memory(data_dir: str = None) -> LongTermMemory:
    """Retorna instância global da memória de longo prazo"""
    global _memory
    if _memory is None:
        _memory = LongTermMemory(data_dir)
    return _memory
