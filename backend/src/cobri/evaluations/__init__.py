import logging
import httpx
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class EvaluationResult:
    def __init__(self, score: float, feedback: str, provider_used: str):
        self.score = score
        self.feedback = feedback
        self.provider_used = provider_used


class ModelEvaluator(Protocol):
    async def evaluate(self, payload: dict[str, Any]) -> EvaluationResult:
        ...


class GrokEvaluator:
    """
    Primary Provider: xAI Grok API.
    Docs: https://docs.x.ai/api/endpoints/chat
    Endpoint: https://api.x.ai/v1/chat/completions
    """

    def __init__(self, api_key: str, model: str = "grok-2-latest"):#replace model name
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.x.ai/v1/chat/completions"

    async def evaluate(self, payload: dict[str, Any]) -> EvaluationResult:
        if not self.api_key:
            raise RuntimeError("Grok API key missing or unconfigured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": f"Evaluate response: {payload}"}
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            feedback = data["choices"][0]["message"]["content"]

            return EvaluationResult(
                score=1.0,
                feedback=feedback,
                provider_used=f"grok:{self.model}",
            )


class OpenRouterEvaluator:
    """
    Fallback Provider: OpenRouter API.
    Docs: https://openrouter.ai/docs/requests
    Endpoint: https://openrouter.ai/api/v1/chat/completions
    """

    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    async def evaluate(self, payload: dict[str, Any]) -> EvaluationResult:
        if not self.api_key:
            raise RuntimeError("OpenRouter API key missing or unconfigured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://cobri.local",
                    "X-Title": "Cobri Tutor",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": f"Evaluate response: {payload}"}
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            feedback = data["choices"][0]["message"]["content"]

            return EvaluationResult(
                score=1.0,
                feedback=feedback,
                provider_used=f"openrouter:{self.model}",
            )


class FallbackModelEvaluator:
    """
    Attempts primary provider (Grok) first.
    Catches exceptions and routes to fallback provider (OpenRouter).
    """

    def __init__(self, primary: ModelEvaluator, fallback: ModelEvaluator):
        self.primary = primary
        self.fallback = fallback

    async def evaluate(self, payload: dict[str, Any]) -> EvaluationResult:
        try:
            return await self.primary.evaluate(payload)
        except Exception as exc:
            logger.warning(
                "Primary Grok provider failed (%s). Failing over to OpenRouter fallback...",
                exc,
            )
            return await self.fallback.evaluate(payload)
