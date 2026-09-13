"""Canonical evaluation, content, and provider-fallback coverage."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from cobri.config import Settings
from cobri.content.catalog import FileContentCatalog
from cobri.errors import ResourceNotFound
from cobri.evaluations.contracts import Evaluation
from cobri.model_gateway.gateway import StructuredModelGateway


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"outcome_verdict":"correct","reasoning_verdict":"sound",'
                            '"diagnostic_status":"supported","evidence_references":[],'
                            '"misconception_id":null}'
                        )
                    }
                }
            ]
        }


class FakeClient:
    calls: list[str] = []
    bodies: list[dict] = []

    def __init__(self, **_: object) -> None:
        pass

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **_: object) -> FakeResponse:
        self.calls.append(url)
        self.bodies.append(_["json"])
        if "groq" in url:
            raise httpx.ConnectError("provider unavailable")
        return FakeResponse()


def test_provider_fallback_returns_validated_canonical_evaluation(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    FakeClient.calls.clear()
    FakeClient.bodies.clear()
    settings = Settings(
        _env_file=None,
        groq_api_key="groq-test",
        openrouter_api_key="openrouter-test",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
    )
    result = asyncio.run(StructuredModelGateway(settings).evaluate("evidence"))
    assert isinstance(result, Evaluation)
    assert FakeClient.calls[-2:] == [
        "https://api.groq.com/openai/v1/chat/completions",
        "https://openrouter.ai/api/v1/chat/completions",
    ]
    schema = FakeClient.bodies[-1]["response_format"]["json_schema"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert FakeClient.bodies[-1]["provider"] == {"require_parameters": True}


def test_content_catalog_rejects_unreviewed_package(tmp_path: Path) -> None:
    package_dir = tmp_path / "draft" / "1.0.0"
    package_dir.mkdir(parents=True)
    source = json.loads(
        (
            Path(__file__).parents[2] / "content-packages/python-functions/1.0.0/package.json"
        ).read_text(encoding="utf-8")
    )
    source.update({"content_package_id": "draft", "review_status": "draft"})
    (package_dir / "package.json").write_text(json.dumps(source), encoding="utf-8")
    catalog = FileContentCatalog(tmp_path)
    with pytest.raises(ResourceNotFound):
        asyncio.run(catalog.require_package("draft", "1.0.0"))


def test_approved_day2_content_is_valid_and_selectable() -> None:
    root = Path(__file__).parents[2] / "content-packages"
    catalog = FileContentCatalog(root)
    selected = asyncio.run(catalog.require_package("python-functions", "2.0.0"))
    assert selected.content_version == "2.0.0"
    package = catalog._packages[("python-functions", "2.0.0")]
    assert package.review_status == "reviewed"
    assert len(package.items) == 3
    assert all(item.evidence and item.rubric and item.transfer for item in package.items)
