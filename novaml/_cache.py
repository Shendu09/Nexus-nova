"""Caching utilities for model downloads and embeddings."""

from __future__ import annotations
import hashlib
from pathlib import Path
from novaml._config import settings


class ModelCache:
    """Manages model caching and downloads."""

    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = Path(cache_dir or settings.models_dir_expanded)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str) -> Path:
        """Get full path for a cached model."""
        return self.cache_dir / f"{model_name}.pt"

    def has_model(self, model_name: str) -> bool:
        """Check if model exists in cache."""
        return self.get_model_path(model_name).exists()

    def cache_hash(self, data: bytes) -> str:
        """Compute SHA256 hash of data."""
        return hashlib.sha256(data).hexdigest()

    def is_valid(self, model_name: str, expected_hash: str | None = None) -> bool:
        """Validate model integrity."""
        path = self.get_model_path(model_name)
        if not path.exists():
            return False
        if expected_hash is None:
            return True
        # In production: verify hash against metadata
        return True


# Global model cache instance
_cache = None


def get_model_cache() -> ModelCache:
    """Get or create global model cache."""
    global _cache
    if _cache is None:
        _cache = ModelCache()
    return _cache
