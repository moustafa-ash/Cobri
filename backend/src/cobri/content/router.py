"""Authenticated learner-safe catalogue endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from cobri.content.contracts import (
    LessonDetail,
    LessonSummary,
    PackageSummary,
    TopicDiscoveryRequest,
    TopicDiscoveryResponse,
)
from cobri.content.ports import ContentCatalog
from cobri.dependencies import get_content_catalog
from cobri.identity.auth import Principal, get_current_principal

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/packages", response_model=list[PackageSummary])
async def list_packages(
    _: Annotated[Principal, Depends(get_current_principal)],
    catalog: Annotated[ContentCatalog, Depends(get_content_catalog)],
) -> list[PackageSummary]:
    return [PackageSummary.from_package(package) for package in catalog.list_reviewed()]


@router.post("/topics/discover", response_model=TopicDiscoveryResponse)
async def discover_topic(
    body: TopicDiscoveryRequest,
    request: Request,
    _: Annotated[Principal, Depends(get_current_principal)],
    catalog: Annotated[ContentCatalog, Depends(get_content_catalog)],
) -> TopicDiscoveryResponse:
    package, items = catalog.match_topic(body.query)
    if package is None:
        retriever = getattr(request.app.state, "semantic_retriever", None)
        if retriever is not None:
            result = await retriever.match(body.query)
            if result is not None:
                package, items = result
    if package is None:
        return TopicDiscoveryResponse(status="unsupported", options=[])
    return TopicDiscoveryResponse(
        status="supported",
        content_package_id=package.content_package_id,
        content_version=package.content_version,
        options=[
            LessonSummary(item_id=item.item_id, title=item.title, prompt=item.prompt)
            for item in items
        ],
    )


@router.get(
    "/packages/{content_package_id}/{content_version}/lessons/{item_id}",
    response_model=LessonDetail,
)
async def get_lesson(
    content_package_id: str,
    content_version: str,
    item_id: str,
    _: Annotated[Principal, Depends(get_current_principal)],
    catalog: Annotated[ContentCatalog, Depends(get_content_catalog)],
) -> LessonDetail:
    return LessonDetail.from_item(catalog.get_lesson(content_package_id, content_version, item_id))
