"""LLM integration via Ollama for root cause analysis."""

from __future__ import annotations
import asyncio
import json
import logging
import httpx
from novaml._config import settings
from novaml._models import TriageReport, Severity

logger = logging.getLogger(__name__)

# Pre-defined fallback rules
FALLBACK_KEYWORDS = {
    "oom": ("out of memory", Severity.CRITICAL, 0.7),
    "killed": ("process killed", Severity.CRITICAL, 0.7),
    "connection refused": ("network failure", Severity.HIGH, 0.65),
    "connection reset": ("network failure", Severity.HIGH, 0.65),
    "timeout": ("timeout", Severity.HIGH, 0.65),
    "exception": ("unhandled exception", Severity.HIGH, 0.65),
    "traceback": ("python exception", Severity.HIGH, 0.65),
    "segfault": ("segmentation fault", Severity.CRITICAL, 0.7),
    "panic": ("system panic", Severity.CRITICAL, 0.7),
    "fatal": ("fatal error", Severity.CRITICAL, 0.7),
}


class TriageReport:
    """Root cause analysis report."""

    def __init__(
        self,
        severity: Severity,
        root_cause: str,
        affected_components: list[str],
        evidence: list[str],
        next_steps: list[str],
        confidence: float,
        model_used: str,
    ):
        self.severity = severity
        self.root_cause = root_cause
        self.affected_components = affected_components
        self.evidence = evidence
        self.next_steps = next_steps
        self.confidence = confidence
        self.model_used = model_used


class LogTriager:
    """Async triager using Ollama LLM with fallbacks."""

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self._warmup()

    def _warmup(self) -> None:
        """Ping Ollama on init to verify connectivity."""
        try:
            import httpx
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    logger.info(f"Ollama is available at {self.base_url}")
                else:
                    logger.warning(f"Ollama returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}. Will use fallback rules.")

    async def analyze(
        self,
        logs: list[str],
        anomalous_indices: list[int],
        model: str = "mistral",
    ) -> TriageReport:
        """
        Analyze logs to produce root cause analysis.

        Args:
            logs: All log lines
            anomalous_indices: Indices of anomalous lines
            model: Model name to use

        Returns:
            TriageReport with severity, root_cause, next_steps, etc
        """
        # Extract context
        anomalous_text = "\n".join(logs[i] for i in anomalous_indices[:50]) if anomalous_indices else (logs[0] if logs else "")

        # Try LLM
        try:
            report = await self._call_ollama(anomalous_text, model)
            if report:
                logger.info(f"LLM triage succeeded: {report.severity}")
                return report
        except Exception as e:
            logger.warning(f"LLM triage failed: {e}, using fallback rules")

        # Fallback to rules
        return self._rule_based_triage(anomalous_text)

    async def _call_ollama(self, text: str, model: str) -> TriageReport | None:
        """Call Ollama API for triage."""
        prompt = f"""Analyze this error log and provide a JSON response with these exact fields:
{{
  "severity": "CRITICAL|HIGH|WARNING|INFO",
  "root_cause": "short description",
  "affected_components": ["component1", "component2"],
  "evidence": ["evidence1", "evidence2"],
  "next_steps": ["step1", "step2"],
  "confidence": 0.0-1.0
}}

Log text:
{text}

Respond ONLY with valid JSON, no markdown, no extra text."""

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "temperature": 0.1, "stream": False},
                )
                resp.raise_for_status()
                result = resp.json()
                response_text = result.get("response", "").strip()

                # Remove markdown fences if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                data = json.loads(response_text)

                return TriageReport(
                    severity=Severity(data["severity"]),
                    root_cause=data["root_cause"],
                    affected_components=data.get("affected_components", []),
                    evidence=data.get("evidence", []),
                    next_steps=data.get("next_steps", []),
                    confidence=float(data.get("confidence", 0.5)),
                    model_used=model,
                )
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None

    def _rule_based_triage(self, text: str) -> TriageReport:
        """Fallback rule-based triage."""
        text_lower = text.lower()

        # Check keywords
        for keyword, (label, severity, confidence) in FALLBACK_KEYWORDS.items():
            if keyword in text_lower:
                logger.info(f"Matched keyword: {keyword}")
                return TriageReport(
                    severity=severity,
                    root_cause=label,
                    affected_components=[],
                    evidence=[],
                    next_steps=["Investigate the issue", "Check logs for more details"],
                    confidence=confidence,
                    model_used="fallback-rules",
                )

        # Default
        return TriageReport(
            severity=Severity.WARNING,
            root_cause="Unknown error detected",
            affected_components=[],
            evidence=[],
            next_steps=["Review the anomalous logs", "Check system metrics"],
            confidence=0.5,
            model_used="fallback-default",
        )
