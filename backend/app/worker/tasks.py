"""Background task actors.

Consumed by the `worker` service (`dramatiq app.worker.tasks`) and enqueued
from anywhere in the API with `<actor>.send(...)`.
"""

import dramatiq

from app.config.logging import get_logger
from app.worker.broker import redis_broker  # noqa: F401 — configures the broker on import

logger = get_logger(__name__)


@dramatiq.actor(max_retries=3)
def ping() -> None:
    """Smoke-test actor confirming the worker is wired up end-to-end."""
    logger.info("pong")
