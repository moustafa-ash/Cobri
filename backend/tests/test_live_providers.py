"""Opt-in smoke checks for independently configured model providers."""

import os

import pytest

from cobri.config import Settings
from cobri.model_gateway.gateway import StructuredModelGateway


@pytest.mark.anyio
@pytest.mark.live_provider
async def test_live_groq_only() -> None:
    if os.getenv("COBRI_RUN_LIVE_PROVIDERS") != "1":
        pytest.skip("Set COBRI_RUN_LIVE_PROVIDERS=1 to run provider checks")
    settings = Settings(_env_file=None, openrouter_api_key=None)
    if not settings.groq_api_key:
        pytest.skip("Configure COBRI_GROQ_API_KEY for the Groq-only check")
    result = await StructuredModelGateway(settings).evaluate("Return a canonical evaluation.")
    assert result.outcome_verdict.value in {"correct", "incorrect", "unverified"}


@pytest.mark.anyio
@pytest.mark.live_provider
async def test_live_openrouter_only_requires_fixed_model() -> None:
    if os.getenv("COBRI_RUN_LIVE_PROVIDERS") != "1":
        pytest.skip("Set COBRI_RUN_LIVE_PROVIDERS=1 to run provider checks")
    settings = Settings(_env_file=None, groq_api_key=None)
    if not settings.openrouter_api_key:
        pytest.skip("Configure COBRI_OPENROUTER_API_KEY for the OpenRouter-only check")
    if settings.openrouter_model == "openrouter/free":
        pytest.fail("Set COBRI_OPENROUTER_MODEL to an approved fixed model ID")
    result = await StructuredModelGateway(settings).evaluate("Return a canonical evaluation.")
    assert result.outcome_verdict.value in {"correct", "incorrect", "unverified"}
