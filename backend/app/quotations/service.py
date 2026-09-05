"""Quotations CRUD + preview — `BACKEND_PHASE_2.md` Task 4.

Every mutation follows the same shape: check the quotation is editable, check
`expected_version`, compute the *hypothetical* result and reject before writing
anything if it's priced below cost (Hard Gate 1), then mutate, bump `version`, record
an event, run the golden-rule approval revalidation, and commit once.
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ErrorCode, EventType, QuoteStatus
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PageParams
from app.core.tenant_context import require_current_org
from app.customers.models import Customer
from app.events.service import record_event
from app.policies.service import get_active_policy, get_policy_snapshot_by_version
from app.pricing import engine
from app.pricing.service import RawLineInput, build_evaluation_inputs
from app.pricing.service import tax_bps_by_product as load_tax_bps
from app.quotations.models import Quotation, QuoteLine
from app.quotations.schemas import (
    PreviewRequest,
    QuotationCreate,
    QuotationUpdate,
    QuoteComputation,
    QuoteLineCreate,
    QuoteLineUpdate,
)
from app.quotations.serialization import to_quotation_read
from app.users.models import User

_LOCKED_STATUSES = {
    QuoteStatus.CONFIRMED,
    QuoteStatus.FULFILLING,
    QuoteStatus.INVOICED,
    QuoteStatus.PAID,
    QuoteStatus.REJECTED,
    QuoteStatus.CANCELLED,
    QuoteStatus.EXPIRED,
}


def line_hash(quotation: Quotation) -> str:
    """Over `(product_id, variant_id, quantity, discount_bps)`, sorted — the golden
    rule's fingerprint. See `DECISION_ENGINE.md` §8 and `BACKEND_PHASE_2.md` Task 6."""
    items = sorted(
        (line.product_id, line.variant_id or 0, line.quantity, line.discount_bps) for line in quotation.lines
    )
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()


def _ensure_editable(quotation: Quotation) -> None:
    if quotation.status in _LOCKED_STATUSES:
        raise ConflictException(
            f"Quotation '{quotation.reference}' is {quotation.status} and can no longer be edited.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )


def _version_conflict(db: Session, quotation: Quotation) -> ConflictException:
    return ConflictException(
        "This quotation changed since you loaded it.",
        code=ErrorCode.VERSION_CONFLICT,
        extra={
            "current_version": quotation.version,
            "current": to_quotation_read(db, quotation).model_dump(mode="json"),
        },
    )


def _check_version(db: Session, quotation: Quotation, expected_version: int) -> None:
    if expected_version != quotation.version:
        raise _version_conflict(db, quotation)


def evaluate_raw_lines(db: Session, quotation: Quotation, raw_lines: list[RawLineInput], order_discount_bps: int) -> QuoteComputation:
    policy = get_policy_snapshot_by_version(db, quotation.policy_version)
    evaluated = build_evaluation_inputs(db, customer_tier=quotation.customer.tier, raw_lines=raw_lines)
    tax_bps = load_tax_bps(db, {e.product_id for e in evaluated})
    return engine.evaluate(
        evaluated,
        policy,
        quotation.customer.tier,
        order_discount_bps,
        currency=quotation.currency,
        tax_bps_by_product=tax_bps,
    )


def raw_lines_from_saved(quotation: Quotation) -> list[RawLineInput]:
    return [
        RawLineInput(
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            discount_bps=line.discount_bps,
            line_id=line.id,
            added_from_suggestion=line.added_from_suggestion,
        )
        for line in quotation.lines
    ]


def _reject_if_blocked(computation: QuoteComputation) -> None:
    if computation.trace.outcome == "blocked":
        raise ValidationException(
            "This change would price a line below cost.", code=ErrorCode.POLICY_VIOLATION
        )


def _revalidate_approvals(db: Session, quotation: Quotation, actor: User | Customer) -> None:
    from app.approvals.service import revalidate_after_line_change  # local: avoids a service<->service cycle

    revalidate_after_line_change(db, quotation, actor)


def generate_reference(db: Session, quotation: Quotation) -> str:
    return f"QT-{datetime.now(timezone.utc).year}-{quotation.id:06d}"


def list_quotations(
    db: Session,
    *,
    params: PageParams,
    status: str | None,
    owner_rep_id: int | None,
    customer_id: int | None,
    q: str | None,
) -> tuple[list[Quotation], int]:
    stmt = select(Quotation).where(Quotation.org_id == require_current_org(db))
    if status:
        stmt = stmt.where(Quotation.status == status)
    if owner_rep_id:
        stmt = stmt.where(Quotation.owner_rep_id == owner_rep_id)
    if customer_id:
        stmt = stmt.where(Quotation.customer_id == customer_id)
    if q:
        stmt = stmt.where(Quotation.reference.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Quotation.updated_at.desc())
    stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
    items = list(db.scalars(stmt).unique().all())
    return items, total


def get_quotation_or_404(db: Session, quotation_id: int) -> Quotation:
    quotation = db.get(Quotation, quotation_id)
    if quotation is None:
        raise NotFoundException("Quotation not found")
    return quotation


def create_quotation(db: Session, payload: QuotationCreate, owner: User) -> Quotation:
    customer = db.get(Customer, payload.customer_id)
    if customer is None:
        raise NotFoundException("Customer not found")

    policy = get_active_policy(db)
    quotation = Quotation(
        reference="PENDING",
        customer_id=customer.id,
        owner_rep_id=owner.id,
        status=QuoteStatus.DRAFT.value,
        version=1,
        policy_version=policy.version,
        order_discount_bps=0,
        currency="INR",
        valid_until=payload.valid_until,
    )
    db.add(quotation)
    db.flush()
    quotation.reference = generate_reference(db, quotation)

    record_event(
        db,
        quotation,
        EventType.QUOTE_CREATED,
        owner,
        summary=f"{owner.full_name} created this quotation for {customer.name}.",
        payload={"customer_id": customer.id},
    )
    db.commit()
    db.refresh(quotation)
    return quotation


def update_quotation(db: Session, quotation: Quotation, payload: QuotationUpdate, actor: User) -> Quotation:
    _ensure_editable(quotation)
    _check_version(db, quotation, payload.expected_version)

    new_order_discount = (
        payload.order_discount_bps if payload.order_discount_bps is not None else quotation.order_discount_bps
    )
    changes: list[str] = []
    if new_order_discount != quotation.order_discount_bps:
        computation = evaluate_raw_lines(db, quotation, raw_lines_from_saved(quotation), new_order_discount)
        _reject_if_blocked(computation)
        changes.append(f"order discount from {quotation.order_discount_bps / 100:.1f}% to {new_order_discount / 100:.1f}%")
        quotation.order_discount_bps = new_order_discount

    if payload.valid_until is not None and payload.valid_until != quotation.valid_until:
        changes.append(f"valid-until date to {payload.valid_until.isoformat()}")
        quotation.valid_until = payload.valid_until

    if not changes:
        return quotation

    quotation.version += 1
    record_event(
        db,
        quotation,
        EventType.QUOTE_DISCOUNT_CHANGED,
        actor,
        summary=f"{actor.full_name} changed " + " and ".join(changes) + ".",
        payload={"order_discount_bps": quotation.order_discount_bps},
    )
    _revalidate_approvals(db, quotation, actor)
    db.commit()
    db.refresh(quotation)
    return quotation


def add_line(db: Session, quotation: Quotation, payload: QuoteLineCreate, actor: User) -> Quotation:
    _ensure_editable(quotation)
    _check_version(db, quotation, payload.expected_version)

    if payload.quantity <= 0:
        raise ValidationException("Quantity must be positive")

    new_raw = RawLineInput(
        product_id=payload.product_id,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
        discount_bps=payload.discount_bps,
        added_from_suggestion=payload.from_suggestion,
    )
    hypothetical = raw_lines_from_saved(quotation) + [new_raw]
    computation = evaluate_raw_lines(db, quotation, hypothetical, quotation.order_discount_bps)
    _reject_if_blocked(computation)

    # Resolve product/category once more (cheap — one row) to populate the stored
    # QuoteLine columns; the engine already validated the product/variant exist.
    evaluated = build_evaluation_inputs(db, customer_tier=quotation.customer.tier, raw_lines=[new_raw])
    resolved = evaluated[0]

    next_position = (max((line.position for line in quotation.lines), default=-1)) + 1
    line = QuoteLine(
        product_id=resolved.product_id,
        variant_id=resolved.variant_id,
        category_id=resolved.category_id,
        line_type=resolved.line_type,
        subscription_plan_id=resolved.subscription_plan_id,
        quantity=resolved.quantity,
        unit_price_minor=resolved.unit_price_minor,
        cost_price_minor=resolved.cost_price_minor,
        discount_bps=resolved.discount_bps,
        added_from_suggestion=resolved.added_from_suggestion,
        position=next_position,
    )
    # Append via the relationship (not `db.add` + a manual `quotation_id`) so the
    # in-memory `quotation.lines` collection is correct immediately — `line_hash`
    # and the golden-rule revalidation below both read it before this transaction commits.
    quotation.lines.append(line)
    quotation.version += 1

    event_type = EventType.QUOTE_UPSELL_ADDED if resolved.added_from_suggestion else EventType.QUOTE_LINE_ADDED
    record_event(
        db,
        quotation,
        event_type,
        actor,
        summary=f"{actor.full_name} added {resolved.product_name} (qty {resolved.quantity}) to the quotation.",
        payload={"product_id": resolved.product_id, "quantity": resolved.quantity, "discount_bps": resolved.discount_bps},
    )
    _revalidate_approvals(db, quotation, actor)
    db.commit()
    db.refresh(quotation)
    return quotation


def update_line(db: Session, quotation: Quotation, line_id: int, payload: QuoteLineUpdate, actor: User) -> Quotation:
    _ensure_editable(quotation)
    _check_version(db, quotation, payload.expected_version)

    line = next((l for l in quotation.lines if l.id == line_id), None)
    if line is None:
        raise NotFoundException("Line not found on this quotation")

    new_quantity = payload.quantity if payload.quantity is not None else line.quantity
    new_discount_bps = payload.discount_bps if payload.discount_bps is not None else line.discount_bps
    if new_quantity <= 0:
        raise ValidationException("Quantity must be positive")
    if new_quantity == line.quantity and new_discount_bps == line.discount_bps:
        return quotation

    hypothetical = [
        RawLineInput(
            product_id=l.product_id,
            variant_id=l.variant_id,
            quantity=new_quantity if l.id == line_id else l.quantity,
            discount_bps=new_discount_bps if l.id == line_id else l.discount_bps,
            line_id=l.id,
            added_from_suggestion=l.added_from_suggestion,
        )
        for l in quotation.lines
    ]
    computation = evaluate_raw_lines(db, quotation, hypothetical, quotation.order_discount_bps)
    _reject_if_blocked(computation)

    old_quantity, old_discount_bps = line.quantity, line.discount_bps
    line.quantity = new_quantity
    line.discount_bps = new_discount_bps
    quotation.version += 1

    changes = []
    if old_quantity != new_quantity:
        changes.append(f"quantity from {old_quantity} to {new_quantity}")
    if old_discount_bps != new_discount_bps:
        changes.append(f"discount from {old_discount_bps / 100:.1f}% to {new_discount_bps / 100:.1f}%")

    record_event(
        db,
        quotation,
        EventType.QUOTE_LINE_UPDATED,
        actor,
        summary=f"{actor.full_name} changed {line.product.name} " + " and ".join(changes) + ".",
        payload={"line_id": line.id, "quantity": new_quantity, "discount_bps": new_discount_bps},
    )
    _revalidate_approvals(db, quotation, actor)
    db.commit()
    db.refresh(quotation)
    return quotation


def remove_line(db: Session, quotation: Quotation, line_id: int, expected_version: int, actor: User) -> Quotation:
    _ensure_editable(quotation)
    _check_version(db, quotation, expected_version)

    line = next((l for l in quotation.lines if l.id == line_id), None)
    if line is None:
        raise NotFoundException("Line not found on this quotation")

    product_name = line.product.name
    # Remove via the relationship (delete-orphan cascade handles the DELETE at
    # flush) so `quotation.lines` is correct immediately for `line_hash` below.
    quotation.lines.remove(line)
    quotation.version += 1
    record_event(
        db,
        quotation,
        EventType.QUOTE_LINE_REMOVED,
        actor,
        summary=f"{actor.full_name} removed {product_name} from the quotation.",
        payload={"line_id": line_id, "product_id": line.product_id},
    )
    db.flush()
    _revalidate_approvals(db, quotation, actor)
    db.commit()
    db.refresh(quotation)
    return quotation


def preview(db: Session, quotation: Quotation, payload: PreviewRequest) -> QuoteComputation:
    """Dry run — never writes. Mirrors the current, possibly-unsaved, editor state."""
    raw_lines = [
        RawLineInput(
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            discount_bps=line.discount_bps,
        )
        for line in payload.lines
    ]
    return evaluate_raw_lines(db, quotation, raw_lines, payload.order_discount_bps)
