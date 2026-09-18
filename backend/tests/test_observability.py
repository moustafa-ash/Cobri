from cobri.observability import OperationalMetrics


def test_provider_metrics_are_aggregate_and_sanitized() -> None:
    metrics = OperationalMetrics()
    metrics.record_evaluation(
        "groq", "fixed-model", 235, fallback=False, failure_category="timeout"
    )
    snapshot = metrics.snapshot()
    assert snapshot["provider.groq.model.fixed-model.evaluations"] == 1
    assert snapshot["provider.groq.latency_bucket.200ms"] == 1
    assert snapshot["provider.groq.failure.timeout"] == 1
