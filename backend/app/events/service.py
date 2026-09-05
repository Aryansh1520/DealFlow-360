"""The event-ledger API used everywhere a quotation mutates.

`record_event` writes the event **and** bumps `quotations.last_activity_at` in the
same transaction — it does not commit; the caller commits once, as part of its own
mutation, so a single DB round-trip covers the whole operation.

Phase 3: it also upserts the `deal_metrics` read model (same transaction — strongly
consistent, `FEATURES.md` §4) and publishes an SSE `StreamFrame` to the quote /
approvals / dashboard scopes.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.enums import ActorType, EventType
from app.customers.models import Customer
from app.events.models import QuoteEvent
from app.events.stream import publish_event
from app.users.models import User

if TYPE_CHECKING:
    from app.quotations.models import Quotation

logger = logging.getLogger(__name__)


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

    resolved_type = event_type.value if isinstance(event_type, EventType) else event_type

    event = QuoteEvent(
        quotation_id=quotation.id,
        event_type=resolved_type,
        actor_type=actor_type.value,
        actor_id=actor_id,
        actor_name=actor_name,
        summary=summary,
        payload=payload or {},
    )
    db.add(event)
    quotation.last_activity_at = datetime.now(timezone.utc)

    _upsert_deal_metric(db, quotation)

    try:
        publish_event(
            quotation_id=quotation.id,
            org_id=quotation.org_id,
            event_type=resolved_type,
            payload={"reference": quotation.reference, "status": quotation.status},
        )
    except Exception:  # a live-channel hiccup must never break a core mutation
        logger.exception("SSE publish failed for quotation %s", quotation.id)

    return event


def _upsert_deal_metric(db: Session, quotation: "Quotation") -> None:
    """Keep `deal_metrics` in lockstep with the ledger. Best-effort on the derived
    money fields (the engine can raise if config is mid-edit); the row's stage and
    activity timestamp are always current."""
    from app.dashboard.models import DealMetric

    total_minor = margin_bps = risk_score = 0
    try:
        from app.quotations.serialization import compute_quotation

        computation = compute_quotation(db, quotation)
        total_minor = computation.total_minor
        margin_bps = computation.margin_bps
        risk_score = computation.risk_score
    except Exception:
        logger.debug("deal_metrics: computation skipped for quotation %s", quotation.id, exc_info=True)

    metric = db.get(DealMetric, quotation.id)
    now = datetime.now(timezone.utc)
    if metric is None:
        db.add(
            DealMetric(
                quotation_id=quotation.id,
                org_id=quotation.org_id,
                stage=quotation.status,
                owner_rep_id=quotation.owner_rep_id,
                customer_id=quotation.customer_id,
                total_minor=total_minor,
                margin_bps=margin_bps,
                risk_score=risk_score,
                last_activity_at=now,
                days_inactive=0,
                flags=[],
            )
        )
    else:
        metric.stage = quotation.status
        metric.owner_rep_id = quotation.owner_rep_id
        metric.customer_id = quotation.customer_id
        metric.total_minor = total_minor
        metric.margin_bps = margin_bps
        metric.risk_score = risk_score
        metric.last_activity_at = now
        metric.days_inactive = 0
