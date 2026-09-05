"""Request-scoped context: the `X-Request-ID`, readable from anywhere in the call
stack (exception handlers included) without threading it through every signature."""

from contextvars import ContextVar

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()
