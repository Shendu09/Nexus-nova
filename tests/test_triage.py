"""Tests for triage module."""

import pytest
from novaml._triage import LogTriager
from novaml._models import Severity


def test_rule_based_triage_oom():
    """Test OOM detection in fallback."""
    triager = LogTriager()
    text = "FATAL: out of memory error detected"
    report = triager._rule_based_triage(text)

    assert report.severity == Severity.CRITICAL


def test_rule_based_triage_connection():
    """Test connection error detection."""
    triager = LogTriager()
    text = "ERROR: connection refused to database"
    report = triager._rule_based_triage(text)

    assert report.severity == Severity.HIGH


def test_fallback_unknown_error():
    """Test default fallback."""
    triager = LogTriager()
    text = "something strange happened"
    report = triager._rule_based_triage(text)

    assert report.severity == Severity.WARNING  # Default fallback
