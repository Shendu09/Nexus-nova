"""
Replaces: AWS Nova Embeddings
With: sentence-transformers (all-MiniLM-L6-v2)
Cost: FREE — runs locally, no API calls
"""

from __future__ import annotations
import logging
import numpy as np
from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from src.config import settings

logger = logging.getLogger(__name__)


class LogEmbedder:
    """Converts log lines into semantic vector embeddings."""

    def __init__(self) -> None:
        self.model_name = settings.embedding_model
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load model on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            cache_dir = settings.models_dir / "embeddings"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(cache_dir)
            )
            logger.info("Embedding model loaded successfully")
        return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        """
        Embed a list of log lines into vectors.

        Args:
            texts: List of log line strings

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        # Truncate very long lines to 256 tokens
        texts = [t[:1024] for t in texts]

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,  # L2 normalize for cosine similarity
            )
            logger.debug(f"Embedded {len(texts)} log lines")
            return embeddings
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            # Fallback: return zero vectors
            return np.zeros((len(texts), settings.embedding_dim))

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single log line."""
        result = self.embed([text])
        return result[0] if len(result) > 0 else np.zeros(settings.embedding_dim)


@lru_cache(maxsize=1)
def get_embedder() -> LogEmbedder:
    """Singleton embedder instance."""
    return LogEmbedder()
