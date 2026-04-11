"""Tests for forecaster module."""

import pytest
from novaml._forecaster import LogForecaster


def test_forecaster_init():
    """Test forecaster initialization."""
    forecaster = LogForecaster()
    assert forecaster is not None
    assert hasattr(forecaster, "_models_cache")
