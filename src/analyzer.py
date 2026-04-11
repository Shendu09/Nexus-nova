"""
Replaces: Cordon kNN anomaly detection + Nova Embeddings
With: PyTorch LSTM + Autoencoder (trained locally)
Cost: FREE — no API calls ever
"""

from __future__ import annotations
import logging
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from dataclasses import dataclass
from src.config import settings
from src.embedder import get_embedder

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result of anomaly detection on a batch of logs."""
    scores: list[float]
    anomalous_indices: list[int]
    method: str
    threshold: float


class LogAnomalyLSTM(nn.Module):
    """
    LSTM that learns sequential log patterns.
    Trained on: (embedding_sequence) -> anomaly_probability
    """

    def __init__(
        self,
        input_dim: int = 384,
        hidden_dim: int = 256,
        num_layers: int = 2,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout,
        )
        self.attention = nn.Linear(hidden_dim, 1)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape (batch, seq_len, input_dim)
        Returns:
            Tensor of shape (batch, 1) — anomaly probability
        """
        lstm_out, _ = self.lstm(x)
        attn = torch.softmax(self.attention(lstm_out), dim=1)
        context = (attn * lstm_out).sum(1)
        return self.classifier(context)


class LogAutoencoder(nn.Module):
    """
    Autoencoder trained only on NORMAL logs.
    Anomalies have high reconstruction error.
    No labels needed — fully unsupervised.
    """

    def __init__(self, input_dim: int = 384) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 64),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(64, 256),
            nn.ReLU(),
            nn.Linear(256, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """MSE reconstruction error per sample."""
        recon = self.forward(x)
        return ((x - recon) ** 2).mean(dim=1)


class AnomalyDetector:
    """
    Main anomaly detection class.
    Tries LSTM first, falls back to Autoencoder,
    then falls back to simple z-score baseline.
    """

    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.lstm: LogAnomalyLSTM | None = None
        self.autoencoder: LogAutoencoder | None = None
        self.ae_threshold: float = settings.anomaly_threshold
        self._load_models()

    def _load_models(self) -> None:
        """Load saved model weights if available."""
        lstm_path = settings.models_dir / "lstm.pt"
        ae_path = settings.models_dir / "autoencoder.pt"

        if lstm_path.exists():
            try:
                self.lstm = LogAnomalyLSTM(input_dim=settings.embedding_dim)
                self.lstm.load_state_dict(torch.load(lstm_path, map_location="cpu"))
                self.lstm.eval()
                logger.info("LSTM model loaded")
            except Exception as e:
                logger.warning(f"Failed to load LSTM: {e}")
                self.lstm = None

        if ae_path.exists():
            try:
                self.autoencoder = LogAutoencoder(input_dim=settings.embedding_dim)
                self.autoencoder.load_state_dict(
                    torch.load(ae_path, map_location="cpu")
                )
                self.autoencoder.eval()
                # Load saved threshold
                threshold_path = settings.models_dir / "ae_threshold.npy"
                if threshold_path.exists():
                    self.ae_threshold = float(np.load(threshold_path))
                logger.info(f"Autoencoder loaded, threshold={self.ae_threshold:.4f}")
            except Exception as e:
                logger.warning(f"Failed to load Autoencoder: {e}")
                self.autoencoder = None

    def detect(self, log_lines: list[str]) -> AnomalyResult:
        """
        Detect anomalous log lines.

        Args:
            log_lines: Raw log strings

        Returns:
            AnomalyResult with scores and anomalous indices
        """
        if not log_lines:
            return AnomalyResult([], [], "none", 0.0)

        embeddings = self.embedder.embed(log_lines)

        if self.lstm is not None:
            return self._detect_lstm(log_lines, embeddings)
        elif self.autoencoder is not None:
            return self._detect_autoencoder(embeddings)
        else:
            logger.warning("No trained model found — using z-score fallback")
            return self._detect_zscore(embeddings)

    def _detect_lstm(
        self,
        log_lines: list[str],
        embeddings: np.ndarray,
    ) -> AnomalyResult:
        """LSTM sliding window detection."""
        window = settings.lstm_window_size
        stride = settings.lstm_stride
        scores = [0.0] * len(log_lines)

        with torch.no_grad():
            for i in range(0, len(embeddings) - window + 1, stride):
                window_emb = embeddings[i : i + window]
                x = torch.tensor(window_emb, dtype=torch.float32).unsqueeze(0)
                score = self.lstm(x).item()
                for j in range(i, min(i + window, len(log_lines))):
                    scores[j] = max(scores[j], score)

        threshold = settings.anomaly_threshold
        anomalous = [i for i, s in enumerate(scores) if s >= threshold]
        return AnomalyResult(scores, anomalous, "lstm", threshold)

    def _detect_autoencoder(self, embeddings: np.ndarray) -> AnomalyResult:
        """Autoencoder reconstruction error detection."""
        x = torch.tensor(embeddings, dtype=torch.float32)
        with torch.no_grad():
            errors = self.autoencoder.reconstruction_error(x).numpy()

        # Normalize errors to 0–1 range
        max_err = errors.max() if errors.max() > 0 else 1.0
        scores = (errors / max_err).tolist()
        anomalous = [
            i for i, e in enumerate(errors.tolist())
            if e >= self.ae_threshold
        ]
        return AnomalyResult(scores, anomalous, "autoencoder", self.ae_threshold)

    def _detect_zscore(self, embeddings: np.ndarray) -> AnomalyResult:
        """Simple z-score fallback — no model needed."""
        norms = np.linalg.norm(embeddings, axis=1)
        mean, std = norms.mean(), norms.std()
        if std == 0:
            return AnomalyResult([0.0] * len(embeddings), [], "zscore", 3.0)
        z_scores = np.abs((norms - mean) / std)
        scores = (z_scores / z_scores.max()).tolist() if z_scores.max() > 0 else [0.0] * len(embeddings)
        anomalous = [i for i, z in enumerate(z_scores.tolist()) if z >= 3.0]
        return AnomalyResult(scores, anomalous, "zscore", 3.0)
