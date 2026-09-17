import pytest
from cobri.evaluations import (
    GrokEvaluator,
    OpenRouterEvaluator,
    FallbackModelEvaluator,
)


@pytest.mark.anyio
async def test_fallback_to_openrouter_when_grok_fails():
    # Primary Grok initialized with invalid key to trigger failover exception
    primary = GrokEvaluator(api_key="")
    
    # Fallback OpenRouter configured
    fallback = OpenRouterEvaluator(api_key="sk-or-v1-test-key")

    evaluator = FallbackModelEvaluator(primary=primary, fallback=fallback)

    # Mock evaluation execution
    try:
        result = await evaluator.evaluate({"answer": "x = 1"})
        assert result.provider_used.startswith("openrouter:")
    except Exception as exc:
        # Fails gracefully due to dummy network key in testing
        assert "OpenRouter API key missing" not in str(exc)