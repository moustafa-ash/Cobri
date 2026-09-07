"""Only the content references consumed by the Day 1 API, pending team review."""

from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field

Reference = Annotated[str, Field(min_length=1, max_length=128, pattern=r"\S")]


class PackageReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    content_package_id: Reference
    content_version: Reference


class ItemReference(PackageReference):
    item_id: Reference


class ContentCatalog(Protocol):
    """Return only selectable content; use ResourceNotFound for unknown references.

    Asser owns review/publication rules and the actual package loader. A draft
    package must not be represented as reviewed learner-ready content.
    """

    async def require_package(
        self, content_package_id: str, content_version: str
    ) -> PackageReference: ...

    async def require_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> ItemReference: ...
