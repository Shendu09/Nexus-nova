"""Tests for configuration module."""

import pytest
from novaml._config import settings


def test_settings_has_required_fields():
    """Test settings has all required configuration."""
    assert hasattr(settings, "ollama_base_url")
    assert hasattr(settings, "embedding_model")
    assert hasattr(settings, "anomaly_threshold")


def test_default_anomaly_threshold():
    """Test default anomaly threshold."""
    assert settings.anomaly_threshold >= 0.0
    assert settings.anomaly_threshold <= 1.0


def test_models_dir_expanded():
    """Test models directory expansion."""
    models_dir = settings.models_dir_expanded
    assert models_dir is not None
    # Should end with '.novaml/models' after expansion
    assert "novaml" in str(models_dir)
