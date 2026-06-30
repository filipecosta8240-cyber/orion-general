"""
ORION Embedding System
=======================
Semantic similarity and embedding generation for memory retrieval.

Features:
- Character n-gram embeddings (stdlib-only, no external deps)
- Cosine similarity calculation
- TF-IDF weighted embeddings
- Batch embedding generation
"""

import math
import re
import hashlib
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger("orion.embeddings")


@dataclass
class EmbeddingVector:
    """Document embedding vector"""
    vector: Dict[int, float]  # Sparse vector: {feature_index: weight}
    dimension: int = 10000
    features: List[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "vector": {str(k): v for k, v in self.vector.items()},
            "dimension": self.dimension
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EmbeddingVector":
        return cls(
            vector={int(k): v for k, v in data.get("vector", {}).items()},
            dimension=data.get("dimension", 10000)
        )


class NGramTokenizer:
    """Character n-gram tokenizer"""
    
    def __init__(self, n_min: int = 2, n_max: int = 4):
        self.n_min = n_min
        self.n_max = n_max
    
    def tokenize(self, text: str) -> List[str]:
        """Generate character n-grams"""
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        ngrams = []
        for n in range(self.n_min, self.n_max + 1):
            for i in range(len(text) - n + 1):
                ngrams.append(text[i:i+n])
        return ngrams


class TFIDFVectorizer:
    """TF-IDF vectorizer for text"""
    
    def __init__(self, max_features: int = 10000):
        self.max_features = max_features
        self.tokenizer = NGramTokenizer()
        self.idf: Dict[str, float] = {}
        self.feature_index: Dict[str, int] = {}
        self.doc_count = 0
        self.fitted = False
    
    def fit(self, texts: List[str]) -> "TFIDFVectorizer":
        """Fit vectorizer on corpus"""
        doc_freq = Counter()
        
        for text in texts:
            tokens = set(self.tokenizer.tokenize(text))
            for token in tokens:
                doc_freq[token] += 1
            self.doc_count += 1
        
        # Build feature index (top N by frequency)
        sorted_tokens = sorted(doc_freq.items(), key=lambda x: -x[1])
        for i, (token, _) in enumerate(sorted_tokens[:self.max_features]):
            self.feature_index[token] = i
        
        # Calculate IDF
        for token in self.feature_index:
            df = doc_freq.get(token, 1)
            self.idf[token] = math.log((self.doc_count + 1) / (df + 1)) + 1
        
        self.fitted = True
        return self
    
    def transform(self, text: str) -> EmbeddingVector:
        """Transform text to embedding vector"""
        if not self.fitted:
            raise ValueError("Vectorizer not fitted")
        
        tokens = self.tokenizer.tokenize(text)
        tf = Counter(tokens)
        
        vector = {}
        max_tf = max(tf.values()) if tf else 1
        
        for token, count in tf.items():
            if token in self.feature_index:
                tfidf = (count / max_tf) * self.idf.get(token, 1)
                idx = self.feature_index[token]
                vector[idx] = tfidf
        
        return EmbeddingVector(
            vector=vector,
            dimension=self.max_features,
            features=list(tf.keys())
        )


class EmbeddingEngine:
    """
    Embedding engine for semantic similarity.
    Uses TF-IDF with character n-grams for stdlib-only operation.
    """
    
    def __init__(self):
        self.vectorizer = TFIDFVectorizer(max_features=10000)
        self.fitted = False
        self.document_store: Dict[str, Dict] = {}  # doc_id -> {text, embedding}
    
    def fit(self, documents: List[str]) -> "EmbeddingEngine":
        """Fit embedding engine on documents"""
        self.vectorizer.fit(documents)
        self.fitted = True
        return self
    
    def embed(self, text: str) -> EmbeddingVector:
        """Generate embedding for text"""
        if not self.fitted:
            # Auto-fit on first document
            self.vectorizer.fit([text])
            self.fitted = True
        return self.vectorizer.transform(text)
    
    def cosine_similarity(self, vec1: EmbeddingVector, vec2: EmbeddingVector) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1.vector or not vec2.vector:
            return 0.0
        
        intersection = set(vec1.vector.keys()) & set(vec2.vector.keys())
        
        dot_product = sum(vec1.vector[k] * vec2.vector[k] for k in intersection)
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.vector.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.vector.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def search(
        self,
        query: str,
        documents: Dict[str, str],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float, str]]:
        """Search documents by similarity to query"""
        if not documents:
            return []
        
        query_vec = self.embed(query)
        
        results = []
        for doc_id, text in documents.items():
            doc_vec = self.embed(text)
            similarity = self.cosine_similarity(query_vec, doc_vec)
            if similarity > threshold:
                results.append((doc_id, similarity, text))
        
        results.sort(key=lambda x: -x[1])
        return results[:top_k]
    
    def batch_embed(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for multiple texts"""
        return [self.embed(text) for text in texts]
    
    def similarity_matrix(self, texts: List[str]) -> List[List[float]]:
        """Calculate similarity matrix for a list of texts"""
        vectors = self.batch_embed(texts)
        n = len(vectors)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(i, n):
                sim = self.cosine_similarity(vectors[i], vectors[j])
                matrix[i][j] = sim
                matrix[j][i] = sim
        
        return matrix


# Global instance
_embedding_engine: Optional[EmbeddingEngine] = None

def get_embedding_engine() -> EmbeddingEngine:
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine
