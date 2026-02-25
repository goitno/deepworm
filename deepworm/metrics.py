"""Research metrics and telemetry.

Tracks timing, API calls, errors, and resource usage across research sessions.
All data stays local — nothing is sent externally.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metrics:
    """Accumulated research metrics."""

    # Timing
    total_time: float = 0.0
    search_time: float = 0.0
    fetch_time: float = 0.0
    analysis_time: float = 0.0
    synthesis_time: float = 0.0

    # Counts
    api_calls: int = 0
    search_queries: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    sources_analyzed: int = 0
    duplicates_skipped: int = 0

    # Errors
    retries: int = 0
    errors: int = 0
    error_types: dict[str, int] = field(default_factory=dict)

    # Quality
    avg_source_relevance: float = 0.0
    tokens_estimated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_time": round(self.total_time, 2),
            "search_time": round(self.search_time, 2),
            "fetch_time": round(self.fetch_time, 2),
            "analysis_time": round(self.analysis_time, 2),
            "synthesis_time": round(self.synthesis_time, 2),
            "api_calls": self.api_calls,
            "search_queries": self.search_queries,
            "pages_fetched": self.pages_fetched,
            "pages_failed": self.pages_failed,
            "sources_analyzed": self.sources_analyzed,
            "duplicates_skipped": self.duplicates_skipped,
            "retries": self.retries,
            "errors": self.errors,
            "error_types": dict(self.error_types),
            "avg_source_relevance": round(self.avg_source_relevance, 3),
            "tokens_estimated": self.tokens_estimated,
        }

    @property
    def success_rate(self) -> float:
        """Page fetch success rate (0-1)."""
        total = self.pages_fetched + self.pages_failed
        return self.pages_fetched / total if total > 0 else 0.0

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        parts = [
            f"Time: {self.total_time:.1f}s",
            f"API calls: {self.api_calls}",
            f"Queries: {self.search_queries}",
            f"Pages: {self.pages_fetched}/{self.pages_fetched + self.pages_failed}",
            f"Sources: {self.sources_analyzed}",
        ]
        if self.retries > 0:
            parts.append(f"Retries: {self.retries}")
        if self.errors > 0:
            parts.append(f"Errors: {self.errors}")
        return " · ".join(parts)


class MetricsCollector:
    """Collects metrics during research.

    Usage:
        mc = MetricsCollector()
        with mc.time("search"):
            search_results = search(query)
        mc.increment("api_calls")
        metrics = mc.finalize()
    """

    def __init__(self):
        self._metrics = Metrics()
        self._start_time = time.time()
        self._timers: dict[str, float] = {}

    @property
    def metrics(self) -> Metrics:
        return self._metrics

    def increment(self, field: str, count: int = 1) -> None:
        """Increment a counter field."""
        current = getattr(self._metrics, field, 0)
        setattr(self._metrics, field, current + count)

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence."""
        self._metrics.errors += 1
        self._metrics.error_types[error_type] = (
            self._metrics.error_types.get(error_type, 0) + 1
        )

    def time(self, phase: str) -> "_Timer":
        """Context manager for timing a phase."""
        return _Timer(self, phase)

    def finalize(self) -> Metrics:
        """Finalize and return metrics."""
        self._metrics.total_time = time.time() - self._start_time
        return self._metrics


class _Timer:
    """Context manager for timing a phase."""

    def __init__(self, collector: MetricsCollector, phase: str):
        self._collector = collector
        self._phase = phase
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self._start
        field = f"{self._phase}_time"
        if hasattr(self._collector.metrics, field):
            current = getattr(self._collector.metrics, field)
            setattr(self._collector.metrics, field, current + elapsed)
