"""Session endpoints with authenticated identity and replaceable dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from cobri.content.ports import ContentCatalog, PackageReference
from cobri.dependencies import get_content_catalog, get_session_store
from cobri.errors import IntegrationContractError, validate_result
from cobri.identity.auth import Principal, get_current_principal
from cobri.tutoring.contracts import SessionCreate, SessionStore, SessionView

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionView, status_code=201)
async def create_session(
    body: SessionCreate,
    response: Response,
    principal: Annotated[Principal, Depends(get_current_principal)],
    store: Annotated[SessionStore, Depends(get_session_store)],
    catalog: Annotated[ContentCatalog, Depends(get_content_catalog)],
) -> SessionView:
    package = validate_result(
        PackageReference,
        await catalog.require_package(body.content_package_id, body.content_version),
    )
    if (package.content_package_id, package.content_version) != (
        body.content_package_id,
        body.content_version,
    ):
        raise IntegrationContractError
    session = validate_result(SessionView, await store.create_session(principal, body))
    if session.model_dump(include=set(SessionCreate.model_fields)) != body.model_dump():
        raise IntegrationContractError
    response.headers["Location"] = f"/api/v1/sessions/{session.session_id}"
    return session


@router.get("/{session_id}", response_model=SessionView)
async def get_session(
    session_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    store: Annotated[SessionStore, Depends(get_session_store)],
) -> SessionView:
    session = validate_result(SessionView, await store.get_session(principal, session_id))
    if session.session_id != session_id:
        raise IntegrationContractError
    return session
