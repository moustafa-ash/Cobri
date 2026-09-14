"""Only the content references consumed by the Day 1 API, pending team review."""

from typing import Annotated, Any, Protocol

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
class ContentPackageNotFoundError(Exception):
    """Raised when a package or version is missing or in an unreviewed draft state."""
    def __init__(self, message: str = "Requested content package was not found or is unreviewed."):
        self.message = message
        super().__init__(self.message)
# Inside FileContentCatalog / Package Loader
def get_package(self, package_id: str, version: str):
    package_data = self._load_package_json(package_id, version)
    
    # Enforce locked decision: Draft packages must be explicitly reviewed before publication
    if package_data.get("status") == "draft":
        raise ContentPackageNotFoundError(
            f"Package '{package_id}' version '{version}' is currently in draft state and unreviewed."
        )
        
    return package_data


async def require_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> ItemReference: ...

def list_reviewed(self) -> list[Any]: ...

def match_topic(self, query: str) -> tuple[Any | None, list[Any]]: ...

def get_lesson(self, content_package_id: str, content_version: str, item_id: str) -> Any: ...

def get_item(self, content_package_id: str, content_version: str, item_id: str) -> Any: ...

def lesson_for_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> Any: ...
