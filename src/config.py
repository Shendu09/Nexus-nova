"""Central config — all settings from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Ollama (local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Paths
    models_dir: Path = Path("models")
    logs_dir: Path = Path("logs")

    # Redis
    redis_url: str = "redis://localhost:6379"

    # PostgreSQL
    database_url: str = "postgresql://nexus:nexus@localhost:5432/nexus"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Anomaly detection
    anomaly_threshold: float = 0.75
    lstm_window_size: int = 16
    lstm_stride: int = 4

    # Severity labels
    severity_labels: list[str] = ["INFO", "WARNING", "HIGH", "CRITICAL"]

    # Security
    api_secret_key: str = "change-me-in-production"
    max_log_size_mb: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
