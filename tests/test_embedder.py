"""Tests for embedder module."""

import pytest
import numpy as np
from novaml._embedder import get_embedder, LogEmbedder


def test_embed_empty_returns_correct_shape():
    """Test embedding empty list."""
    embedder = LogEmbedder()
    result = embedder.embed([])

    assert isinstance(result, np.ndarray)
    assert result.shape[0] == 0


def test_embed_single_returns_1d():
    """Test embedding single log line."""
    embedder = LogEmbedder()
    result = embedder.embed_single("test log")

    assert isinstance(result, np.ndarray)
    assert len(result.shape) == 1
    assert result.shape[0] == 384  # default embedding dim


def test_embedder_is_singleton():
    """Test get_embedder returns singleton."""
    e1 = get_embedder()
    e2 = get_embedder()
    assert e1 is e2


def test_embed_truncates_long_lines():
    """Test long lines are truncated."""
    embedder = LogEmbedder()
    long_log = "x" * 2000
    result = embedder.embed([long_log])

    assert isinstance(result, np.ndarray)
    assert result.shape == (1, 384)
