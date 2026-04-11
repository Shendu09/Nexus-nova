"""Type definitions for novaml."""

from __future__ import annotations
from typing import TypeVar, Callable, Any
import numpy as np

# Type aliases
LogLine = str
LogBatch = list[str]
Embedding = np.ndarray
Embeddings = np.ndarray
AnomalyScore = float
AnomalyScores = list[float]

# Generic type variables
T = TypeVar("T")
CallableT = TypeVar("CallableT", bound=Callable[..., Any])
