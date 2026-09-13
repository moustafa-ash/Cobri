"""Learner-safe content API contracts."""

from pydantic import BaseModel, ConfigDict

from cobri.content.catalog import (
    ContentItem,
    ContentPackage,
    EvidenceSource,
    LocalizedText,
    RubricCriterion,
)


class LessonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    title: LocalizedText
    prompt: LocalizedText


class PackageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_package_id: str
    content_version: str
    topic: str
    lessons: list[LessonSummary]

    @classmethod
    def from_package(cls, package: ContentPackage) -> "PackageSummary":
        return cls(
            content_package_id=package.content_package_id,
            content_version=package.content_version,
            topic=package.topic,
            lessons=[
                LessonSummary(item_id=item.item_id, title=item.title, prompt=item.prompt)
                for item in package.items
            ],
        )


class LessonDetail(LessonSummary):
    evidence: list[EvidenceSource]
    rubric: list[RubricCriterion]

    @classmethod
    def from_item(cls, item: ContentItem) -> "LessonDetail":
        return cls(
            item_id=item.item_id,
            title=item.title,
            prompt=item.prompt,
            evidence=item.evidence,
            rubric=item.rubric,
        )
