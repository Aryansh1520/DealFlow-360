"""In-process asyncio pub/sub for the SSE live channel — `BACKEND_PHASE_3.md` Task 2.

`record_event()` (sync, runs in FastAPI's threadpool) calls `publish()`, which hops
onto the main event loop via `call_soon_threadsafe` and fans the frame out to every
queue subscribed to the scope. `GET /events/stream` holds one queue per connection
and formats each frame as an SSE `data:` line.

Frames carry **no sensitive state** — `{id, scope, event_type, quotation_id,
payload, emitted_at}`, where `payload` is a tiny notification dict. The client
refetches through the normal REST endpoint; the live channel therefore cannot leak
anything REST wouldn't return (`FEATURES.md` §5).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)

# Cap the blast radius of a leak / a slow client during the demo.
MAX_QUEUES_PER_SCOPE = 64
MAX_QUEUE_SIZE = 256
HEARTBEAT_SECONDS = 25

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once from the app lifespan so sync worker threads know which loop to
    schedule `publish` onto."""
    global _loop
    _loop = loop


def make_frame(scope: str, event_type: str, quotation_id: int | None, payload: dict | None = None) -> dict:
    return {
        "id": uuid4().hex,
        "scope": scope,
        "event_type": event_type,
        "quotation_id": quotation_id,
        "payload": payload or {},
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    }


def _fanout(scope: str, frame: dict) -> None:
    for queue in list(_subscribers.get(scope, ())):
        try:
            queue.put_nowait(frame)
        except asyncio.QueueFull:
            logger.warning("SSE queue full for scope %s — dropping frame", scope)


def publish(scope: str, frame: dict) -> None:
    """Thread-safe. Safe to call from a sync request handler running in the
    threadpool, or from the event loop itself."""
    loop = _loop
    if loop is None or not loop.is_running():
        # No loop yet (tests, scripts) — nothing is listening, so this is a no-op.
        return
    try:
        loop.call_soon_threadsafe(_fanout, scope, frame)
    except RuntimeError:
        pass


def publish_event(
    *, quotation_id: int, org_id: int, event_type: str, payload: dict | None = None
) -> None:
    """The single call site used by `record_event`: one ledger event lands on up to
    three scopes — the quote's own channel, the org approval queue, the org dashboard."""
    body = payload or {}
    publish(f"quote:{quotation_id}", make_frame(f"quote:{quotation_id}", event_type, quotation_id, body))
    publish(f"org:{org_id}:approvals", make_frame("approvals", event_type, quotation_id, body))
    publish(f"org:{org_id}:dashboard", make_frame("dashboard", event_type, quotation_id, body))


def publish_to_scope(scope: str, event_type: str, quotation_id: int | None, payload: dict | None = None) -> None:
    publish(scope, make_frame(scope, event_type, quotation_id, payload))


async def subscribe(internal_scope: str):
    """Async generator of frames for one connection. Emits a `heartbeat` frame every
    25s of silence. Removes its queue on cancellation (client disconnect)."""
    if len(_subscribers[internal_scope]) >= MAX_QUEUES_PER_SCOPE:
        raise RuntimeError("Too many live subscribers for this scope")

    queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    _subscribers[internal_scope].add(queue)
    try:
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                frame = make_frame(internal_scope, "heartbeat", None, {})
            yield f"data: {json.dumps(frame)}\n\n"
    finally:
        _subscribers[internal_scope].discard(queue)
        if not _subscribers[internal_scope]:
            _subscribers.pop(internal_scope, None)
