"""Deterministic, version-aware cosine retrieval primitives."""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from cobri.errors import ResourceNotFound


@dataclass(frozen=True)
class VectorRecord:
    item_id: str
    package_digest: str
    model_revision: str
    values: tuple[float, ...]
    dimensions: int | None = None
    normalized: bool | None = None
    tokenizer_revision: str | None = None
    content_package_id: str | None = None
    content_version: str | None = None


def save_index(path: Path, records: list[VectorRecord]) -> None:
    rows = []
    for record in records:
        row = {
            "item_id": record.item_id,
            "package_digest": record.package_digest,
            "model_revision": record.model_revision,
            "values": record.values,
        }
        if record.dimensions is not None:
            row["dimensions"] = record.dimensions
        if record.normalized is not None:
            row["normalized"] = record.normalized
        if record.tokenizer_revision is not None:
            row["tokenizer_revision"] = record.tokenizer_revision
        if record.content_package_id is not None:
            row["content_package_id"] = record.content_package_id
        if record.content_version is not None:
            row["content_version"] = record.content_version
        rows.append(row)
    path.write_text(
        json.dumps(rows, separators=(",", ":")),
        encoding="utf-8",
    )


def load_index(path: Path) -> list[VectorRecord]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        VectorRecord(
            item_id=row["item_id"],
            package_digest=row["package_digest"],
            model_revision=row["model_revision"],
            values=tuple(float(value) for value in row["values"]),
            dimensions=row.get("dimensions"),
            normalized=row.get("normalized"),
            tokenizer_revision=row.get("tokenizer_revision"),
            content_package_id=row.get("content_package_id"),
            content_version=row.get("content_version"),
        )
        for row in rows
    ]


def records_from_rows(rows: list[object]) -> list[VectorRecord]:
    return [
        VectorRecord(
            item_id=row.item_id,
            package_digest=row.package_digest,
            model_revision=row.model_revision,
            values=tuple(float(value) for value in row.vector),
            dimensions=getattr(row, "dimensions", None),
            normalized=getattr(row, "normalized", None),
            tokenizer_revision=getattr(row, "tokenizer_revision", None),
            content_package_id=getattr(row, "content_package_id", None),
            content_version=getattr(row, "content_version", None),
        )
        for row in rows
    ]


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("vectors must have equal non-zero dimensions")
    denominator = sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    return (
        sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0
    )


def rank(
    query: tuple[float, ...], records: list[VectorRecord], package_digest: str, model_revision: str
) -> list[tuple[float, VectorRecord]]:
    eligible = [
        record
        for record in records
        if record.package_digest == package_digest and record.model_revision == model_revision
    ]
    return sorted(
        ((cosine(query, record.values), record) for record in eligible),
        reverse=True,
        key=lambda item: (item[0], item[1].item_id),
    )


def validate_metadata(record: VectorRecord, expected_digest: str, expected_model: str) -> None:
    if record.package_digest != expected_digest or record.model_revision != expected_model:
        raise ValueError("embedding metadata does not match requested content/model")


class LocalE5Embedder:
    """Lazy local embedder; absence of the optional runtime fails closed."""

    def __init__(self, model_name: str, revision: str, dimensions: int) -> None:
        if not revision:
            raise ValueError("an immutable embedding model revision is required")
        self.model_name = model_name
        self.revision = revision
        self.dimensions = dimensions
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("sentence-transformers is not installed") from exc
            self._model = SentenceTransformer(
                self.model_name,
                revision=self.revision,
                device="cpu",
                local_files_only=True,
            )
        return self._model

    async def encode(self, text: str, *, prefix: str) -> tuple[float, ...]:
        values = await asyncio.to_thread(self._encode, text, prefix)
        vector = tuple(float(value) for value in values)
        if len(vector) != self.dimensions:
            raise ValueError("embedding dimensions do not match configuration")
        return vector

    def _encode(self, text: str, prefix: str):
        return self._load().encode(
            f"{prefix}: {text}", normalize_embeddings=True, convert_to_numpy=True
        )


class SemanticTopicRetriever:
    """Small in-memory exact search over a validated package index."""

    def __init__(
        self,
        root: Path,
        catalog,
        embedder: LocalE5Embedder,
        records: list[VectorRecord],
        min_score: float,
    ):
        self.root = root
        self.catalog = catalog
        self.embedder = embedder
        self.records = records
        self.min_score = min_score

    async def match(self, query: str):
        try:
            if not self.records or any(
                record.dimensions != self.embedder.dimensions
                or record.normalized is not True
                or record.tokenizer_revision != self.embedder.revision
                for record in self.records
            ):
                return None
            query_vector = await self.embedder.encode(query, prefix="query")
            candidates = []
            for score, record in rank(
                query_vector,
                self.records,
                self.records[0].package_digest if self.records else "",
                self.embedder.revision,
            )[:3]:
                if (
                    score < self.min_score
                    or not record.content_package_id
                    or not record.content_version
                ):
                    continue
                package_path = (
                    self.root / record.content_package_id / record.content_version / "package.json"
                )
                if (
                    not package_path.is_file()
                    or hashlib.sha256(package_path.read_bytes()).hexdigest()
                    != record.package_digest
                ):
                    return None
                candidates.append(
                    self.catalog.get_lesson(
                        record.content_package_id, record.content_version, record.item_id
                    )
                )
            if not candidates:
                return None
            first = self.records[0]
            return (
                self.catalog.get_package(first.content_package_id, first.content_version),
                candidates,
            )
        except (OSError, ResourceNotFound, RuntimeError, ValueError, IndexError):
            return None
