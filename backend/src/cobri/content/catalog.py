"""Versioned JSON content catalog with reviewed-package enforcement."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from cobri.content.ports import ItemReference, PackageReference
from cobri.errors import ResourceNotFound


class ContentItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str = Field(min_length=1, max_length=128)
    title: dict[str, str]
    prompt: dict[str, str]
    expected_code: str = Field(min_length=1)
    tests: list[str] = Field(min_length=1)
    evidence_references: list[str] = Field(min_length=1)
    misconception_ids: list[str] = Field(default_factory=list)
    transfer_prompt: dict[str, str]


class ContentPackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_package_id: str
    content_version: str
    topic: str
    review_status: str
    reviewed_by: str | None = None
    items: list[ContentItem] = Field(min_length=1)


class FileContentCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._packages: dict[tuple[str, str], ContentPackage] = {}
        self._load()

    def _load(self) -> None:
        for path in self.root.glob("*/**/package.json"):
            package = ContentPackage.model_validate_json(path.read_text(encoding="utf-8"))
            self._packages[(package.content_package_id, package.content_version)] = package

    async def require_package(
        self, content_package_id: str, content_version: str
    ) -> PackageReference:
        package = self._packages.get((content_package_id, content_version))
        if package is None or package.review_status != "reviewed":
            raise ResourceNotFound
        return PackageReference(
            content_package_id=package.content_package_id,
            content_version=package.content_version,
        )

    async def require_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> ItemReference:
        package = self._packages.get((content_package_id, content_version))
        if package is None or package.review_status != "reviewed":
            raise ResourceNotFound
        if not any(item.item_id == item_id for item in package.items):
            raise ResourceNotFound
        return ItemReference(
            content_package_id=content_package_id,
            content_version=content_version,
            item_id=item_id,
        )

    def get_item(self, content_package_id: str, content_version: str, item_id: str) -> ContentItem:
        package = self._packages.get((content_package_id, content_version))
        if package is None or package.review_status != "reviewed":
            raise ResourceNotFound
        for item in package.items:
            if item.item_id == item_id:
                return item
        raise ResourceNotFound


def write_example_package(path: Path) -> None:
    """Validate a package file without making it selectable at runtime."""
    ContentPackage.model_validate_json(path.read_text(encoding="utf-8"))
