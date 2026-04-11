"""Settings and configuration management."""

from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """All configuration for novaml from environment variables."""

    # Core paths
    models_dir: str = "~/.novaml/models"
    logs_dir: str = "~/.novaml/logs"

    # Ollama configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Embedding configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Anomaly detection
    anomaly_threshold: float = 0.75
    lstm_window_size: int = 16
    lstm_stride: int = 4
    lstm_hidden_dim: int = 256
    num_lstm_layers: int = 2
    autoencoder_epochs: int = 50
    batch_size: int = 32

    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_secret_key: str = "dev-key-change-in-prod"

    # Classification
    severity_confidence_gate: float = 0.82
    max_log_lines_per_request: int = 10000

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def models_dir_expanded(self) -> Path:
        """Return expanded models directory path."""
        return Path(self.models_dir).expanduser()

    @property
    def logs_dir_expanded(self) -> Path:
        """Return expanded logs directory path."""
        return Path(self.logs_dir).expanduser()


settings = Settings()
