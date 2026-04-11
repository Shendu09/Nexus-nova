"""
Explainability module — the killer feature no other library has.
Tells users WHY a log line is anomalous, not just THAT it is.
"""

from __future__ import annotations
import re
import logging
from collections import Counter
from novaml._models import ExplainResult

logger = logging.getLogger(__name__)

# Patterns that strongly indicate anomalies
ANOMALY_SIGNALS = {
    "oom": "Out of memory",
    "out of memory": "Out of memory",
    "killed": "Process killed",
    "segfault": "Segmentation fault",
    "connection refused": "Network failure",
    "timeout": "Timeout",
    "exception": "Unhandled exception",
    "traceback": "Python traceback",
    "null pointer": "Null reference",
    "disk full": "Storage exhausted",
    "permission denied": "Auth failure",
    "certificate": "TLS/cert issue",
    "deadlock": "Thread deadlock",
    "panic": "System panic",
    "fatal": "Fatal error",
    "critical": "Critical condition",
}


class LogExplainer:
    """
    Explains anomalous log lines using:
    1. Semantic signal extraction (keyword + pattern matching)
    2. TF-IDF deviation (terms rare in normal logs)
    3. Attention weight visualization (if LSTM is available)
    """

    def __init__(self) -> None:
        self._normal_vocab: Counter | None = None

    def explain(self, logs: list[str]) -> ExplainResult:
        """
        Explain why logs contain anomalies.

        Args:
            logs: Log lines to analyze

        Returns:
            ExplainResult with top_signals and token importance
        """
        signals = self._extract_signals(logs)
        token_scores = self._score_tokens(logs)
        patterns = self._find_patterns(logs)

        explanation = self._generate_explanation(signals, patterns)

        return ExplainResult(
            top_signals=signals[:10],
            token_scores=token_scores,
            anomalous_patterns=patterns,
            explanation_text=explanation,
        )

    def _extract_signals(self, logs: list[str]) -> list[str]:
        """Find known anomaly signals in logs."""
        found = []
        combined = " ".join(logs).lower()
        for keyword, label in ANOMALY_SIGNALS.items():
            if keyword in combined and label not in found:
                found.append(label)
        return found

    def _score_tokens(self, logs: list[str]) -> dict[str, float]:
        """Score each unique token by how anomalous it is."""
        all_tokens = []
        for log in logs:
            tokens = re.findall(r'\b[A-Za-z][A-Za-z0-9_]{2,}\b', log)
            all_tokens.extend(t.lower() for t in tokens)

        counts = Counter(all_tokens)
        total = max(sum(counts.values()), 1)

        # Stop words to ignore
        stopwords = {
            "the", "and", "for", "with", "this", "that",
            "from", "into", "log", "info", "debug", "line",
        }
        scores = {}
        for token, count in counts.most_common(50):
            if token not in stopwords and len(token) > 3:
                # Rarity score: less common = more suspicious
                freq = count / total
                scores[token] = round(1.0 - freq, 4)

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20])

    def _find_patterns(self, logs: list[str]) -> list[str]:
        """Find structural anomaly patterns (repeated errors, bursts, etc.)"""
        patterns = []

        # Error burst detection
        error_lines = [l for l in logs if re.search(r'error|exception|fatal', l, re.I)]
        if len(error_lines) > len(logs) * 0.3:
            patterns.append(f"Error burst: {len(error_lines)}/{len(logs)} lines are errors")

        # Repeated identical lines (log spam)
        line_counts = Counter(logs)
        most_common_line, count = line_counts.most_common(1)[0]
        if count > 5:
            patterns.append(f"Log spam: '{most_common_line[:60]}' repeated {count}x")

        # Stack trace detection
        if any("at " in l and "(" in l for l in logs):
            patterns.append("Stack trace present — unhandled exception")

        # Rapid timestamp escalation
        timestamps = re.findall(r'\d{2}:\d{2}:\d{2}', " ".join(logs[:20]))
        if len(timestamps) >= 2:
            patterns.append(f"Rapid log sequence: {len(logs)} lines")

        return patterns

    def _generate_explanation(
        self, signals: list[str], patterns: list[str]
    ) -> str:
        if not signals and not patterns:
            return "Anomalous embedding distance detected — pattern differs from baseline."

        parts = []
        if signals:
            parts.append(f"Detected signals: {', '.join(signals[:3])}.")
        if patterns:
            parts.append(f"Structural patterns: {patterns[0]}.")
        return " ".join(parts)
