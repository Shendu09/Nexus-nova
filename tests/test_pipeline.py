"""Full pipeline tests — runs with zero real AWS or Ollama needed."""

import pytest
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock
from src.embedder import LogEmbedder
from src.analyzer import AnomalyDetector, LogAutoencoder
from src.triage import LogTriager, TriageReport
from src.classifier import SeverityClassifier

SAMPLE_LOGS = [
    "2024-01-01 INFO Service started successfully",
    "2024-01-01 INFO Processing request id=123",
    "2024-01-01 ERROR Connection refused to database",
    "2024-01-01 ERROR Retrying... attempt 1/3",
    "2024-01-01 FATAL Out of memory — process killed",
    "2024-01-01 INFO Health check passed",
]


class TestEmbedder:
    def test_embed_returns_correct_shape(self):
        embedder = LogEmbedder()
        with patch.object(embedder, "model") as mock_model:
            mock_model.encode.return_value = np.random.rand(6, 384)
            result = embedder.embed(SAMPLE_LOGS)
            assert result.shape == (6, 384)

    def test_embed_empty_returns_empty(self):
        embedder = LogEmbedder()
        result = embedder.embed([])
        assert len(result) == 0

    def test_embed_single(self):
        embedder = LogEmbedder()
        with patch.object(embedder, "model") as mock_model:
            mock_model.encode.return_value = np.random.rand(1, 384)
            result = embedder.embed_single("test log line")
            assert result.shape == (384,)


class TestAnomalyDetector:
    def test_zscore_fallback_detects_anomalies(self):
        detector = AnomalyDetector()
        detector.lstm = None
        detector.autoencoder = None

        with patch.object(detector.embedder, "embed") as mock_embed:
            # Make one line very different from others
            embeddings = np.random.rand(6, 384) * 0.1
            embeddings[4] = np.ones(384) * 10.0  # Outlier
            mock_embed.return_value = embeddings

            result = detector.detect(SAMPLE_LOGS)
            assert result.method == "zscore"
            assert 4 in result.anomalous_indices

    def test_empty_logs_returns_empty(self):
        detector = AnomalyDetector()
        result = detector.detect([])
        assert result.scores == []
        assert result.anomalous_indices == []


class TestTriager:
    @pytest.mark.asyncio
    async def test_rule_based_fallback_oom(self):
        triager = LogTriager()
        result = triager._rule_based_fallback(
            SAMPLE_LOGS,
            ["FATAL Out of memory — process killed"],
        )
        assert result.severity == "CRITICAL"
        assert result.model_used == "rule-based-fallback"

    @pytest.mark.asyncio
    async def test_ollama_failure_uses_fallback(self):
        triager = LogTriager()
        with patch.object(triager, "_call_ollama", side_effect=Exception("Connection refused")):
            result = await triager.analyze(SAMPLE_LOGS, [2, 3, 4])
            assert result.severity in ["INFO", "WARNING", "HIGH", "CRITICAL"]
            assert result.model_used == "rule-based-fallback"


class TestSeverityClassifier:
    def test_keyword_fallback_critical(self):
        clf = SeverityClassifier()
        clf._model = None
        result = clf.predict("FATAL out of memory process killed OOM")
        assert result.label == "CRITICAL"

    def test_keyword_fallback_high(self):
        clf = SeverityClassifier()
        clf._model = None
        result = clf.predict("ERROR connection refused database")
        assert result.label == "HIGH"

    def test_confidence_is_valid_range(self):
        clf = SeverityClassifier()
        clf._model = None
        result = clf.predict("INFO service started")
        assert 0.0 <= result.confidence <= 1.0
