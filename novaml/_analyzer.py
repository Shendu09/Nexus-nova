"""Anomaly detection with LSTM and Autoencoder."""

from __future__ import annotations
import logging
import numpy as np
from pathlib import Path
from novaml._config import settings
from novaml._models import AnomalyResult, Severity
from novaml._embedder import get_embedder

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Anomaly detection with multiple fallback strategies."""

    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.lstm_model = None
        self.autoencoder_model = None
        self.ae_threshold = settings.anomaly_threshold
        self._load_models()

    def _load_models(self) -> None:
        """Try to load pre-trained models from disk."""
        try:
            import torch
            model_dir = settings.models_dir_expanded

            lstm_path = model_dir / "lstm_anomaly.pt"
            if lstm_path.exists():
                logger.info(f"Loading LSTM from {lstm_path}")
                self.lstm_model = torch.load(lstm_path)

            ae_path = model_dir / "autoencoder.pt"
            if ae_path.exists():
                logger.info(f"Loading autoencoder from {ae_path}")
                self.autoencoder_model = torch.load(ae_path)

            ae_threshold_path = model_dir / "ae_threshold.npy"
            if ae_threshold_path.exists():
                self.ae_threshold = float(np.load(ae_threshold_path))
                logger.info(f"Loaded threshold: {self.ae_threshold:.4f}")
        except Exception as e:
            logger.warning(f"Could not load pre-trained models: {e}")

    def detect(self, logs: list[str]) -> AnomalyResult:
        """
        Detect anomalies using LSTM → Autoencoder → z-score cascade.

        Args:
            logs: List of log lines

        Returns:
            AnomalyResult with scores, indices, method
        """
        if not logs:
            return AnomalyResult(
                scores=[],
                anomalous_indices=[],
                threshold=self.ae_threshold,
                method="empty",
                total_lines=0,
            )

        # Get embeddings
        embeddings = self.embedder.embed(logs)

        # Try LSTM first
        if self.lstm_model is not None:
            try:
                scores, indices = self._detect_lstm(embeddings)
                return AnomalyResult(
                    scores=scores.tolist(),
                    anomalous_indices=indices.tolist(),
                    threshold=0.5,
                    method="lstm",
                    total_lines=len(logs),
                )
            except Exception as e:
                logger.warning(f"LSTM detection failed: {e}")

        # Fall back to autoencoder
        if self.autoencoder_model is not None:
            try:
                scores, indices = self._detect_autoencoder(embeddings)
                return AnomalyResult(
                    scores=scores.tolist(),
                    anomalous_indices=indices.tolist(),
                    threshold=self.ae_threshold,
                    method="autoencoder",
                    total_lines=len(logs),
                )
            except Exception as e:
                logger.warning(f"Autoencoder detection failed: {e}")

        # Fall back to z-score
        scores, indices = self._detect_zscore(embeddings)
        return AnomalyResult(
            scores=scores.tolist(),
            anomalous_indices=indices.tolist(),
            threshold=2.0,
            method="zscore",
            total_lines=len(logs),
        )

    def _detect_lstm(self, embeddings: np.ndarray) -> tuple:
        """Detect anomalies using LSTM model."""
        import torch

        # Sliding window
        window_size = settings.lstm_window_size
        stride = settings.lstm_stride
        scores = np.zeros(len(embeddings))

        with torch.no_grad():
            for start in range(0, len(embeddings) - window_size + 1, stride):
                window = embeddings[start:start + window_size]
                tensor = torch.from_numpy(window).float().unsqueeze(0)
                output = self.lstm_model(tensor)
                window_scores = output.squeeze().numpy()
                scores[start:start + window_size] = np.maximum(
                    scores[start:start + window_size], window_scores
                )

        threshold = 0.5
        indices = np.where(scores > threshold)[0]
        return scores, indices

    def _detect_autoencoder(self, embeddings: np.ndarray) -> tuple:
        """Detect anomalies using reconstruction error."""
        import torch

        with torch.no_grad():
            tensor = torch.from_numpy(embeddings).float()
            reconstructed = self.autoencoder_model(tensor)
            errors = torch.mean((tensor - reconstructed) ** 2, dim=1).numpy()

        threshold = self.ae_threshold
        indices = np.where(errors > threshold)[0]
        return errors, indices

    def _detect_zscore(self, embeddings: np.ndarray) -> tuple:
        """Detect anomalies using z-score on embedding distances."""
        # Compute distances to mean embedding
        mean_emb = np.mean(embeddings, axis=0)
        distances = np.linalg.norm(embeddings - mean_emb, axis=1)

        # Z-score
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)

        if std_dist == 0:
            return distances, np.array([])

        z_scores = np.abs((distances - mean_dist) / std_dist)
        threshold = 2.0
        indices = np.where(z_scores > threshold)[0]
        return z_scores, indices

    def train_autoencoder(self, logs: list[str], save_dir: str = "~/.novaml/models") -> dict:
        """Train autoencoder on logs (unsupervised)."""
        logger.info(f"Training autoencoder on {len(logs)} logs")

        embeddings = self.embedder.embed(logs)
        if len(embeddings) < 10:
            return {"error": "Not enough logs to train", "model_path": None}

        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import TensorDataset, DataLoader

            # Build simple autoencoder
            class SimpleAutoencoder(nn.Module):
                def __init__(self, input_dim=384):
                    super().__init__()
                    self.encoder = nn.Sequential(
                        nn.Linear(input_dim, 256),
                        nn.ReLU(),
                        nn.Linear(256, 64),
                    )
                    self.decoder = nn.Sequential(
                        nn.Linear(64, 256),
                        nn.ReLU(),
                        nn.Linear(256, input_dim),
                    )

                def forward(self, x):
                    encoded = self.encoder(x)
                    decoded = self.decoder(encoded)
                    return decoded

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = SimpleAutoencoder().to(device)
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

            # Prepare data
            X = torch.from_numpy(embeddings).float().to(device)
            split = int(0.8 * len(X))
            train_data = TensorDataset(X[:split])
            val_data = TensorDataset(X[split:])

            train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
            val_loader = DataLoader(val_data, batch_size=32)

            # Train
            best_loss = float("inf")
            patience = 5
            patience_counter = 0

            for epoch in range(settings.autoencoder_epochs):
                model.train()
                train_loss = 0
                for batch in train_loader:
                    x = batch[0]
                    optimizer.zero_grad()
                    output = model(x)
                    loss = criterion(output, x)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()

                train_loss /= len(train_loader)

                # Evaluate
                model.eval()
                val_loss = 0
                with torch.no_grad():
                    for batch in val_loader:
                        x = batch[0]
                        output = model(x)
                        loss = criterion(output, x)
                        val_loss += loss.item()

                val_loss /= len(val_loader)

                if val_loss < best_loss:
                    best_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1

                if (epoch + 1) % 10 == 0:
                    logger.info(f"Epoch {epoch+1}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}")

                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

            # Save model
            save_path = Path(save_dir).expanduser()
            save_path.mkdir(parents=True, exist_ok=True)

            model_file = save_path / "autoencoder.pt"
            torch.save(model, model_file)
            logger.info(f"Model saved to {model_file}")

            # Compute and save threshold
            model.eval()
            with torch.no_grad():
                reconstructed = model(X)
                errors = torch.mean((X - reconstructed) ** 2, dim=1).numpy()
                threshold = np.percentile(errors, 95)

            np.save(save_path / "ae_threshold.npy", threshold)
            logger.info(f"Threshold saved: {threshold:.4f}")

            return {
                "model_path": str(model_file),
                "threshold": float(threshold),
                "train_loss": float(train_loss),
                "val_loss": float(best_loss),
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"error": str(e), "model_path": None}
