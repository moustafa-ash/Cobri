"""Composition boundary: absent adapters fail closed; tests override dependencies."""

from fastapi import Request

from Cobri.backend.src.cobri.assessments.contracts import SubmissionService
from Cobri.backend.src.cobri.content.ports import ContentCatalog
from Cobri.backend.src.cobri.core.errors import DependencyUnavailable
from Cobri.backend.src.cobri.tutoring.contracts import SessionStore


def get_session_store(request: Request) -> SessionStore:
    adapter = request.app.state.session_store
    if adapter is None:
        raise DependencyUnavailable
    return adapter


def get_submission_service(request: Request) -> SubmissionService:
    adapter = request.app.state.submission_service
    if adapter is None:
        raise DependencyUnavailable
    return adapter


def get_content_catalog(request: Request) -> ContentCatalog:
    adapter = request.app.state.content_catalog
    if adapter is None:
        raise DependencyUnavailable
    return adapter
