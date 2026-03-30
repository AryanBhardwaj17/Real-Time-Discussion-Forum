"""FastAPI exception handlers — register on each microservice app."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from shared.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from shared.logging import get_logger

logger = get_logger(__name__)


def _error_response(status_code: int, detail: str, request_id: str | None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "request_id": request_id})


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc.detail, _rid(request))


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc.detail, _rid(request))


async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    return _error_response(status.HTTP_401_UNAUTHORIZED, exc.detail, _rid(request))


async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc.detail, _rid(request))


async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.detail, _rid(request))


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc_info=exc, request_id=_rid(request))
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error", _rid(request))


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to a FastAPI app."""
    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnauthorizedError, unauthorized_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ForbiddenError, forbidden_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_handler)
