"""
Replaces: Amazon Nova 2 Lite (paid Bedrock LLM)
With: Mistral 7B running locally via Ollama
Cost: FREE — runs on your own machine/server
Setup: Install Ollama, run: ollama pull mistral
"""

from __future__ import annotations
import logging
import httpx
import json
from dataclasses import dataclass
from src.config import settings

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = """You are an expert SRE (Site Reliability Engineer).
Analyze these anomalous log lines and provide a structured root cause analysis.

ANOMALOUS LOG LINES:
{log_section}

Respond in this exact JSON format:
{{
  "severity": "INFO|WARNING|HIGH|CRITICAL",
  "root_cause": "One sentence describing the most likely root cause",
  "affected_components": ["component1", "component2"],
  "evidence": ["key log line 1", "key log line 2"],
  "next_steps": ["step 1", "step 2", "step 3"],
  "confidence": 0.0
}}

Rules:
- severity must be exactly one of: INFO, WARNING, HIGH, CRITICAL
- confidence is a float 0.0 to 1.0
- next_steps must be concrete and actionable
- Respond ONLY with valid JSON, no other text"""


@dataclass
class TriageReport:
    """Structured root cause analysis report."""
    severity: str
    root_cause: str
    affected_components: list[str]
    evidence: list[str]
    next_steps: list[str]
    confidence: float
    model_used: str
    raw_log_count: int


class LogTriager:
    """
    Performs root cause analysis using a local LLM via Ollama.
    Falls back to rule-based analysis if Ollama is unavailable.
    """

    def __init__(self) -> None:
        self.ollama_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def analyze(
        self,
        log_lines: list[str],
        anomalous_indices: list[int],
    ) -> TriageReport:
        """
        Generate a root cause analysis report.

        Args:
            log_lines: All log lines
            anomalous_indices: Which lines were flagged as anomalous

        Returns:
            TriageReport with severity, root cause, and next steps
        """
        anomalous_lines = [log_lines[i] for i in anomalous_indices]
        log_section = "\n".join(anomalous_lines[:50])

        try:
            report = await self._call_ollama(log_section, len(log_lines))
            return report
        except Exception as e:
            logger.error(f"Ollama call failed: {e} — using rule-based fallback")
            return self._rule_based_fallback(log_lines, anomalous_lines)

    async def _call_ollama(
        self, log_section: str, total_lines: int
    ) -> TriageReport:
        """Call local Ollama Mistral model."""
        prompt = TRIAGE_PROMPT.format(log_section=log_section)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 512,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        raw_text = data.get("response", "")

        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("```")

        parsed = json.loads(clean)

        return TriageReport(
            severity=parsed.get("severity", "WARNING"),
            root_cause=parsed.get("root_cause", "Unknown"),
            affected_components=parsed.get("affected_components", []),
            evidence=parsed.get("evidence", []),
            next_steps=parsed.get("next_steps", []),
            confidence=float(parsed.get("confidence", 0.5)),
            model_used=self.model,
            raw_log_count=total_lines,
        )

    def _rule_based_fallback(
        self, log_lines: list[str], anomalous_lines: list[str]
    ) -> TriageReport:
        """Simple keyword-based fallback when LLM is unavailable."""
        combined = " ".join(anomalous_lines).lower()

        if any(k in combined for k in ["oom", "out of memory", "killed"]):
            severity, cause = "CRITICAL", "Out of memory — process killed by OOM"
        elif any(k in combined for k in ["connection refused", "timeout", "unreachable"]):
            severity, cause = "HIGH", "Network connectivity failure detected"
        elif any(k in combined for k in ["exception", "error", "traceback"]):
            severity, cause = "HIGH", "Unhandled exception in application"
        elif any(k in combined for k in ["warn", "deprecated"]):
            severity, cause = "WARNING", "Non-critical warning detected"
        else:
            severity, cause = "INFO", "Anomalous log pattern detected"

        return TriageReport(
            severity=severity,
            root_cause=cause,
            affected_components=["unknown"],
            evidence=anomalous_lines[:3],
            next_steps=["Review full logs", "Check system metrics", "Escalate if persists"],
            confidence=0.4,
            model_used="rule-based-fallback",
            raw_log_count=len(log_lines),
        )
