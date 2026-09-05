"""The event-ledger API used everywhere a quotation mutates.

`record_event` writes the event **and** bumps `quotations.last_activity_at` in the
same transaction — it does not commit; the caller commits once, as part of its own
mutation, so a single DB round-trip covers the whole operation.

Phase 3 hook: this is also where `deal_metrics` gets upserted and the SSE frame gets
published, once those exist. Left as a clearly marked no-op for now so that lands as a
three-line change, not a refactor.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.enums import ActorType, EventType
from app.customers.models import Customer
from app.events.models import QuoteEvent
from app.users.models import User

if TYPE_CHECKING:
    from app.quotations.models import Quotation


def record_event(
    db: Session,
    quotation: "Quotation",
    event_type: EventType | str,
    actor: User | Customer | None,
    *,
    summary: str,
    payload: dict | None = None,
) -> QuoteEvent:
    if isinstance(actor, User):
        actor_type, actor_id, actor_name = ActorType.INTERNAL, actor.id, actor.full_name
    elif isinstance(actor, Customer):
        actor_type, actor_id, actor_name = ActorType.CUSTOMER, actor.id, actor.name
    else:
        actor_type, actor_id, actor_name = ActorType.SYSTEM, None, "System"

    event = QuoteEvent(
        quotation_id=quotation.id,
        event_type=event_type.value if isinstance(event_type, EventType) else event_type,
        actor_type=actor_type.value,
        actor_id=actor_id,
        actor_name=actor_name,
        summary=summary,
        payload=payload or {},
    )
    db.add(event)
    quotation.last_activity_at = datetime.now(timezone.utc)

    # Phase 3: upsert deal_metrics + publish to the SSE bus here.

    return event
