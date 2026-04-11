"""
Unit tests for embedding fine-tuning module.
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from datetime import datetime

try:
    from nexus.models.embeddings import SimCSEEmbedder, SimCSETrainer, LogEmbeddingStore
    _embeddings_available = True
except ImportError:
    _embeddings_available = False


@pytest.mark.skipif(not _embeddings_available, reason="sentence-transformers not installed")
class TestSimCSEEmbedder:
    """Tests for SimCSE embedder."""
    
    @pytest.fixture
    def embedder(self):
        """Create embedder instance."""
        return SimCSEEmbedder()
    
    def test_embedder_init(self, embedder):
        """Test embedder initialization."""
        assert embedder is not None
        assert embedder.EMBEDDING_DIM == 768
        assert embedder.model is not None
    
    def test_encode_single(self, embedder):
        """Test encoding single sentence."""
        text = "This is a test log message"
        embedding = embedder.encode_single(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)
        assert embedding.dtype in [np.float32, np.float64]
    
    def test_encode_batch(self, embedder):
        """Test encoding batch."""
        texts = [
            "Log message 1",
            "Log message 2",
            "Log message 3"
        ]
        
        embeddings = embedder.encode(texts)
        
        assert embeddings.shape == (3, 768)
        assert isinstance(embeddings, np.ndarray)
    
    def test_similarity_cosine(self, embedder):
        """Test cosine similarity computation."""
        texts_a = [
            "High CPU alert",
            "Memory usage warning"
        ]
        texts_b = [
            "CPU spike detected",
            "Memory pressure"
        ]
        
        emb_a = embedder.encode(texts_a)
        emb_b = embedder.encode(texts_b)
        
        similarities = embedder.get_similarity(emb_a, emb_b, metric="cosine")
        
        assert similarities.shape == (2, 2)
        assert np.all(similarities <= 1.0)
        assert np.all(similarities >= -1.0)
    
    def test_get_most_similar(self, embedder):
        """Test finding most similar embeddings."""
        texts = [
            "CPU at 95%",
            "Memory at 90%",
            "CPU spike alert",
            "Database error",
            "High CPU warning"
        ]
        
        embeddings = embedder.encode(texts)
        query = embeddings[0]
        corpus = embeddings[1:]
        
        results = embedder.get_most_similar(query, corpus, top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(idx, int) and isinstance(sim, float) for idx, sim in results)
    
    def test_save_and_load(self, embedder):
        """Test saving and loading model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            embedder.save(tmpdir)
            
            # Check files exist
            assert Path(tmpdir).exists()
            
            # Load
            loaded = SimCSEEmbedder.load(tmpdir)
            
            # Test loaded model
            text = "Test embedding"
            original_emb = embedder.encode_single(text)
            loaded_emb = loaded.encode_single(text)
            
            # Embeddings should be very similar (allowing for minor numerical differences)
            assert np.allclose(original_emb, loaded_emb, atol=1e-4)


@pytest.mark.skipif(not _embeddings_available, reason="sentence-transformers not installed")
class TestSimCSETrainer:
    """Tests for SimCSE trainer."""
    
    def test_trainer_init(self):
        """Test trainer initialization."""
        trainer = SimCSETrainer()
        
        assert trainer is not None
        assert trainer.model is not None
        assert trainer.temperature == 0.05
    
    def test_prepare_log_pairs(self):
        """Test creating training pairs."""
        trainer = SimCSETrainer()
        
        logs = [
            "CPU alert 1",
            "Memory warning 1",
            "CPU alert 2",
            "Memory warning 2"
        ]
        incident_ids = ["inc-1", "inc-1", "inc-2", "inc-2"]
        
        pairs = trainer.prepare_log_pairs(logs, incident_ids)
        
        assert len(pairs) > 0
        assert all(isinstance(pair, list) for pair in pairs)
        assert all(len(pair) >= 2 for pair in pairs)


@pytest.mark.skipif(not _embeddings_available, reason="sentence-transformers not installed")
class TestLogEmbeddingStore:
    """Tests for embedding store."""
    
    @pytest.fixture
    def embedder(self):
        """Create embedder."""
        return SimCSEEmbedder()
    
    @pytest.fixture
    def store(self, embedder):
        """Create store."""
        return LogEmbeddingStore(embedder)
    
    def test_store_add_logs(self, store):
        """Test adding logs to store."""
        logs = [
            "CPU high alert",
            "Memory warning",
            "Error rate spike"
        ]
        metadata = [
            {"service": "api"},
            {"service": "worker"},
            {"service": "api"}
        ]
        
        store.add_logs(logs, metadata)
        
        assert len(store.logs) == 3
        assert store.embeddings is not None
        assert store.embeddings.shape == (3, 768)
    
    def test_store_search(self, store):
        """Test searching similar logs."""
        logs = [
            "High CPU alert on api service",
            "Memory pressure on worker",
            "CPU spike detected",
            "Database connection timeout",
            "High CPU on microservice"
        ]
        
        store.add_logs(logs)
        
        results = store.search_similar("CPU problem detected", top_k=2)
        
        assert len(results) <= 2
        assert all(
            isinstance(log, str) and isinstance(sim, float) and isinstance(meta, dict)
            for log, sim, meta in results
        )
    
    def test_store_multiple_adds(self, store):
        """Test adding logs in multiple batches."""
        batch1 = ["Log 1", "Log 2"]
        batch2 = ["Log 3", "Log 4"]
        
        store.add_logs(batch1)
        store.add_logs(batch2)
        
        assert len(store.logs) == 4
        assert store.embeddings.shape == (4, 768)


@pytest.mark.skipif(not _embeddings_available, reason="sentence-transformers not installed")
class TestEmbeddingQuality:
    """Tests for embedding quality and semantics."""
    
    @pytest.fixture
    def embedder(self):
        """Create embedder."""
        return SimCSEEmbedder()
    
    def test_semantic_similarity(self, embedder):
        """Test that semantically similar logs have high similarity."""
        similar_logs = [
            "CPU at 95%",
            "CPU spike to 95 percent"
        ]
        
        different_logs = [
            "CPU at 95%",
            "Memory at 80%"
        ]
        
        # Get embeddings
        sim_embs = embedder.encode(similar_logs)
        diff_embs = embedder.encode(different_logs)
        
        # Compute similarities
        similar_sim = embedder.get_similarity(
            sim_embs[[0]],
            sim_embs[[1]]
        )[0, 0]
        
        different_sim = embedder.get_similarity(
            diff_embs[[0]],
            diff_embs[[1]]
        )[0, 0]
        
        # Similar logs should have higher similarity
        assert similar_sim > different_sim
    
    def test_embedding_stability(self, embedder):
        """Test that embeddings are stable (same input = same output)."""
        text = "Consistent log message"
        
        emb1 = embedder.encode_single(text)
        emb2 = embedder.encode_single(text)
        
        # Should be numerically identical
        assert np.allclose(emb1, emb2, atol=1e-6)
    
    def test_embedding_normalization(self, embedder):
        """Test embedding value ranges."""
        texts = ["Random log", "Another log"]
        embeddings = embedder.encode(texts)
        
        # Check values are reasonable (not NaN, not too large)
        assert not np.any(np.isnan(embeddings))
        assert not np.any(np.isinf(embeddings))
        assert np.max(np.abs(embeddings)) < 50  # Reasonable range


class TestLogDataGenerator:
    """Tests for log data generation."""
    
    def test_generator_creates_realistic_logs(self):
        """Test that generator creates realistic log patterns."""
        from scripts.train_embeddings import LogDataGenerator
        
        gen = LogDataGenerator()
        logs, incident_ids = gen.generate_incident_logs(
            num_incidents=5,
            logs_per_incident=3
        )
        
        assert len(logs) == 15
        assert len(incident_ids) == 15
        assert all(logs)  # No empty logs
        assert all(inc_id.startswith("inc-") for inc_id in incident_ids)
    
    def test_generator_incident_grouping(self):
        """Test that logs are properly grouped by incident."""
        from scripts.train_embeddings import LogDataGenerator
        
        gen = LogDataGenerator()
        logs, incident_ids = gen.generate_incident_logs(
            num_incidents=3,
            logs_per_incident=2
        )
        
        # Count incidents
        unique_incidents = set(incident_ids)
        assert len(unique_incidents) == 3
        
        # Check grouping
        for inc_id in unique_incidents:
            count = incident_ids.count(inc_id)
            assert count == 2
