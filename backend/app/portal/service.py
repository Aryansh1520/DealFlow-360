"""Customer-portal reads and negotiation actions. `BACKEND_PHASE_3.md` Task 3.

Every read is built from `scoped_query()` (customer-within-tenant filter) and
serialised by the whitelisting `to_portal_quotation_read`. A customer asking for
another customer's quotation id gets a **404**, not a 403 — the endpoint never
confirms the row exists.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Principal
from app.core.enums import EventType, QuoteStatus
from app.core.exceptions import ConflictException, ErrorCode, NotFoundException
from app.core.pagination import PageParams
from app.core.scoping import scoped_query
from app.customers.models import Customer
from app.events.models import QuoteEvent
from app.events.service import record_event
from app.portal.schemas import PortalCommentRequest, PortalCounterRequest, PortalQuotationRead
from app.portal.serialization import to_portal_quotation_read
from app.quotations.models import Quotation
from app.quotations.serialization import compute_quotation
from app.quotations.transitions import transition

_NEGOTIABLE = {QuoteStatus.SENT.value, QuoteStatus.UNDER_NEGOTIATION.value}
_CONFIRMABLE = _NEGOTIABLE | {QuoteStatus.APPROVED.value}
# The customer can comment on / counter a quote that is `sent`, already
# `under_negotiation`, or `approved` (they can still push for a better price
# right up until they confirm). Any of these coming from a non-negotiation
# status flips the quote to `under_negotiation` so the rep picks it back up.
_COUNTERABLE = _NEGOTIABLE | {QuoteStatus.APPROVED.value}
_REOPENS_NEGOTIATION = {QuoteStatus.SENT.value, QuoteStatus.APPROVED.value}

# Statuses a quotation is still purely internal in — the customer should not see
# these in the portal even for their own `customer_id`. Everything else (approved
# onwards, plus pending_* re-entries) is visible: an approved quote is ready for
# the customer to confirm without the rep needing a separate "send" click.
_PORTAL_HIDDEN_STATUSES = {
    QuoteStatus.DRAFT.value,
    QuoteStatus.REJECTED.value,
    QuoteStatus.RETURNED_FOR_REVISION.value,
}


def _load_or_404(db: Session, quotation_id: int, principal: Principal) -> Quotation:
    quotation = db.scalar(
        scoped_query(Quotation, principal)
        .where(Quotation.id == quotation_id)
        .where(Quotation.status.not_in(_PORTAL_HIDDEN_STATUSES))
    )
    if quotation is None:
        raise NotFoundException("Quotation not found")
    return quotation


def list_my_quotations(
    db: Session, principal: Principal, params: PageParams
) -> tuple[list[PortalQuotationRead], int]:
    base = scoped_query(Quotation, principal).where(
        Quotation.status.not_in(_PORTAL_HIDDEN_STATUSES)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(Quotation.updated_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()
    return [to_portal_quotation_read(db, q) for q in rows], total


def get_my_quotation(db: Session, quotation_id: int, principal: Principal) -> PortalQuotationRead:
    quotation = _load_or_404(db, quotation_id, principal)
    _record_first_view(db, quotation, principal.customer)
    return to_portal_quotation_read(db, quotation)


def _record_first_view(db: Session, quotation: Quotation, customer: Customer | None) -> None:
    seen = db.scalar(
        select(QuoteEvent.id).where(
            QuoteEvent.quotation_id == quotation.id,
            QuoteEvent.event_type == EventType.QUOTE_CUSTOMER_VIEWED.value,
        )
    )
    if seen is not None:
        return
    record_event(
        db,
        quotation,
        EventType.QUOTE_CUSTOMER_VIEWED,
        customer,
        summary=f"{quotation.customer.name} opened this quotation.",
        payload={},
    )
    db.commit()


def add_comment(
    db: Session, quotation_id: int, principal: Principal, payload: PortalCommentRequest
) -> PortalQuotationRead:
    quotation = _load_or_404(db, quotation_id, principal)
    if quotation.status not in _COUNTERABLE:
        raise ConflictException(
            "This quotation is not open for comments.", code=ErrorCode.ILLEGAL_TRANSITION
        )
    record_event(
        db,
        quotation,
        EventType.QUOTE_CUSTOMER_COMMENTED,
        principal.customer,
        summary=f"{quotation.customer.name} commented: \"{payload.body[:180]}\"",
        payload={"line_id": payload.line_id, "body": payload.body},
    )
    if quotation.status in _REOPENS_NEGOTIATION:
        transition(
            db,
            quotation,
            QuoteStatus.UNDER_NEGOTIATION.value,
            principal.customer,
            expected_version=quotation.version,
        )
    db.commit()
    db.refresh(quotation)
    return to_portal_quotation_read(db, quotation)


def counter_offer(
    db: Session, quotation_id: int, principal: Principal, payload: PortalCounterRequest
) -> PortalQuotationRead:
    quotation = _load_or_404(db, quotation_id, principal)
    if quotation.status not in _COUNTERABLE:
        raise ConflictException(
            "This quotation is not open for a counter-offer.", code=ErrorCode.ILLEGAL_TRANSITION
        )
    note = (payload.message or "").strip()
    record_event(
        db,
        quotation,
        EventType.QUOTE_CUSTOMER_COUNTERED,
        principal.customer,
        summary=(
            f"{quotation.customer.name} asked for a discount of "
            f"{payload.requested_discount_bps / 100:.1f}%"
            + (" on one line" if payload.line_id else "")
            + "."
            + (f' Note: "{note}"' if note else "")
        ),
        payload={
            "requested_discount_bps": payload.requested_discount_bps,
            "line_id": payload.line_id,
            "message": payload.message,
        },
    )
    if quotation.status in _REOPENS_NEGOTIATION:
        transition(
            db,
            quotation,
            QuoteStatus.UNDER_NEGOTIATION.value,
            principal.customer,
            expected_version=quotation.version,
        )
    db.commit()
    db.refresh(quotation)
    return to_portal_quotation_read(db, quotation)


def confirm(
    db: Session, quotation_id: int, principal: Principal, expected_version: int
) -> tuple[str, bool]:
    """Returns `(status, re_entered_approval)`."""
    quotation = _load_or_404(db, quotation_id, principal)
    if quotation.status not in _CONFIRMABLE:
        raise ConflictException(
            f"This quotation is {quotation.status} and can no longer be confirmed.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )
    if expected_version != quotation.version:
        raise ConflictException(
            "This quotation changed since you loaded it.",
            code=ErrorCode.VERSION_CONFLICT,
            extra={"current_version": quotation.version},
        )

    customer = principal.customer
    record_event(
        db,
        quotation,
        EventType.QUOTE_CUSTOMER_CONFIRMED,
        customer,
        summary=f"{quotation.customer.name} confirmed the quotation on the current terms.",
        payload={},
    )

    # Confirming from `approved` goes straight to `confirmed` **only** if the terms
    # are still exactly what was signed off — `line_hash` (lines + order discount)
    # must match `approved_line_hash`. If a rep has nudged the discount since (even
    # a little, even across several counter-offers), the fingerprint won't match and
    # we fall through to re-run the engine, so the current position can't skip
    # approval just because the status still reads `approved`.
    from app.quotations.service import line_hash

    terms_match_approval = (
        quotation.approved_line_hash is not None
        and line_hash(quotation) == quotation.approved_line_hash
    )
    if quotation.status == QuoteStatus.APPROVED.value and terms_match_approval:
        transition(
            db, quotation, QuoteStatus.CONFIRMED.value, customer, expected_version=quotation.version
        )
        db.commit()
        db.refresh(quotation)
        return quotation.status, False

    computation = compute_quotation(db, quotation)
    if computation.required_approvals:
        # Needs sign-off again → route through the same submission logic. Neither
        # `sent` nor `approved` has a direct edge to `pending_*`, so hop via
        # `under_negotiation` first.
        if quotation.status in (QuoteStatus.SENT.value, QuoteStatus.APPROVED.value):
            transition(
                db,
                quotation,
                QuoteStatus.UNDER_NEGOTIATION.value,
                customer,
                expected_version=quotation.version,
            )
        from app.approvals.service import route_quotation

        route_quotation(db, quotation, customer, expected_version=quotation.version)
        db.commit()
        db.refresh(quotation)
        return quotation.status, True

    transition(db, quotation, QuoteStatus.CONFIRMED.value, customer, expected_version=quotation.version)
    db.commit()
    db.refresh(quotation)
    return quotation.status, False
