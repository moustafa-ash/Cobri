"""HTTPS-only official Python source quarantine."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class QuarantinedSource:
    url: str
    retrieved_at: str
    digest: str
    review_status: str = "quarantined"


def validate_source_url(url: str) -> None:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("only https://docs.python.org sources are allowed") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "docs.python.org"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("only https://docs.python.org sources are allowed")


def quarantine(url: str, text: str, retrieved_at: str) -> QuarantinedSource:
    validate_source_url(url)
    return QuarantinedSource(url, retrieved_at, hashlib.sha256(text.encode()).hexdigest())


async def fetch_quarantined(
    url: str, retrieved_at: str, *, timeout: float = 5, max_bytes: int = 1_000_000
) -> tuple[QuarantinedSource, str]:
    validate_source_url(url)
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        current = url
        for _ in range(4):
            async with client.stream("GET", current) as response:
                if response.is_redirect:
                    current = response.headers.get("location", "")
                    validate_source_url(current)
                    continue
                response.raise_for_status()
                if int(response.headers.get("content-length", "0")) > max_bytes:
                    raise ValueError("source exceeds quarantine size limit")
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        raise ValueError("source exceeds quarantine size limit")
                text = bytes(chunks)
                break
        else:
            raise ValueError("source exceeded redirect limit")
    decoded = text.decode("utf-8", errors="replace")
    return quarantine(url, decoded, retrieved_at), decoded


async def search_tavily(
    query: str, api_key: str, *, timeout: float = 5, max_results: int = 3
) -> list[str]:
    if not api_key:
        raise ValueError("Tavily API key is required")
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "query": query,
                "include_domains": ["docs.python.org"],
                "max_results": max_results,
            },
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    urls: list[str] = []
    for result in results[:max_results]:
        url = result.get("url") if isinstance(result, dict) else None
        if not isinstance(url, str):
            continue
        validate_source_url(url)
        urls.append(url)
    return urls


def store_quarantine(path: Path, source: QuarantinedSource, text: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    content_path = path / f"{source.digest}.txt"
    metadata_path = path / f"{source.digest}.json"
    if not content_path.exists():
        content_path.write_text(text, encoding="utf-8")
        metadata_path.write_text(
            json.dumps({**source.__dict__, "stored_at": datetime.now(UTC).isoformat()}, indent=2)
            + "\n",
            encoding="utf-8",
        )
