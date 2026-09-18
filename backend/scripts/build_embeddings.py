"""Build an exact-cosine JSON index for one active, immutable package."""

import argparse
import asyncio
import hashlib
from pathlib import Path

from cobri.content.catalog import FileContentCatalog
from cobri.content.lifecycle import active_digests
from cobri.content.retrieval import LocalE5Embedder, VectorRecord, save_index


async def build(root: Path, package_id: str, version: str, revision: str, output: Path) -> None:
    package_path = root / package_id / version / "package.json"
    digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if active_digests(root).get((package_id, version)) != digest:
        raise ValueError("package is not active at the requested immutable digest")
    package = FileContentCatalog(root).get_package(package_id, version)
    embedder = LocalE5Embedder("intfloat/multilingual-e5-small", revision, 384)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("content-packages"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(build(args.root, args.package, args.version, args.revision, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
