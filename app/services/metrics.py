"""
Application metrics collector for monitoring and analytics.
Tracks call counts, latencies, tool usage, and error rates.
Exposes a /metrics endpoint for Prometheus scraping or manual inspection.

This is a lightweight in-process collector; for production, hook into
Prometheus client or Datadog SDK.
"""
import time
from collections import defaultdict
from typing import Optional
from app.logger import logger


class MetricsCollector:
    """Collects and exposes application metrics."""

    def __init__(self):
        # Counters
        self.counters: dict[str, int] = defaultdict(int)
        # Histograms (store individual values for percentile calculation)
        self.histograms: dict[str, list[float]] = defaultdict(list)
        # Gauges (current values)
        self.gauges: dict[str, float] = defaultdict(float)
        self._start_time = time.time()

    # ── Counter operations ──

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self.counters[name] += value

    # ── Histogram operations ──

    def observe(self, name: str, value: float) -> None:
        """Record an observation for a histogram metric (e.g., latency)."""
        self.histograms[name].append(value)
        # Keep only last 1000 observations to bound memory
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]

    # ── Gauge operations ──

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric to a specific value."""
        self.gauges[name] = value

    # ── Timer context manager ──

    class Timer:
        """Context manager for timing operations."""
        def __init__(self, collector: "MetricsCollector", metric_name: str):
            self.collector = collector
            self.metric_name = metric_name
            self.start = None

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            elapsed_ms = (time.time() - self.start) * 1000
            self.collector.observe(self.metric_name, elapsed_ms)

    def timer(self, metric_name: str) -> "Timer":
        """Create a timer context manager for the given metric."""
        return self.Timer(self, metric_name)

    # ── Snapshot ──

    def snapshot(self) -> dict:
        """Return a snapshot of all metrics for the /metrics endpoint."""
        result = {
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {},
        }

        for name, values in self.histograms.items():
            if values:
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                result["histograms"][name] = {
                    "count": n,
                    "min": round(sorted_vals[0], 2),
                    "max": round(sorted_vals[-1], 2),
                    "avg": round(sum(sorted_vals) / n, 2),
                    "p50": round(sorted_vals[n // 2], 2),
                    "p95": round(sorted_vals[int(n * 0.95)], 2) if n >= 20 else None,
                    "p99": round(sorted_vals[int(n * 0.99)], 2) if n >= 100 else None,
                }

        return result


# Global metrics instance
metrics = MetricsCollector()
