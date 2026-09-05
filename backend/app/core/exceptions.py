"""Application exceptions and centralized exception handlers.

Every error response keeps the app's `{success, message, data}` envelope — see
`app/core/responses.py`. Per `API_CONTRACT.md` §1 "Error envelope", `data` additionally
always carries `code` (an `ErrorCode` member, or `null`) and `request_id`, plus whatever
exception-specific `extra` fields a given error needs (e.g. future `current_version` /
`current` on a version conflict). The frontend already reads `body.message`; `code` and
`request_id` are purely additive.
"""

import logging
from typing import Any

import psycopg.errors as psycopg_errors
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.enums import ErrorCode
from app.core.request_context import get_request_id

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for expected application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: ErrorCode | None = None

    def __init__(
        self,
        message: str = "Bad request",
        *,
        code: ErrorCode | None = None,
        extra: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code or type(self).code
        self.extra = extra or {}
        super().__init__(message)


class BadRequestException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.PERMISSION_DENIED


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = ErrorCode.NOT_FOUND


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT


class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ErrorCode.VALIDATION_ERROR


def _error_data(code: ErrorCode | str | None, extra: dict[str, Any] | None = None) -> dict:
    return {
        "code": code.value if isinstance(code, ErrorCode) else code,
        "request_id": get_request_id(),
        **(extra or {}),
    }


def _error_response(
    status_code: int,
    message: str,
    code: ErrorCode | str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": _error_data(code, extra)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    from app.core.idempotency import IdempotencyReplay

    @app.exception_handler(IdempotencyReplay)
    async def idempotency_replay_handler(request: Request, exc: IdempotencyReplay) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.response_json,
            headers={"X-Idempotency-Replay": "true"},
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return _error_response(exc.status_code, exc.message, exc.code, exc.extra)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in err["loc"] if part != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Validation error.",
            ErrorCode.VALIDATION_ERROR,
            {"errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)

        if isinstance(exc.orig, psycopg_errors.UniqueViolation):
            return _error_response(status.HTTP_409_CONFLICT, "This record already exists.")
        if isinstance(exc.orig, psycopg_errors.ForeignKeyViolation):
            return _error_response(
                status.HTTP_400_BAD_REQUEST,
                "This operation conflicts with a related resource.",
            )
        return _error_response(
            status.HTTP_409_CONFLICT, "The operation conflicts with existing data."
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error.")
