"""Redis pub/sub for the SSE live channel — `BACKEND_PHASE_3.md` Task 2.

`record_event()` runs in FastAPI's threadpool. It calls `publish_event(db, ...)`,
which **buffers** the frames on the request's SQLAlchemy session
(`db.info["_sse_frames"]`). The buffer is flushed to Redis by the `after_commit`
hook in `app/db/session.py` — so a rolled-back mutation never emits a frame, and a
frame is only sent once its data is durably committed.

Redis (not an in-process dict) is the bus so a frame published by the worker that
handled a write reaches SSE connections held by *any* of the `uvicorn --workers N`
processes. `GET /events/stream` subscribes one `redis.asyncio` pub/sub per
connection and re-emits each message as an SSE `data:` line.

Frames carry **no sensitive state** — `{id, scope, event_type, quotation_id,
payload, emitted_at}`, where `payload` is a tiny notification dict. The client
refetches through the normal REST endpoint; the live channel therefore cannot leak
anything REST wouldn't return (`FEATURES.md` §5).
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

import redis
from redis import asyncio as aioredis
from sqlalchemy.orm import Session

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Cap concurrent live connections per scope, per worker process.
MAX_QUEUES_PER_SCOPE = 64
HEARTBEAT_SECONDS = 25

_SESSION_BUFFER_KEY = "_sse_frames"

_publish_client: redis.Redis | None = None
_conn_count: dict[str, int] = defaultdict(int)


def _client() -> redis.Redis:
    global _publish_client
    if _publish_client is None:
        _publish_client = redis.Redis.from_url(settings.redis_url)
    return _publish_client


def _channel(scope: str) -> str:
    return f"sse:{scope}"


def make_frame(scope: str, event_type: str, quotation_id: int | None, payload: dict | None = None) -> dict:
    return {
        "id": uuid4().hex,
        "scope": scope,
        "event_type": event_type,
        "quotation_id": quotation_id,
        "payload": payload or {},
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    }


def publish(scope: str, frame: dict) -> None:
    """Push one frame onto the Redis bus immediately. Safe from any thread. A
    live-channel hiccup must never break a core mutation, so failures are logged and
    swallowed."""
    try:
        _client().publish(_channel(scope), json.dumps(frame))
    except Exception:
        logger.warning("SSE publish failed for scope %s", scope, exc_info=True)


def publish_event(
    db: Session, *, quotation_id: int, org_id: int, event_type: str, payload: dict | None = None
) -> None:
    """The single call site used by `record_event`: one ledger event lands on up to
    three scopes — the quote's own channel, the org approval queue, the org dashboard.

    Frames are buffered on the session and flushed to Redis after the transaction
    commits (see `app/db/session.py`)."""
    body = payload or {}
    buffer: list[tuple[str, dict]] = db.info.setdefault(_SESSION_BUFFER_KEY, [])
    buffer.append((f"quote:{quotation_id}", make_frame(f"quote:{quotation_id}", event_type, quotation_id, body)))
    buffer.append((f"org:{org_id}:approvals", make_frame("approvals", event_type, quotation_id, body)))
    buffer.append((f"org:{org_id}:dashboard", make_frame("dashboard", event_type, quotation_id, body)))


def flush_session_frames(db: Session) -> None:
    """Called from the session `after_commit` hook — drain the buffer to Redis."""
    buffer: list[tuple[str, dict]] = db.info.pop(_SESSION_BUFFER_KEY, [])
    for scope, frame in buffer:
        publish(scope, frame)


def discard_session_frames(db: Session) -> None:
    """Called from the session rollback hooks — drop un-committed frames."""
    db.info.pop(_SESSION_BUFFER_KEY, None)


def publish_to_scope(scope: str, event_type: str, quotation_id: int | None, payload: dict | None = None) -> None:
    publish(scope, make_frame(scope, event_type, quotation_id, payload))


async def subscribe(internal_scope: str):
    """Async generator of frames for one connection. Emits a `heartbeat` frame every
    25s of silence. Tears down its Redis pub/sub on cancellation (client disconnect)."""
    if _conn_count[internal_scope] >= MAX_QUEUES_PER_SCOPE:
        raise RuntimeError("Too many live subscribers for this scope")

    client = aioredis.Redis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(internal_scope))
    _conn_count[internal_scope] += 1
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=HEARTBEAT_SECONDS)
            if message is None:
                yield f"data: {json.dumps(make_frame(internal_scope, 'heartbeat', None, {}))}\n\n"
                continue
            data = message["data"]
            if isinstance(data, (bytes, bytearray)):
                data = data.decode()
            yield f"data: {data}\n\n"
    finally:
        _conn_count[internal_scope] = max(0, _conn_count[internal_scope] - 1)
        if _conn_count[internal_scope] == 0:
            _conn_count.pop(internal_scope, None)
        try:
            await pubsub.unsubscribe(_channel(internal_scope))
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            logger.debug("SSE pubsub teardown hiccup for scope %s", internal_scope, exc_info=True)
