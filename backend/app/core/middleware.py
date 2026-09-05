"""CORS, request logging, request-ID, and rate-limiting middleware."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.config.settings import settings
from app.core.request_context import get_request_id, set_request_id
from app.core.security import ACCESS_TOKEN, decode_token

logger = logging.getLogger("app.request")

SLOW_REQUEST_THRESHOLD_MS = 300

# key -> (window_start_epoch_seconds, request_count). Process-local by design;
# with multiple workers/replicas each counts independently, so the effective
# ceiling scales with process count.
_rate_limit_windows: dict[str, tuple[float, int]] = {}


def _rate_limit_key_allowed(key: str) -> bool:
    now = time.monotonic()
    window_start, count = _rate_limit_windows.get(key, (now, 0))
    if now - window_start >= settings.rate_limit_window_seconds:
        window_start, count = now, 0
    count += 1
    _rate_limit_windows[key] = (window_start, count)
    return count <= settings.rate_limit_requests


def _rate_limit_keys(request: Request) -> list[str]:
    """IP always; account too when a (possibly stale) bearer token is present."""
    client_ip = request.client.host if request.client else "unknown"
    keys = [f"ip:{client_ip}"]

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            payload = decode_token(auth_header[7:], expected_type=ACCESS_TOKEN)
            keys.append(f"account:{payload['user_type']}:{payload['sub']}")
        except Exception:
            pass  # invalid/expired token — the real auth dependency rejects it downstream

    return keys


def register_middleware(app: FastAPI) -> None:
    # Registered before CORSMiddleware: Starlette makes the *last*-added middleware
    # outermost, so CORS must be added last to keep wrapping every response — including
    # the 429s the rate limiter returns early, without which the browser would surface
    # them as a CORS error instead of a readable 429.
    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if not settings.rate_limit_enabled or request.url.path == "/health":
            return await call_next(request)

        for key in _rate_limit_keys(request):
            if not _rate_limit_key_allowed(key):
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "Too many requests. Please try again later.",
                        "data": {"code": None, "request_id": get_request_id()},
                    },
                )

        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        log = logger.warning if duration_ms > SLOW_REQUEST_THRESHOLD_MS else logger.info
        log(
            "%s %s -> %s (%.1fms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            get_request_id(),
        )
        return response

    # Outermost of the three `@app.middleware("http")` handlers (registration order:
    # last-added wraps the others first) — every downstream handler, including the
    # rate limiter and every exception handler, sees the request ID via the contextvar
    # before it runs.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
