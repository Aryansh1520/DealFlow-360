"""Idempotency-Key support for `/quotations/*/submit`, `/quotations/*/transition` and
`/approvals/*/act` — see `BACKEND_PHASE_2.md` Task 5 and `API_CONTRACT.md` §6.

Usage inside a guarded endpoint (all three are `async def` so they can `await
request.body()`):

    request_hash = begin_idempotent(db, key=idempotency_key, endpoint="quotations.submit", body=await request.body())
    ... do the work, build `response` ...
    finish_idempotent(db, key=idempotency_key, endpoint="quotations.submit", request_hash=request_hash,
                       status_code=200, response_json=jsonable_encoder(response))
    db.commit()
    return response

A same-key/same-hash replay short-circuits via `IdempotencyReplay`, caught by the
handler registered in `app/core/exceptions.py`, which replays the stored envelope
verbatim and adds `X-Idempotency-Replay: true` — the success envelope has no `code`
slot free to carry `IDEMPOTENCY_REPLAY` in, since that slot holds the replayed
resource itself. See the open question this settles in `API_CONTRACT.md` §1.
"""

import hashlib
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.core.exceptions import ValidationException
from app.db.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (Index("ix_idempotency_keys_created_at", "created_at"),)

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IdempotencyReplay(Exception):
    def __init__(self, status_code: int, response_json: dict):
        self.status_code = status_code
        self.response_json = response_json


def begin_idempotent(db: Session, *, key: str, endpoint: str, body: bytes) -> str:
    """Call before doing any work. Returns the request hash to pass to
    `finish_idempotent`. Raises `IdempotencyReplay` on a same-key/same-hash hit, or a
    `422 VALIDATION_ERROR` on a same-key/different-hash hit."""
    request_hash = hashlib.sha256(body).hexdigest()
    existing = db.get(IdempotencyRecord, key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ValidationException("This Idempotency-Key was already used for a different request.")
        raise IdempotencyReplay(existing.status_code, existing.response_json)
    return request_hash


def finish_idempotent(
    db: Session,
    *,
    key: str,
    endpoint: str,
    request_hash: str,
    status_code: int,
    response_json: dict[str, Any],
) -> None:
    """Call once the response is built, in the same transaction as the mutation
    itself — the caller still owns the final `db.commit()`."""
    db.add(
        IdempotencyRecord(
            key=key,
            endpoint=endpoint,
            request_hash=request_hash,
            response_json=response_json,
            status_code=status_code,
        )
    )
