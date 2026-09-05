"""Application exceptions and centralized exception handlers.

Every error response shares one shape: {"success": false, "message": str, "data": ...}
so the frontend can handle all failures without special-casing endpoints.
"""

import logging
from typing import Any

import psycopg.errors as psycopg_errors
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for expected application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str = "Bad request", data: Any = None):
        self.message = message
        self.data = data
        super().__init__(message)


class BadRequestException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT


class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


def _error_response(status_code: int, message: str, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": data},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return _error_response(exc.status_code, exc.message, exc.data)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in err["loc"] if part != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return _error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, "Validation error.", errors)

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
