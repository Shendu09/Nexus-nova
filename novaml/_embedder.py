"""Log embedding via sentence-transformers."""

from __future__ import annotations
import logging
import numpy as np
from functools import lru_cache
from novaml._config import settings

logger = logging.getLogger(__name__)


class LogEmbedder:
    """Lazy-loads sentence-transformers model, encodes texts to vectors."""

    def __init__(self) -> None:
        self._model = None

    @property
    def model(self):
        """Lazy load sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {settings.embedding_model}")
                self._model = SentenceTransformer(
                    settings.embedding_model,
                    cache_folder=str(settings.models_dir_expanded / "embeddings"),
                )
            except Exception as e:
                logger.error(f"Failed to load embedder: {e}")
                raise
        return self._model

    def embed(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        """
        Embed a list of log lines.

        Args:
            texts: List of log strings
            normalize: Whether to L2-normalize vectors

        Returns:
            (N, 384) numpy array of embeddings
        """
        if not texts:
            return np.array([]).reshape(0, settings.embedding_dim)

        try:
            # Truncate long lines
            truncated = [t[:1024] if len(t) > 1024 else t for t in texts]
            embeddings = self.model.encode(truncated, batch_size=64, convert_to_numpy=True)

            if normalize and len(embeddings) > 0:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1
                embeddings = embeddings / norms

            return embeddings
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            # Return zero vectors as fallback
            return np.zeros((len(texts), settings.embedding_dim))

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single log line."""
        result = self.embed([text])
        return result[0] if len(result) > 0 else np.zeros(settings.embedding_dim)


@lru_cache(maxsize=1)
def get_embedder() -> LogEmbedder:
    """Get singleton embedder."""
    return LogEmbedder()
