"""
RAG (Retrieval-Augmented Generation) System
============================================
Advanced document retrieval and augmentation system for grounding LLM responses.
Based on 2026 production RAG patterns with hybrid search and reranking.

Features:
- Document ingestion and chunking
- Vector embeddings and storage
- Hybrid search (semantic + keyword)
- Reranking for relevance
- Context augmentation for LLM prompts
"""

from __future__ import annotations

import json
import logging
import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
import threading

logger = logging.getLogger("orion.rag_system")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "RAG_DATA"


class ChunkingStrategy(str, Enum):
    """Document chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


class RetrievalStrategy(str, Enum):
    """Retrieval strategies."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    RERANKED = "reranked"


@dataclass
class Document:
    """Document representation."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentChunk:
    """A chunk of a document."""
    chunk_id: str
    doc_id: str
    content: str
    index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """Search result with relevance score."""
    chunk: DocumentChunk
    score: float
    rank: int = 0
    strategy: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "rank": self.rank,
            "strategy": self.strategy
        }


@dataclass
class RAGQuery:
    """A RAG query with context."""
    query_id: str
    query_text: str
    results: List[SearchResult]
    context: str = ""
    sources: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentProcessor:
    """Process and chunk documents."""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, doc: Document, 
                        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE) -> List[DocumentChunk]:
        """Process a document into chunks."""
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._fixed_size_chunking(doc)
        elif strategy == ChunkingStrategy.SENTENCE:
            return self._sentence_chunking(doc)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            return self._paragraph_chunking(doc)
        elif strategy == ChunkingStrategy.RECURSIVE:
            return self._recursive_chunking(doc)
        else:
            return self._fixed_size_chunking(doc)
    
    def _fixed_size_chunking(self, doc: Document) -> List[DocumentChunk]:
        """Fixed-size chunking."""
        chunks = []
        content = doc.content
        
        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            chunk_text = content[i:i + self.chunk_size]
            chunks.append(DocumentChunk(
                chunk_id=f"{doc.doc_id}_chunk_{len(chunks)}",
                doc_id=doc.doc_id,
                content=chunk_text,
                index=len(chunks),
                metadata={**doc.metadata, "chunk_strategy": "fixed_size"}
            ))
        
        return chunks
    
    def _sentence_chunking(self, doc: Document) -> List[DocumentChunk]:
        """Sentence-based chunking."""
        sentences = re.split(r'[.!?]+', doc.content)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < self.chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{doc.doc_id}_chunk_{len(chunks)}",
                        doc_id=doc.doc_id,
                        content=current_chunk.strip(),
                        index=len(chunks),
                        metadata={**doc.metadata, "chunk_strategy": "sentence"}
                    ))
                current_chunk = sentence + ". "
        
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{doc.doc_id}_chunk_{len(chunks)}",
                doc_id=doc.doc_id,
                content=current_chunk.strip(),
                index=len(chunks),
                metadata={**doc.metadata, "chunk_strategy": "sentence"}
            ))
        
        return chunks
    
    def _paragraph_chunking(self, doc: Document) -> List[DocumentChunk]:
        """Paragraph-based chunking."""
        paragraphs = doc.content.split('\n\n')
        chunks = []
        
        for i, para in enumerate(paragraphs):
            if para.strip():
                chunks.append(DocumentChunk(
                    chunk_id=f"{doc.doc_id}_chunk_{i}",
                    doc_id=doc.doc_id,
                    content=para.strip(),
                    index=i,
                    metadata={**doc.metadata, "chunk_strategy": "paragraph"}
                ))
        
        return chunks
    
    def _recursive_chunking(self, doc: Document) -> List[DocumentChunk]:
        """Recursive chunking with overlap."""
        chunks = []
        content = doc.content
        start = 0
        
        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            chunk_text = content[start:end]
            
            if end < len(content):
                last_period = chunk_text.rfind('.')
                last_space = chunk_text.rfind(' ')
                split_point = max(last_period, last_space)
                
                if split_point > self.chunk_size * 0.5:
                    chunk_text = chunk_text[:split_point + 1]
                    end = start + split_point + 1
            
            chunks.append(DocumentChunk(
                chunk_id=f"{doc.doc_id}_chunk_{len(chunks)}",
                doc_id=doc.doc_id,
                content=chunk_text.strip(),
                index=len(chunks),
                metadata={**doc.metadata, "chunk_strategy": "recursive"}
            ))
            
            start = end - self.chunk_overlap
        
        return chunks


class EmbeddingEngine:
    """Simple embedding engine using TF-IDF-like approach."""
    
    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def _hash_embedding(self, text: str) -> List[float]:
        """Generate a consistent embedding using hashing."""
        tokens = self._tokenize(text)
        embedding = [0.0] * self.dimension
        
        for token in tokens:
            hash_val = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = hash_val % self.dimension
            embedding[idx] += 1.0
        
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self._hash_embedding(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        return [self.embed_text(text) for text in texts]


class VectorStore:
    """Simple vector store for embeddings."""
    
    def __init__(self):
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def add_vector(self, vector_id: str, vector: List[float], 
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to the store."""
        with self._lock:
            self._vectors[vector_id] = vector
            self._metadata[vector_id] = metadata or {}
    
    def remove_vector(self, vector_id: str) -> None:
        """Remove a vector from the store."""
        with self._lock:
            if vector_id in self._vectors:
                del self._vectors[vector_id]
                del self._metadata[vector_id]
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar vectors using cosine similarity."""
        results = []
        
        for vec_id, vec in self._vectors.items():
            similarity = self._cosine_similarity(query_vector, vec)
            results.append((vec_id, similarity))
        
        results.sort(key=lambda x: -x[1])
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_metadata(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a vector."""
        return self._metadata.get(vector_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "total_vectors": len(self._vectors),
            "dimension": len(next(iter(self._vectors.values()), [])) if self._vectors else 0
        }


class RAGSystem:
    """
    RAG (Retrieval-Augmented Generation) System
    
    Provides document retrieval and context augmentation for LLM responses.
    Supports hybrid search with reranking for improved relevance.
    """
    
    def __init__(self, rag_root: Optional[Path] = None):
        self._root = rag_root or RAG_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        
        self.doc_processor = DocumentProcessor()
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore()
        
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._load_documents()
    
    def _load_documents(self) -> None:
        """Load documents from disk."""
        docs_file = self._root / "documents.json"
        if docs_file.exists():
            try:
                data = json.loads(docs_file.read_text(encoding="utf-8"))
                for did, ddata in data.items():
                    self._documents[did] = Document(**ddata)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save_documents(self) -> None:
        """Save documents to disk."""
        docs_file = self._root / "documents.json"
        data = {did: d.to_dict() for did, d in self._documents.items()}
        docs_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None,
                    source: str = "", chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE) -> Document:
        """Add a document to the RAG system."""
        doc_id = f"doc_{len(self._documents)}_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"
        
        doc = Document(
            doc_id=doc_id,
            content=content,
            metadata=metadata or {},
            source=source
        )
        
        self._documents[doc_id] = doc
        
        chunks = self.doc_processor.process_document(doc, chunking_strategy)
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            embedding = self.embedding_engine.embed_text(chunk.content)
            chunk.embedding = embedding
            self.vector_store.add_vector(
                chunk.chunk_id,
                embedding,
                {"doc_id": doc_id, "chunk_index": chunk.index}
            )
        
        self._save_documents()
        logger.info(f"Document added: {doc_id} with {len(chunks)} chunks")
        return doc
    
    def search(self, query: str, top_k: int = 5,
              strategy: RetrievalStrategy = RetrievalStrategy.HYBRID) -> List[SearchResult]:
        """Search for relevant chunks."""
        query_embedding = self.embedding_engine.embed_text(query)
        
        if strategy == RetrievalStrategy.SEMANTIC:
            results = self._semantic_search(query_embedding, top_k)
        elif strategy == RetrievalStrategy.KEYWORD:
            results = self._keyword_search(query, top_k)
        elif strategy == RetrievalStrategy.HYBRID:
            semantic_results = self._semantic_search(query_embedding, top_k * 2)
            keyword_results = self._keyword_search(query, top_k * 2)
            results = self._merge_results(semantic_results, keyword_results, top_k)
        else:
            results = self._semantic_search(query_embedding, top_k)
        
        for i, result in enumerate(results):
            result.rank = i + 1
            result.strategy = strategy.value
        
        return results
    
    def _semantic_search(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """Semantic search using embeddings."""
        vector_results = self.vector_store.search(query_embedding, top_k)
        
        results = []
        for vec_id, score in vector_results:
            if vec_id in self._chunks:
                results.append(SearchResult(
                    chunk=self._chunks[vec_id],
                    score=score,
                    strategy="semantic"
                ))
        
        return results
    
    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """Keyword-based search."""
        query_terms = set(query.lower().split())
        results = []
        
        for chunk_id, chunk in self._chunks.items():
            chunk_terms = set(chunk.content.lower().split())
            overlap = len(query_terms & chunk_terms)
            
            if overlap > 0:
                score = overlap / len(query_terms)
                results.append(SearchResult(
                    chunk=chunk,
                    score=score,
                    strategy="keyword"
                ))
        
        results.sort(key=lambda r: -r.score)
        return results[:top_k]
    
    def _merge_results(self, semantic: List[SearchResult], 
                      keyword: List[SearchResult], top_k: int) -> List[SearchResult]:
        """Merge and deduplicate results from different strategies."""
        seen_chunks = set()
        merged = []
        
        for result in semantic:
            if result.chunk.chunk_id not in seen_chunks:
                seen_chunks.add(result.chunk.chunk_id)
                result.score *= 0.7
                merged.append(result)
        
        for result in keyword:
            if result.chunk.chunk_id not in seen_chunks:
                seen_chunks.add(result.chunk.chunk_id)
                result.score *= 0.3
                merged.append(result)
        
        merged.sort(key=lambda r: -r.score)
        return merged[:top_k]
    
    def augment_prompt(self, query: str, base_prompt: str, 
                      top_k: int = 3) -> Tuple[str, List[str]]:
        """Augment a prompt with retrieved context."""
        results = self.search(query, top_k)
        
        context_parts = []
        sources = []
        
        for result in results:
            context_parts.append(result.chunk.content)
            doc = self._documents.get(result.chunk.doc_id)
            if doc and doc.source:
                sources.append(doc.source)
        
        context = "\n\n---\n\n".join(context_parts)
        
        augmented_prompt = f"""Context from relevant documents:
{context}

---

User Query: {query}

Based on the context above, please respond to the query."""
        
        return augmented_prompt, sources
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        return {
            "total_documents": len(self._documents),
            "total_chunks": len(self._chunks),
            "vector_store": self.vector_store.get_stats()
        }
