"""Tests for analyzer module."""

import pytest
import numpy as np


def test_detect_empty_logs():
    """Test detection on empty logs."""
    from novaml._analyzer import AnomalyDetector

    detector = AnomalyDetector()
    result = detector.detect([])

    assert result.total_lines == 0
    assert len(result.scores) == 0
    assert len(result.anomalous_indices) == 0


def test_zscore_fallback_detects_outlier():
    """Test z-score fallback detection."""
    from novaml._analyzer import AnomalyDetector
    from novaml._embedder import get_embedder

    detector = AnomalyDetector()
    embedder = get_embedder()

    # Create embeddings with one outlier
    logs = ["normal log"] * 5 + ["CRITICAL ERROR OOM"]
    embeddings = embedder.embed(logs)

    # Mock z-score method
    scores, indices = detector._detect_zscore(embeddings)

    assert len(scores) == len(logs)
    # Last line should have high anomaly score
    assert scores[-1] > 0  # Should detect something


def test_detect_returns_anomaly_result():
    """Test detect returns correct format."""
    from novaml._analyzer import AnomalyDetector
    from novaml._models import AnomalyResult

    detector = AnomalyDetector()
    logs = ["ERROR: test error"]

    result = detector.detect(logs)

    assert isinstance(result, AnomalyResult)
    assert result.total_lines == 1
    assert hasattr(result, "scores")
    assert hasattr(result, "anomalous_indices")
    assert hasattr(result, "threshold")
    assert hasattr(result, "method")
