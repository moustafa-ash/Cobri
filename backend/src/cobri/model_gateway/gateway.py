"""Groq-first, OpenRouter-fallback structured evaluation gateway."""

import json
from collections.abc import Awaitable, Callable

import httpx

from cobri.config import Settings
from cobri.evaluations.contracts import Evaluation, EvaluationInput


class ProviderUnavailable(RuntimeError):
    """The provider failed and the job may be retried."""


class StructuredModelGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def evaluate(self, prompt: str) -> Evaluation:
        providers: list[Callable[[str], Awaitable[Evaluation]]] = []
        if self.settings.groq_api_key:
            providers.append(self._groq)
        if self.settings.openrouter_api_key:
            providers.append(self._openrouter)
        if not providers:
            raise ProviderUnavailable("no model provider configured")
        last_error: Exception | None = None
        for provider in providers:
            try:
                return await provider(prompt)
            except (ProviderUnavailable, httpx.HTTPError, ValueError) as exc:
                last_error = exc
        raise ProviderUnavailable(str(last_error or "all providers failed"))

    async def _groq(self, prompt: str) -> Evaluation:
        return await self._request(
            self.settings.groq_base_url,
            self.settings.groq_api_key,
            self.settings.groq_model,
            prompt,
        )

    async def _openrouter(self, prompt: str) -> Evaluation:
        return await self._request(
            self.settings.openrouter_base_url,
            self.settings.openrouter_api_key,
            self.settings.openrouter_model,
            prompt,
        )

    async def _request(
        self, base_url: str, api_key: str | None, model: str, prompt: str
    ) -> Evaluation:
        if not api_key:
            raise ProviderUnavailable("provider key is missing")
        schema = Evaluation.model_json_schema()
        # Groq and OpenRouter strict structured outputs require every property
        # to be listed in ``required``. Optionality is represented by the
        # property's nullable type, not by omitting it from the response.
        schema["required"] = list(schema.get("properties", {}))
        body = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Evaluate the learner response using only the supplied evidence. "
                        "Return the requested JSON schema. Use uncertain diagnostic status "
                        "when the evidence does not support a misconception."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "cobri_evaluation",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        if "openrouter.ai" in base_url:
            body["provider"] = {"require_parameters": True}
        try:
            async with httpx.AsyncClient(timeout=self.settings.model_timeout_seconds) as client:
                response = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                return Evaluation.model_validate(json.loads(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable("provider response was unavailable or invalid") from exc


def evaluation_prompt(input_data: EvaluationInput, evidence: str) -> str:
    return json.dumps(
        {
            "submission": input_data.model_dump(mode="json"),
            "evidence": evidence,
        },
        ensure_ascii=False,
    )
