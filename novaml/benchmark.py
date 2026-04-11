"""Benchmarking utilities for novaml."""

import time
import novaml
from novaml._models import Severity


def benchmark_triage(logs: list[str], num_runs: int = 3) -> dict:
    """Benchmark triage performance."""
    times = []

    for _ in range(num_runs):
        start = time.perf_counter()
        result = novaml.triage(logs)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return {
        "num_runs": num_runs,
        "num_logs": len(logs),
        "mean_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
    }


def benchmark_detect(logs: list[str], num_runs: int = 3) -> dict:
    """Benchmark anomaly detection."""
    times = []

    for _ in range(num_runs):
        start = time.perf_counter()
        result = novaml.detect(logs)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return {
        "method": result.method,
        "mean_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
    }


if __name__ == "__main__":
    logs = ["ERROR: test"] * 100
    print("Triage benchmark:", benchmark_triage(logs))
    print("Detect benchmark:", benchmark_detect(logs))
