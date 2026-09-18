"""Small process-local counters for local operations and adapter instrumentation."""

from collections import Counter
from threading import Lock


class OperationalMetrics:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1

    def record_evaluation(
        self,
        provider: str,
        model: str,
        latency_ms: int,
        *,
        fallback: bool,
        failure_category: str | None = None,
    ) -> None:
        """Record aggregate provenance without prompts, answers, tokens, or responses."""
        self.increment(f"provider.{provider}.model.{model}.evaluations")
        self.increment(f"provider.{provider}.latency_bucket.{latency_ms // 100}00ms")
        if fallback:
            self.increment("provider.fallback")
        if failure_category:
            self.increment(f"provider.{provider}.failure.{failure_category}")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(sorted(self._counts.items()))
