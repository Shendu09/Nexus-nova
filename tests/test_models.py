"""Tests for models module."""

import pytest
from novaml._models import TriageResult, AnomalyResult, Severity, ExplainResult


def test_triage_result_to_dict():
    """Test TriageResult serialization to dict."""
    result = TriageResult(
        severity=Severity.CRITICAL,
        root_cause="OOM",
        confidence=0.95,
        anomalous_line_count=5,
        total_line_count=100,
    )

    d = result.to_dict()
    assert d["severity"] == "CRITICAL"
    assert d["root_cause"] == "OOM"
    assert d["confidence"] == 0.95


def test_triage_result_to_json():
    """Test TriageResult JSON serialization."""
    result = TriageResult(
        severity=Severity.HIGH,
        root_cause="Error",
        confidence=0.85,
    )

    json_str = result.to_json()
    assert "HIGH" in json_str
    assert "Error" in json_str


def test_severity_enum_values():
    """Test all severity values exist."""
    assert Severity.INFO.value == "INFO"
    assert Severity.WARNING.value == "WARNING"
    assert Severity.HIGH.value == "HIGH"
    assert Severity.CRITICAL.value == "CRITICAL"


def test_confidence_validation():
    """Test confidence field validation."""
    with pytest.raises(ValueError):
        TriageResult(
            severity=Severity.INFO,
            root_cause="test",
            confidence=1.5,  # Invalid
        )

    # Valid
    result = TriageResult(
        severity=Severity.INFO,
        root_cause="test",
        confidence=0.5,
    )
    assert result.confidence == 0.5


def test_anomaly_result_format():
    """Test AnomalyResult structure."""
    result = AnomalyResult(
        scores=[0.1, 0.2, 0.9, 0.15],
        anomalous_indices=[2],
        threshold=0.5,
        method="lstm",
        total_lines=4,
    )

    assert len(result.scores) == 4
    assert len(result.anomalous_indices) == 1
    assert result.anomalous_indices[0] == 2
