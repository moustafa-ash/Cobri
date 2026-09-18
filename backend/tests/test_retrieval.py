from datetime import UTC, datetime

from cobri.content.retrieval import (
    VectorRecord,
    cosine,
    load_index,
    rank,
    records_from_rows,
    save_index,
)
from cobri.content.web_sources import quarantine, validate_source_url
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore


def test_rank_is_version_and_digest_isolated() -> None:
    records = [
        VectorRecord("a", "digest-1", "model-1", (1.0, 0.0)),
        VectorRecord("b", "digest-1", "model-1", (0.0, 1.0)),
        VectorRecord("old", "digest-old", "model-1", (1.0, 0.0)),
    ]
    assert cosine((1.0, 0.0), (1.0, 0.0)) == 1.0
    assert [record.item_id for _, record in rank((1.0, 0.0), records, "digest-1", "model-1")] == [
        "a",
        "b",
    ]


def test_index_round_trip_preserves_metadata(tmp_path) -> None:
    path = tmp_path / "vectors.json"
    records = [VectorRecord("item", "digest", "revision", (0.25, 0.75))]
    save_index(path, records)
    assert load_index(path) == records


def test_records_from_rows_preserves_database_metadata() -> None:
    class Row:
        item_id = "item"
        package_digest = "digest"
        model_revision = "model"
        vector = [1, 2]

    assert records_from_rows([Row()]) == [VectorRecord("item", "digest", "model", (1.0, 2.0))]


def test_web_sources_are_quarantined_and_host_restricted() -> None:
    source = quarantine("https://docs.python.org/3/library/functions.html", "text", "now")
    assert source.review_status == "quarantined"
    try:
        validate_source_url("https://evil.example/docs")
    except ValueError:
        pass
    else:
        raise AssertionError("untrusted host accepted")


def test_quarantine_metadata_is_idempotently_persisted(tmp_path) -> None:
    import asyncio

    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'sources.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        await store.save_quarantined_source(
            "https://docs.python.org/3/library/functions.html", "d" * 64, datetime.now(UTC)
        )
        await store.save_quarantined_source(
            "https://docs.python.org/3/library/functions.html", "d" * 64, datetime.now(UTC)
        )
        await database.dispose()

    asyncio.run(scenario())


def test_embedding_records_are_filtered_by_digest_and_model(tmp_path) -> None:
    import asyncio

    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'embeddings.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        await store.save_embeddings("pkg", "1.0.0", "digest", "model@1", {"item": [1.0, 0.0]})
        assert len(await store.load_embeddings("pkg", "1.0.0", "digest", "model@1")) == 1
        assert await store.load_embeddings("pkg", "1.0.0", "other", "model@1") == []
        await database.dispose()

    asyncio.run(scenario())
