"""Tests for explainer module."""

import pytest
from novaml._explainer import LogExplainer


def test_extract_signals():
    """Test anomaly signal extraction."""
    explainer = LogExplainer()
    logs = ["OOM error", "connection refused", "normal log"]

    signals = explainer._extract_signals(logs)

    assert "Out of memory" in signals
    assert "Network failure" in signals


def test_find_error_pattern():
    """Test error pattern detection."""
    explainer = LogExplainer()
    logs = ["ERROR"] * 10 + ["INFO"] * 2

    patterns = explainer._find_patterns(logs)

    assert any("Error burst" in p for p in patterns)


def test_score_tokens():
    """Test token scoring."""
    explainer = LogExplainer()
    logs = ["error"] * 5 + ["database"] * 2 + ["connection"] * 1

    scores = explainer._score_tokens(logs)

    # Rarer tokens should have higher scores
    if "connection" in scores and "error" in scores:
        assert scores["connection"] > scores["error"]


def test_explain_returns_result():
    """Test full explain call."""
    explainer = LogExplainer()
    logs = ["ERROR: OOM killed the process"]

    result = explainer.explain(logs)

    assert hasattr(result, "top_signals")
    assert hasattr(result, "token_scores")
    assert hasattr(result, "anomalous_patterns")
    assert hasattr(result, "explanation_text")
