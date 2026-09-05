"""The portal serialiser **whitelists** every field it emits. Never build a portal
shape by dropping keys from an internal one — a blacklist leaks the next field
someone adds. `BACKEND_PHASE_3.md` Task 3 / `API_CONTRACT.md` §4.9.

Stripped by construction: `cost_*`, `margin_*`, `risk_score`, `trace`,
`overage_bps`, `ceiling_bps`, and internal-only event types.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import QuoteStatus
from app.events.models import QuoteEvent
from app.portal.schemas import (
    PortalQuotationRead,
    PortalQuoteLine,
    PortalTimelineEntry,
    PortalTotals,
)
from app.quotations.models import Quotation
from app.quotations.serialization import build_quote_line_reads

# Only these ledger event types are ever shown to a customer. Everything else
# (internal edits, approvals routing, fulfilment, upsell, magic-link issuance, …)
# stays invisible.
PORTAL_VISIBLE_EVENT_TYPES = {
    "quote.created",
    "quote.sent",
    "quote.approved",
    "quote.customer_viewed",
    "quote.customer_commented",
    "quote.customer_countered",
    "quote.counter_rejected",
    "quote.customer_confirmed",
    "quote.invoiced",
    "quote.payment_recorded",
}

_NEGOTIABLE = {QuoteStatus.SENT.value, QuoteStatus.UNDER_NEGOTIATION.value}
# A re-approved quote (customer countered → re-routed → approved) is confirmable
# again without a manual re-send.
_CONFIRMABLE = _NEGOTIABLE | {QuoteStatus.APPROVED.value}
# The customer can still open a counter-offer from an `approved` quote — right up
# until they confirm. Keep this in step with `portal.service._COUNTERABLE`.
_COUNTERABLE = _NEGOTIABLE | {QuoteStatus.APPROVED.value}


def _actor_label(event: QuoteEvent, customer_name: str) -> str:
    if event.actor_type == "customer":
        return customer_name
    if event.actor_type == "system":
        return "System"
    return "Sales team"  # never expose an internal rep's name to the portal


def to_portal_quotation_read(db: Session, quotation: Quotation) -> PortalQuotationRead:
    line_reads, computation = build_quote_line_reads(db, quotation)

    lines = [
        PortalQuoteLine(
            id=lr.id,
            product_name=lr.product_name,
            quantity=lr.quantity,
            unit_price_minor=lr.unit_price_minor,
            discount_bps=lr.discount_bps,
            net_minor=lr.net_minor,
            tax_minor=lr.tax_minor,
        )
        for lr in line_reads
    ]

    totals = PortalTotals(
        gross_minor=computation.gross_minor,
        discount_total_minor=computation.discount_total_minor,
        net_minor=computation.net_minor,
        tax_minor=computation.tax_minor,
        total_minor=computation.total_minor,
    )

    events = db.scalars(
        select(QuoteEvent)
        .where(
            QuoteEvent.quotation_id == quotation.id,
            QuoteEvent.event_type.in_(PORTAL_VISIBLE_EVENT_TYPES),
        )
        .order_by(QuoteEvent.created_at.asc())
    ).all()

    # The customer can only confirm a quote the rep has explicitly *sent* — a bare
    # `approved` (e.g. auto-approved and never sent) isn't confirmable, so an SSE
    # blip can't let the customer accept terms they were never actually shown.
    has_been_sent = any(e.event_type == "quote.sent" for e in events)
    timeline = [
        PortalTimelineEntry(
            event_type=e.event_type,
            summary=e.summary,
            created_at=e.created_at.isoformat(),
            actor_label=_actor_label(e, quotation.customer.name),
        )
        for e in events
    ]

    return PortalQuotationRead(
        id=quotation.id,
        reference=quotation.reference,
        status=quotation.status,
        version=quotation.version,
        currency=quotation.currency,
        valid_until=quotation.valid_until.isoformat() if quotation.valid_until else None,
        customer_name=quotation.customer.name,
        lines=lines,
        totals=totals,
        timeline=timeline,
        can_confirm=quotation.status in _CONFIRMABLE and has_been_sent,
        can_counter=quotation.status in _COUNTERABLE,
    )


def quotation_has_been_sent(db: Session, quotation_id: int) -> bool:
    """A `quote.sent` event exists — the rep explicitly pushed the quote to the
    customer at least once."""
    return (
        db.scalar(
            select(QuoteEvent.id).where(
                QuoteEvent.quotation_id == quotation_id,
                QuoteEvent.event_type == "quote.sent",
            )
        )
        is not None
    )
