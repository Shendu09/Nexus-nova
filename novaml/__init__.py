"""
novaml — AI-powered log intelligence library.

The simplest AIOps library ever built.
Zero cloud. Zero config. One line.

Usage:
    import novaml

    # Triage logs
    result = novaml.triage(logs)

    # Just detect anomalies
    result = novaml.detect(logs)

    # Explain why something is anomalous
    result = novaml.explain(logs)

    # Forecast future issues
    result = novaml.forecast(metric_df)

    # Train on your own logs (no labels needed)
    novaml.train(logs)
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Shendu09"
__license__ = "Apache-2.0"

# Global default pipeline (lazy initialized)
_default_pipeline: object | None = None


def _get_pipeline():
    """Get or create the default pipeline singleton."""
    global _default_pipeline
    if _default_pipeline is None:
        from novaml._pipeline import Pipeline
        _default_pipeline = Pipeline()
    return _default_pipeline


def triage(
    logs: list[str] | str,
    *,
    model: str = "mistral",
    explain: bool = True,
) -> object:
    """
    Full AI log triage in one line.

    Args:
        logs: List of log lines or a single multiline string.
        model: Local LLM model name (default: mistral via Ollama).
        explain: Whether to include per-line explanations.

    Returns:
        TriageResult with severity, root_cause, next_steps, explanation.

    Example:
        result = novaml.triage(open("app.log").readlines())
        print(result)  # pretty-printed triage report
    """
    if isinstance(logs, str):
        logs = logs.strip().splitlines()
    return _get_pipeline().triage(logs, model=model, explain=explain)


def detect(logs: list[str] | str) -> object:
    """
    Detect anomalous log lines using deep learning.

    Args:
        logs: List of log lines or multiline string.

    Returns:
        AnomalyResult with per-line anomaly scores and flagged indices.

    Example:
        result = novaml.detect(logs)
        for i in result.anomalous_indices:
            print(f"Line {i} is anomalous: {logs[i]}")
    """
    if isinstance(logs, str):
        logs = logs.strip().splitlines()
    return _get_pipeline().detect(logs)


def explain(logs: list[str] | str) -> object:
    """
    Explain WHY specific log lines are anomalous.
    Uses SHAP values + attention visualization.

    Args:
        logs: Log lines to analyze.

    Returns:
        ExplainResult with per-token importance scores.

    Example:
        result = novaml.explain(logs)
        print(result.top_signals)  # ["OOM", "connection refused", ...]
    """
    if isinstance(logs, str):
        logs = logs.strip().splitlines()
    return _get_pipeline().explain(logs)


def forecast(
    metric_series: object,
    *,
    horizon_minutes: int = 60,
) -> object:
    """
    Predict future metric anomalies before they happen.

    Args:
        metric_series: DataFrame with 'ds' (datetime) and 'y' (metric value).
        horizon_minutes: How far ahead to forecast.

    Returns:
        ForecastResult with predicted values and breach probability.

    Example:
        result = novaml.forecast(df, horizon_minutes=30)
        if result.breach_probability > 0.8:
            print(f"Alert at {result.estimated_breach_time}")
    """
    return _get_pipeline().forecast(metric_series, horizon_minutes=horizon_minutes)


def train(
    logs: list[str],
    *,
    save_dir: str = "~/.novaml/models",
) -> dict:
    """
    Train the anomaly detection model on YOUR logs.
    No labels needed — fully unsupervised autoencoder training.

    Args:
        logs: List of log lines (preferably from healthy periods).
        save_dir: Where to save trained model weights.

    Returns:
        Training stats dict (loss, threshold, model_path).

    Example:
        stats = novaml.train(open("normal_logs.txt").readlines())
        print(f"Model saved. Threshold: {stats['threshold']:.4f}")
    """
    return _get_pipeline().train(logs, save_dir=save_dir)


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Start the NovAI REST API server.

    Example:
        novaml.serve()  # → http://localhost:8000
    """
    from novaml.server import start_server
    start_server(host=host, port=port)
