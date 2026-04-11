"""Tests for classifier module."""

import pytest
from novaml._classifier import SeverityClassifier
from novaml._models import Severity


def test_keyword_critical_on_fatal():
    """Test keyword detection for CRITICAL."""
    classifier = SeverityClassifier()
    result = classifier.predict("FATAL: Out of memory error")

    assert result.label == Severity.CRITICAL
    assert result.confidence >= 0.7


def test_keyword_high_on_error():
    """Test keyword detection for HIGH."""
    classifier = SeverityClassifier()
    result = classifier.predict("ERROR: Connection refused")

    assert result.label == Severity.HIGH
    assert result.confidence >= 0.6


def test_keyword_warning():
    """Test keyword detection for WARNING."""
    classifier = SeverityClassifier()
    result = classifier.predict("WARNING: Slow response time detected")

    assert result.label == Severity.WARNING


def test_default_info():
    """Test default to INFO."""
    classifier = SeverityClassifier()
    result = classifier.predict("Normal application log message")

    assert result.label == Severity.INFO


def test_confidence_in_valid_range():
    """Test confidence is between 0 and 1."""
    classifier = SeverityClassifier()
    result = classifier.predict("test log")

    assert 0.0 <= result.confidence <= 1.0
