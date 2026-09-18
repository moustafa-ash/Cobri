"""Fetch a bounded set of official Python sources into curator-only quarantine."""

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from cobri.config import Settings
from cobri.content.web_sources import fetch_quarantined, search_tavily, store_quarantine
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore


async def run(query: str, output: Path, database_url: str | None = None) -> dict:
    settings = Settings()
    if not settings.tavily_api_key:
        raise ValueError("Tavily is not configured")
    urls = await search_tavily(
        query,
        settings.tavily_api_key,
        timeout=settings.tavily_timeout_seconds,
        max_results=min(settings.tavily_max_results, 3),
    )
    database = Database(database_url) if database_url else None
    if database is not None:
        await database.create_schema()
    try:
        stored = []
        for url in urls[:3]:
            source, text = await fetch_quarantined(
                url,
                datetime.now(UTC).isoformat(),
                timeout=settings.tavily_timeout_seconds,
            )
            store_quarantine(output, source, text)
            if database is not None:
                await DatabaseStore(database).save_quarantined_source(
                    source.url, source.digest, datetime.now(UTC)
                )
            stored.append({"url": source.url, "digest": source.digest})
        return {"search_requests": 1, "results": len(stored), "sources": stored}
    finally:
        if database is not None:
            await database.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--output", type=Path, default=Path(".data/quarantine"))
    parser.add_argument("--database-url")
    args = parser.parse_args()
    print(asyncio.run(run(args.query, args.output, args.database_url)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
