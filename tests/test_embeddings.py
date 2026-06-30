"""Tests for embedding system"""
import pytest
from orion.embeddings import EmbeddingEngine, NGramTokenizer, TFIDFVectorizer


class TestNGramTokenizer:
    def test_tokenize_basic(self):
        tokenizer = NGramTokenizer(n_min=2, n_max=3)
        tokens = tokenizer.tokenize("hello")
        assert len(tokens) > 0
        assert all(len(t) >= 2 for t in tokens)

    def test_tokenize_empty(self):
        tokenizer = NGramTokenizer()
        tokens = tokenizer.tokenize("")
        assert tokens == []


class TestEmbeddingEngine:
    def test_embed_and_similarity(self):
        engine = EmbeddingEngine()
        vec1 = engine.embed("python programming")
        vec2 = engine.embed("python coding")
        vec3 = engine.embed("chocolate cake recipe")
        sim = engine.cosine_similarity(vec1, vec2)
        sim_diff = engine.cosine_similarity(vec1, vec3)
        assert sim > sim_diff

    def test_search(self):
        engine = EmbeddingEngine()
        docs = {"1": "machine learning", "2": "space exploration", "3": "cooking recipes"}
        results = engine.search("artificial intelligence", docs)
        assert len(results) > 0

    def test_empty_search(self):
        engine = EmbeddingEngine()
        results = engine.search("test", {})
        assert results == []
