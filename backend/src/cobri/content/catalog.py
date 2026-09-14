"""Versioned JSON content catalog with reviewed-package enforcement."""

import re
import unicodedata
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cobri.content.ports import ItemReference, PackageReference
from cobri.errors import ResourceNotFound


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    en: str = Field(min_length=1)
    ar: str = Field(min_length=1)


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1, max_length=128)
    source_title: str = Field(min_length=1, max_length=200)
    source_url: str = Field(pattern=r"^https://")
    explanation: LocalizedText


class RubricCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str = Field(min_length=1, max_length=128)
    description: LocalizedText


class FollowUpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str = Field(min_length=1, max_length=128)
    prompt: LocalizedText
    expected_code: str = Field(min_length=1)
    tests: list[str] = Field(min_length=1)


class Misconception(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    misconception_id: str = Field(min_length=1, max_length=128)
    detection_criteria: list[str] = Field(min_length=1)
    remediation: LocalizedText
    practice: FollowUpItem


class ContentItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str = Field(min_length=1, max_length=128)
    title: LocalizedText
    prompt: LocalizedText
    expected_code: str = Field(min_length=1)
    tests: list[str] = Field(min_length=1)
    evidence_references: list[str] = Field(min_length=1)
    misconception_ids: list[str] = Field(default_factory=list)
    transfer_prompt: LocalizedText
    evidence: list[EvidenceSource] = Field(default_factory=list)
    rubric: list[RubricCriterion] = Field(default_factory=list)
    misconceptions: list[Misconception] = Field(default_factory=list)
    transfer: FollowUpItem | None = None

    @model_validator(mode="after")
    def references_are_internal(self) -> "ContentItem":
        if self.evidence and {source.evidence_id for source in self.evidence} != set(
            self.evidence_references
        ):
            raise ValueError("evidence references must exactly match included evidence")
        if self.misconceptions and {
            misconception.misconception_id for misconception in self.misconceptions
        } != set(self.misconception_ids):
            raise ValueError("misconception IDs must exactly match misconception definitions")
        return self


class ContentPackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_package_id: str
    content_version: str
    topic: str
    review_status: str
    reviewed_by: str | None = None
    items: list[ContentItem] = Field(min_length=1)


class ResolvedContentItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    title: LocalizedText
    prompt: LocalizedText
    expected_code: str
    tests: list[str]
    evidence_references: list[str]
    misconception_ids: list[str]
    evidence: list[EvidenceSource]
    rubric: list[RubricCriterion]


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
        try:
            self.get_item(content_package_id, content_version, item_id)
        except ResourceNotFound:
            raise ResourceNotFound from None
        return ItemReference(
            content_package_id=content_package_id,
            content_version=content_version,
            item_id=item_id,
        )

    def list_reviewed(self) -> list[ContentPackage]:
        return sorted(
            (package for package in self._packages.values() if package.review_status == "reviewed"),
            key=lambda package: (package.content_package_id, package.content_version),
        )

    def match_topic(self, query: str) -> tuple[ContentPackage | None, list[ContentItem]]:
        """Match a learner topic only against the newest reviewed package versions."""
        query_tokens = _topic_tokens(query)
        if not query_tokens:
            return None, []

        newest: dict[str, ContentPackage] = {}
        for package in self.list_reviewed():
            current = newest.get(package.content_package_id)
            if current is None or _version_key(package.content_version) > _version_key(
                current.content_version
            ):
                newest[package.content_package_id] = package

        best: tuple[int, ContentPackage, list[ContentItem]] | None = None
        for package in newest.values():
            package_tokens = _topic_tokens(package.topic)
            specific_query = query_tokens - _GENERIC_TOPIC_TOKENS
            lesson_scores = [
                len(specific_query & (_lesson_topic_tokens(item) - _GENERIC_TOPIC_TOKENS))
                for item in package.items
            ]
            package_specific = package_tokens - _GENERIC_TOPIC_TOKENS
            specific_overlap = len(specific_query & package_specific)
            lesson_overlap = max(lesson_scores, default=0)
            broad_topic_match = _is_supported_topic_phrase(query_tokens, package_tokens)
            if not broad_topic_match and specific_overlap == 0 and lesson_overlap == 0:
                continue

            score = (3 if broad_topic_match else 0) + specific_overlap + lesson_overlap
            options = (
                package.items
                if broad_topic_match
                else [
                    item
                    for item, lesson_score in zip(package.items, lesson_scores, strict=True)
                    if lesson_score
                ]
            )
            if best is None or score > best[0]:
                best = (score, package, options)

        if best is None:
            return None, []
        return best[1], best[2]

    def get_package(self, content_package_id: str, content_version: str) -> ContentPackage:
        package = self._packages.get((content_package_id, content_version))
        if package is None or package.review_status != "reviewed":
            raise ResourceNotFound
        return package

    def get_lesson(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> ContentItem:
        package = self.get_package(content_package_id, content_version)
        for item in package.items:
            if item.item_id == item_id:
                return item
        raise ResourceNotFound

    def get_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> ResolvedContentItem:
        package = self.get_package(content_package_id, content_version)
        for lesson in package.items:
            if lesson.item_id == item_id:
                return self._resolved(
                    lesson,
                    lesson.item_id,
                    lesson.title,
                    lesson.prompt,
                    lesson.expected_code,
                    lesson.tests,
                    lesson.misconception_ids,
                )
            for misconception in lesson.misconceptions:
                if misconception.practice.item_id == item_id:
                    practice = misconception.practice
                    return self._resolved(
                        lesson,
                        practice.item_id,
                        {"en": "Targeted practice", "ar": "تدريب موجّه"},
                        practice.prompt,
                        practice.expected_code,
                        practice.tests,
                        [misconception.misconception_id],
                    )
            if lesson.transfer is not None and lesson.transfer.item_id == item_id:
                transfer = lesson.transfer
                return self._resolved(
                    lesson,
                    transfer.item_id,
                    {"en": "Transfer challenge", "ar": "تحدي الانتقال"},
                    transfer.prompt,
                    transfer.expected_code,
                    transfer.tests,
                    [],
                )
        raise ResourceNotFound

    def lesson_for_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> ContentItem:
        package = self.get_package(content_package_id, content_version)
        for lesson in package.items:
            follow_up_ids = {
                follow_up_id
                for follow_up_id in [
                    lesson.transfer.item_id if lesson.transfer else None,
                    *(misconception.practice.item_id for misconception in lesson.misconceptions),
                ]
                if follow_up_id is not None
            }
            if item_id == lesson.item_id or item_id in follow_up_ids:
                return lesson
        raise ResourceNotFound

    @staticmethod
    def _resolved(
        lesson: ContentItem,
        item_id: str,
        title: LocalizedText,
        prompt: LocalizedText,
        expected_code: str,
        tests: list[str],
        misconception_ids: list[str],
    ) -> ResolvedContentItem:
        return ResolvedContentItem(
            item_id=item_id,
            title=title,
            prompt=prompt,
            expected_code=expected_code,
            tests=tests,
            evidence_references=lesson.evidence_references,
            misconception_ids=misconception_ids,
            evidence=lesson.evidence,
            rubric=lesson.rubric,
        )


_GENERIC_TOPIC_TOKENS = {
    "python",
    "function",
    "functions",
    "code",
    "coding",
    "programming",
    "بايثون",
    "دالة",
    "دوال",
    "برمجة",
    "كود",
    "a",
    "an",
    "and",
    "about",
    "do",
    "for",
    "how",
    "i",
    "in",
    "of",
    "on",
    "the",
    "to",
    "understand",
    "want",
    "أن",
    "عن",
    "على",
    "في",
    "كيف",
    "ما",
    "من",
    "و",
}

_LESSON_TOPIC_ALIASES = {
    "function-return-value": (
        "return returns returned value values إرجاع ارجاع يعيد عودة قيمة قيم القيمة القيم"
    ),
    "parameters-and-arguments": (
        "parameter parameters argument arguments معامل معاملات وسيط وسائط المعاملات الوسائط"
    ),
    "compose-function-calls": (
        "compose composition nested chaining call calls تركيب استدعاء استدعاءات متداخلة"
    ),
}


def _topic_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\u064b-\u065f\u0670]", "", normalized)
    tokens = set(re.findall(r"[\w]+", normalized, flags=re.UNICODE))
    expanded = set(tokens)
    for token in tokens:
        if token.startswith("ال") and len(token) > 4:
            expanded.discard(token)
            expanded.add(token[2:])
        if token.endswith("s") and len(token) > 4:
            expanded.add(token[:-1])
    return expanded


def _lesson_topic_tokens(item: ContentItem) -> set[str]:
    aliases = _LESSON_TOPIC_ALIASES.get(item.item_id, "")
    return _topic_tokens(
        f"{item.title.en} {item.title.ar} {item.prompt.en} {item.prompt.ar} {aliases}"
    )


def _is_supported_topic_phrase(query_tokens: set[str], package_tokens: set[str]) -> bool:
    generic_overlap = query_tokens & package_tokens & _GENERIC_TOPIC_TOKENS
    return len(generic_overlap) >= 2 or (
        {"python", "function"} <= query_tokens or {"بايثون", "دوال"} <= query_tokens
    )


def _version_key(version: str) -> tuple[int, ...]:
    parts = version.split(".")
    if all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return (0,)
