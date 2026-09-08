"""HTTP-safe integration errors; never turn infrastructure failures into verdicts."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError


class ApplicationError(Exception):
    status_code = 500
    code = "integration_error"
    message = "An integration failed. No learner verdict was produced."


class DependencyUnavailable(ApplicationError):
    status_code = 503
    code = "dependency_unavailable"
    message = "A required service is unavailable. Retry later."


class ResourceNotFound(ApplicationError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class IdempotencyConflict(ApplicationError):
    status_code = 409
    code = "idempotency_conflict"
    message = "This idempotency key was already used for a different submission."


class IntegrationContractError(ApplicationError):
    code = "invalid_dependency_response"
    message = "A service returned an invalid response. No learner verdict was produced."


def validate_result[T: BaseModel](model: type[T], value: Any) -> T:
    """Validate adapters as well as HTTP input, including preconstructed models."""
    try:
        return model.model_validate(value)
    except ValidationError as exc:
        raise IntegrationContractError from exc


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
        )
