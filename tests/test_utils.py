"""Tests for utility modules."""

import pytest
from novaml._utils import truncate_text, normalize_log_line, extract_level, batch_list


def test_truncate_text():
    """Test text truncation."""
    short = "hello"
    long = "x" * 2000

    assert truncate_text(short) == short
    assert len(truncate_text(long)) == 1024


def test_normalize_log_line():
    """Test log normalization."""
    # With ANSI codes
    line = "\x1b[31mERROR\x1b[0m message"
    normalized = normalize_log_line(line)
    assert "ERROR" in normalized
    assert "\x1b" not in normalized


def test_extract_level():
    """Test level extraction."""
    assert extract_level("INFO: message") == "INFO"
    assert extract_level("ERROR: test") == "ERROR"
    assert extract_level("plain text") is None


def test_batch_list():
    """Test list batching."""
    items = list(range(10))
    batches = batch_list(items, 3)
    assert len(batches) == 4
    assert len(batches[0]) == 3
    assert len(batches[3]) == 1
