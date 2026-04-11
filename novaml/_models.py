"""Pydantic v2 result models — what users get back."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TriageResult(BaseModel):
    """Full triage report returned by novaml.triage()"""

    severity: Severity
    root_cause: str
    affected_components: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    anomalous_line_count: int = 0
    total_line_count: int = 0
    top_signals: list[str] = Field(default_factory=list)
    anomaly_scores: list[float] = Field(default_factory=list)
    model_used: str = "unknown"
    processing_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        """Beautiful terminal output via rich."""
        if not RICH_AVAILABLE:
            return f"TriageResult(severity={self.severity}, confidence={self.confidence:.0%})"

        console = Console()
        color_map = {
            Severity.INFO: "blue",
            Severity.WARNING: "yellow",
            Severity.HIGH: "orange3",
            Severity.CRITICAL: "red",
        }
        color = color_map.get(self.severity, "white")

        with console.capture() as capture:
            console.print(Panel(
                f"[bold {color}]{self.severity.value}[/bold {color}]  "
                f"[dim]confidence: {self.confidence:.0%}[/dim]\n\n"
                f"[bold]Root cause:[/bold] {self.root_cause}\n\n"
                f"[bold]Next steps:[/bold]\n" +
                "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.next_steps)) +
                f"\n\n[dim]Anomalous lines: {self.anomalous_line_count}/{self.total_line_count} "
                f"| {self.processing_ms:.0f}ms | {self.model_used}[/dim]",
                title="[bold]novaml triage report[/bold]",
                border_style=color,
            ))
        return capture.get()

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


class AnomalyResult(BaseModel):
    """Anomaly detection result from novaml.detect()"""

    scores: list[float]
    anomalous_indices: list[int]
    threshold: float
    method: str
    total_lines: int

    def __str__(self) -> str:
        if not RICH_AVAILABLE:
            return (
                f"AnomalyResult(method={self.method}, "
                f"anomalies={len(self.anomalous_indices)}/{self.total_lines})"
            )

        console = Console()
        with console.capture() as capture:
            t = Table(title="Anomaly Detection", box=box.SIMPLE)
            t.add_column("Metric", style="dim")
            t.add_column("Value")
            t.add_row("Total lines", str(self.total_lines))
            t.add_row("Anomalous", f"[red]{len(self.anomalous_indices)}[/red]")
            t.add_row("Method", self.method)
            t.add_row("Threshold", f"{self.threshold:.4f}")
            console.print(t)
        return capture.get()


class ExplainResult(BaseModel):
    """Explanation of why logs are anomalous — from novaml.explain()"""

    top_signals: list[str]
    token_scores: dict[str, float] = Field(default_factory=dict)
    anomalous_patterns: list[str] = Field(default_factory=list)
    normal_baseline: list[str] = Field(default_factory=list)
    explanation_text: str = ""


class ForecastResult(BaseModel):
    """Time-series forecast — from novaml.forecast()"""

    predicted_values: list[float]
    timestamps: list[datetime]
    breach_probability: float = Field(ge=0.0, le=1.0)
    estimated_breach_time: datetime | None = None
    trend: str = "stable"
    model_used: str = "prophet"
