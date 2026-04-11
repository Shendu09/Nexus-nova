"""Pipeline orchestrator — wires all modules together."""

from __future__ import annotations
import time
import logging
import asyncio
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Lazy-loads all modules on first use.
    Handles fallbacks between every layer.
    """

    def __init__(self) -> None:
        self._embedder: Optional[Any] = None
        self._analyzer: Optional[Any] = None
        self._triager: Optional[Any] = None
        self._classifier: Optional[Any] = None
        self._explainer: Optional[Any] = None
        self._forecaster: Optional[Any] = None

    # ── lazy loaders ──────────────────────────────────────────

    @property
    def embedder(self) -> Any:
        if self._embedder is None:
            from novaml._embedder import LogEmbedder
            self._embedder = LogEmbedder()
        return self._embedder

    @property
    def analyzer(self) -> Any:
        if self._analyzer is None:
            from novaml._analyzer import AnomalyDetector
            self._analyzer = AnomalyDetector()
        return self._analyzer

    @property
    def triager(self) -> Any:
        if self._triager is None:
            from novaml._triage import LogTriager
            self._triager = LogTriager()
        return self._triager

    @property
    def classifier(self) -> Any:
        if self._classifier is None:
            from novaml._classifier import SeverityClassifier
            self._classifier = SeverityClassifier()
        return self._classifier

    @property
    def explainer(self) -> Any:
        if self._explainer is None:
            from novaml._explainer import LogExplainer
            self._explainer = LogExplainer()
        return self._explainer

    @property
    def forecaster(self) -> Any:
        if self._forecaster is None:
            from novaml._forecaster import LogForecaster
            self._forecaster = LogForecaster()
        return self._forecaster

    # ── public methods ────────────────────────────────────────

    def triage(
        self, logs: list[str], *, model: str = "mistral", explain: bool = True
    ) -> Any:
        """Full triage pipeline."""
        from novaml._models import TriageResult, Severity

        if not logs:
            return TriageResult(
                severity=Severity.INFO,
                root_cause="No logs provided",
                confidence=0.5,
            )

        start = time.perf_counter()

        try:
            # Step 1: detect anomalies
            anomaly = self.detect(logs)

            # Step 2: classify severity
            anomalous_text = "\n".join(
                logs[i] for i in anomaly.anomalous_indices[:40]
            ) or (logs[0] if logs else "")
            severity_pred = self.classifier.predict(anomalous_text)

            # Step 3: LLM root cause
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            report = loop.run_until_complete(
                self.triager.analyze(logs, anomaly.anomalous_indices, model=model)
            )

            # Step 4: explanation (optional)
            signals: list[str] = []
            if explain and anomaly.anomalous_indices:
                try:
                    exp = self.explain(logs)
                    signals = exp.top_signals
                except Exception as e:
                    logger.warning(f"Explainer failed: {e}")

            # Merge: BERT severity wins if high confidence
            final_severity = (
                severity_pred.label
                if severity_pred.confidence > 0.82
                else report.severity
            )

            elapsed = (time.perf_counter() - start) * 1000
            return TriageResult(
                severity=final_severity,
                root_cause=report.root_cause,
                affected_components=report.affected_components,
                evidence=report.evidence,
                next_steps=report.next_steps,
                confidence=max(severity_pred.confidence, report.confidence),
                anomalous_line_count=len(anomaly.anomalous_indices),
                total_line_count=len(logs),
                top_signals=signals,
                anomaly_scores=anomaly.scores,
                model_used=report.model_used,
                processing_ms=elapsed,
            )
        except Exception as e:
            logger.error(f"Triage pipeline failed: {e}")
            raise

    def detect(self, logs: list[str]) -> Any:
        """Detect anomalies in logs."""
        return self.analyzer.detect(logs)

    def explain(self, logs: list[str]) -> Any:
        """Explain why logs are anomalous."""
        return self.explainer.explain(logs)

    def forecast(self, metric_df: Any, horizon_minutes: int) -> Any:
        """Forecast future anomalies."""
        return self.forecaster.forecast(metric_df, horizon_minutes)

    def train(self, logs: list[str], save_dir: str) -> dict:
        """Train anomaly detector."""
        return self.analyzer.train_autoencoder(logs, save_dir=save_dir)
