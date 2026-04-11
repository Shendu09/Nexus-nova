"""
Nexus Nova ML Models Package

This package contains deep learning models for:
- Autoencoder-based anomaly detection
- LSTM-based sequential analysis
- Classification models
"""

from .autoencoder import LogAutoencoder
from .bert_classifier import (
    SeverityClassifier,
    SeverityClassifierConfig,
    SeverityClassifierTrainer,
    SeverityPrediction
)

try:
    from .lstm import LogAnomalyLSTM, LogAnomalyLSTMConfig, LogSequenceDataset, LogAnomalyLSTMScorer
    _lstm_available = True
except ImportError:
    _lstm_available = False

__all__ = [
    "LogAutoencoder",
    "SeverityClassifier",
    "SeverityClassifierConfig",
    "SeverityClassifierTrainer",
    "SeverityPrediction",
]

if _lstm_available:
    __all__.extend([
        "LogAnomalyLSTM",
        "LogAnomalyLSTMConfig",
        "LogSequenceDataset",
        "LogAnomalyLSTMScorer",
    ])
