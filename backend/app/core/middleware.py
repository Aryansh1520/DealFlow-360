"""CORS, request logging, and rate-limiting middleware."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.config.settings import settings
from app.core.security import ACCESS_TOKEN, decode_token

logger = logging.getLogger("app.request")

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
                        "data": None,
                    },
                )

        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
