"""Tests for pipeline module."""

import pytest
import novaml
from novaml._models import TriageResult, AnomalyResult, Severity


def test_triage_returns_result_type():
    """Test triage returns TriageResult."""
    logs = ["ERROR: test error"]
    result = novaml.triage(logs)

    assert isinstance(result, TriageResult)
    assert hasattr(result, "severity")
    assert hasattr(result, "root_cause")
    assert hasattr(result, "next_steps")


def test_detect_returns_result_type():
    """Test detect returns AnomalyResult."""
    logs = ["ERROR: test"]
    result = novaml.detect(logs)

    assert isinstance(result, AnomalyResult)


def test_severity_is_valid_enum():
    """Test severity is valid enum."""
    logs = ["test log"]
    result = novaml.triage(logs)

    assert result.severity in [Severity.INFO, Severity.WARNING, Severity.HIGH, Severity.CRITICAL]


def test_anomalous_line_count_lte_total():
    """Test anomalous count <= total count."""
    logs = ["line1", "line2", "line3"]
    result = novaml.triage(logs)

    assert result.anomalous_line_count <= result.total_line_count
    assert result.total_line_count == 3


def test_processing_time_recorded():
    """Test processing time is recorded."""
    logs = ["test log"]
    result = novaml.triage(logs)

    assert result.processing_ms >= 0
