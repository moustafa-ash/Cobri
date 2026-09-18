"""Build an exact-cosine JSON index for one active, immutable package."""

import argparse
import asyncio
import hashlib
from pathlib import Path

from cobri.content.catalog import FileContentCatalog
from cobri.content.lifecycle import active_digests
from cobri.content.retrieval import LocalE5Embedder, VectorRecord, save_index
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore


async def build(
    root: Path,
    package_id: str,
    version: str,
    revision: str,
    output: Path,
    model_path: Path | None = None,
    database_url: str | None = None,
) -> None:
    package_path = root / package_id / version / "package.json"
    digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if active_digests(root).get((package_id, version)) != digest:
        raise ValueError("package is not active at the requested immutable digest")
    package = FileContentCatalog(root).get_package(package_id, version)
    embedder = LocalE5Embedder(
        "intfloat/multilingual-e5-small", revision, 384, model_path=model_path
    )
    records = []
    for item in package.items:
        text = f"{item.title.en}\n{item.title.ar}\n{item.prompt.en}\n{item.prompt.ar}"
        values = await embedder.encode(text, prefix="passage")
        records.append(
            VectorRecord(
                item.item_id,
                digest,
                revision,
                values,
                dimensions=len(values),
                normalized=True,
                tokenizer_revision=revision,
                content_package_id=package_id,
                content_version=version,
            )
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    save_index(output, records)
    if database_url:
        database = Database(database_url)
        await database.create_schema()
        try:
            await DatabaseStore(database).save_embeddings(
                package_id,
                version,
                digest,
                revision,
                {record.item_id: list(record.values) for record in records},
                tokenizer_revision=revision,
                normalized=True,
            )
        finally:
            await database.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("content-packages"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    asyncio.run(
        build(
            args.root,
            args.package,
            args.version,
            args.revision,
            args.output,
            args.model_path,
            args.database_url,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
