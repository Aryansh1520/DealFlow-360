"""The quote status state machine.

**This is the only function in the codebase that writes `quotations.status`.** If a
future change writes `quotation.status = ...` anywhere else, that's a bug — route it
through `transition()` instead.
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.enums import QUOTE_TRANSITIONS, EventType
from app.core.exceptions import ConflictException, ErrorCode
from app.customers.models import Customer
from app.events.service import record_event
from app.users.models import User

if TYPE_CHECKING:
    from app.quotations.models import Quotation

_TRANSITION_EVENT: dict[str, EventType] = {
    "pending_l1": EventType.QUOTE_SUBMITTED,
    "pending_l2": EventType.QUOTE_SUBMITTED,
    "approved": EventType.QUOTE_APPROVED,
    "rejected": EventType.QUOTE_REJECTED,
    "returned_for_revision": EventType.QUOTE_RETURNED,
    "sent": EventType.QUOTE_SENT,
    "cancelled": EventType.QUOTE_CANCELLED,
}


def transition(
    db: Session,
    quotation: "Quotation",
    to_status: str,
    actor: User | Customer | None,
    *,
    expected_version: int,
    reason: str | None = None,
    force: bool = False,
) -> "Quotation":
    """Order of checks — do not reorder:

    1. `expected_version == quotation.version`, else `409 VERSION_CONFLICT`
    2. `to_status in QUOTE_TRANSITIONS[quotation.status]`, else `409 ILLEGAL_TRANSITION`
       (`force=True` skips this — reserved for the golden-rule re-route in
       `app/approvals/service.py`, which is a system-driven consequence of a line edit,
       not a user-chosen transition, and so isn't bound by the user-facing table)
    3+4. Permission and transition-specific guards are the caller's responsibility —
       every caller already sits behind `quotations:write` / `approvals:l1` /
       `approvals:l2`, and Phase 2 has no transition-specific guard to enforce
       (Phase 3's "confirmed requires a fulfilment plan" is the first one).
    5. Mutate status, bump `version`, record the event.

    Does not commit — callers commit once, as part of their own transaction.
    """
    if expected_version != quotation.version:
        from app.quotations.serialization import to_quotation_read  # local: avoids a cycle

        raise ConflictException(
            "This quotation changed since you loaded it.",
            code=ErrorCode.VERSION_CONFLICT,
            extra={
                "current_version": quotation.version,
                "current": to_quotation_read(db, quotation).model_dump(mode="json"),
            },
        )

    if not force and to_status not in QUOTE_TRANSITIONS.get(quotation.status, []):
        raise ConflictException(
            f"Cannot move a quotation from '{quotation.status}' to '{to_status}'.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )

    from_status = quotation.status
    quotation.status = to_status
    quotation.version += 1

    event_type = _TRANSITION_EVENT.get(to_status, EventType.QUOTE_SUBMITTED)
    actor_label = actor.full_name if isinstance(actor, User) else (actor.name if isinstance(actor, Customer) else "System")
    summary = f"{actor_label} moved this quotation from {from_status} to {to_status}."
    if reason:
        summary += f' Reason: "{reason}"'

    record_event(
        db,
        quotation,
        event_type,
        actor,
        summary=summary,
        payload={"from_status": from_status, "to_status": to_status, "reason": reason},
    )

    return quotation
