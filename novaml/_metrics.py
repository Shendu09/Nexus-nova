"""Metrics and monitoring utilities."""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricsCollector:
    """Collect performance metrics from novaml operations."""

    operation: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float | None = None
    memory_mb: float | None = None
    error: str | None = None

    def finalize(self) -> None:
        """Mark operation as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "memory_mb": self.memory_mb,
            "error": self.error,
            "timestamp": datetime.utcnow().isoformat(),
        }


class PerformanceMonitor:
    """Monitor performance across all operations."""

    def __init__(self) -> None:
        self.metrics: list[MetricsCollector] = []

    def record(self, operation: str) -> MetricsCollector:
        """Create a metric collector for an operation."""
        metric = MetricsCollector(operation=operation)
        self.metrics.append(metric)
        return metric

    def average_duration(self, operation: str) -> float:
        """Get average duration for an operation type."""
        matching = [m for m in self.metrics if m.operation == operation and m.duration_ms]
        if not matching:
            return 0.0
        return sum(m.duration_ms for m in matching) / len(matching)


_monitor = PerformanceMonitor()


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor."""
    return _monitor
