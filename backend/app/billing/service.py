"""Billing: subscription schedule generation at confirm, invoice / credit-note
issuance, payments, and supersession. `BACKEND_PHASE_3.md` Task 4.

Every issued document's PDF is rendered here and pushed to MinIO immediately; the
object key is stored on the row and the bytes are only ever served back through
`GET /invoices/{id}/pdf` after that endpoint's ownership check.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import BillingSchedule, Invoice, InvoiceLine, Payment
from app.billing.pdf import render_invoice_pdf
from app.billing.proration import build_periods
from app.billing.schemas import (
    BillingScheduleEntry,
    InvoiceLineRead,
    InvoiceRead,
    SupersedeLine,
)
from app.core.enums import (
    BillingScheduleStatus,
    DocumentType,
    ErrorCode,
    EventType,
    InvoiceStatus,
    QuoteStatus,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.storage import put_object
from app.customers.models import Customer
from app.events.service import record_event
from app.organizations.models import Organization
from app.quotations.models import Quotation, QuoteLine
from app.quotations.serialization import build_quote_line_reads
from app.subscriptions.models import SubscriptionPlan
from app.users.models import User

logger = logging.getLogger(__name__)


# --------------------------------------------------------------- schedule generation


def generate_billing_schedule(db: Session, quotation: Quotation) -> int:
    """Idempotent — the unique `(line_id, period_start)` constraint means a re-run
    inserts nothing. Called as a side effect of a quote reaching `confirmed`."""
    line_reads, _ = build_quote_line_reads(db, quotation)
    reads_by_id = {lr.id: lr for lr in line_reads}
    plans = {
        p.id: p for p in db.scalars(select(SubscriptionPlan)).all()
    }
    start = date.today()
    created = 0

    existing_starts = {
        (row.line_id, row.period_start)
        for row in db.scalars(
            select(BillingSchedule).where(BillingSchedule.quotation_id == quotation.id)
        ).all()
    }

    for line in quotation.lines:
        if line.line_type != "subscription":
            continue
        read = reads_by_id.get(line.id)
        if read is None or read.net_minor <= 0:
            continue
        plan = plans.get(line.subscription_plan_id)
        interval = plan.interval if plan else "monthly"
        billing_cycles = plan.billing_cycles if plan else None
        proration_enabled = plan.proration_enabled if plan else True

        periods = build_periods(
            line_net_minor=read.net_minor,
            start=start,
            interval=interval,
            billing_cycles=billing_cycles,
            proration_enabled=proration_enabled,
        )
        for period in periods:
            if (line.id, period.period_start) in existing_starts:
                continue
            db.add(
                BillingSchedule(
                    quotation_id=quotation.id,
                    line_id=line.id,
                    period_start=period.period_start,
                    period_end=period.period_end,
                    amount_minor=period.amount_minor,
                    is_prorated=period.is_prorated,
                    proration_days=period.proration_days,
                    proration_basis_days=period.proration_basis_days,
                    status=BillingScheduleStatus.SCHEDULED.value,
                )
            )
            created += 1
    return created


def list_billing_schedule(db: Session, quotation: Quotation) -> list[BillingScheduleEntry]:
    rows = db.scalars(
        select(BillingSchedule)
        .where(BillingSchedule.quotation_id == quotation.id)
        .order_by(BillingSchedule.line_id, BillingSchedule.period_start)
    ).all()
    product_names = _product_names_for_lines(db, {r.line_id for r in rows})
    return [
        BillingScheduleEntry(
            id=r.id,
            quotation_id=r.quotation_id,
            line_id=r.line_id,
            product_name=product_names.get(r.line_id, ""),
            period_start=r.period_start,
            period_end=r.period_end,
            amount_minor=r.amount_minor,
            is_prorated=r.is_prorated,
            proration_days=r.proration_days,
            proration_basis_days=r.proration_basis_days,
            status=r.status,
            invoice_id=r.invoice_id,
            currency=quotation.currency,
        )
        for r in rows
    ]


def _product_names_for_lines(db: Session, line_ids: set[int]) -> dict[int, str]:
    if not line_ids:
        return {}
    rows = db.scalars(select(QuoteLine).where(QuoteLine.id.in_(line_ids))).all()
    return {row.id: row.product.name for row in rows}


# ----------------------------------------------------------------- invoice issuance


def _next_number(db: Session, document_type: str) -> str:
    prefix = "CN" if document_type == DocumentType.CREDIT_NOTE.value else "INV"
    year = date.today().year
    count = (
        db.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.document_type == document_type)
        )
        or 0
    )
    return f"{prefix}-{year}-{count + 1:06d}"


def _to_invoice_read(invoice: Invoice) -> InvoiceRead:
    return InvoiceRead(
        id=invoice.id,
        number=invoice.number,
        document_type=invoice.document_type,
        quotation_id=invoice.quotation_id,
        customer_id=invoice.customer_id,
        status=invoice.status,
        issued_at=invoice.issued_at,
        subtotal_minor=invoice.subtotal_minor,
        tax_minor=invoice.tax_minor,
        total_minor=invoice.total_minor,
        paid_minor=invoice.paid_minor,
        balance_minor=invoice.balance_minor,
        currency=invoice.currency,
        supersedes_invoice_id=invoice.supersedes_invoice_id,
        superseded_by_invoice_id=invoice.superseded_by_invoice_id,
        credit_note_id=invoice.credit_note_id,
        lines=[
            InvoiceLineRead(
                description=ln.description,
                quantity=ln.quantity,
                unit_price_minor=ln.unit_price_minor,
                tax_minor=ln.tax_minor,
                amount_minor=ln.amount_minor,
            )
            for ln in invoice.lines
        ],
        is_immutable=invoice.is_immutable,
    )


def _render_and_store_pdf(db: Session, invoice: Invoice) -> None:
    customer = db.get(Customer, invoice.customer_id)
    org = db.get(Organization, invoice.org_id)
    data = render_invoice_pdf(
        invoice,
        customer_name=customer.name if customer else "Customer",
        org_name=org.name if org else "DealFlow360",
    )
    key = f"invoices/{invoice.org_id}/{invoice.number}.pdf"
    try:
        put_object(key, data, content_type="application/pdf")
        invoice.pdf_object_key = key
    except Exception:
        logger.exception("Failed to upload invoice PDF %s to object storage", invoice.number)


def _build_invoice_lines_from_quote(
    db: Session, quotation: Quotation
) -> tuple[list[InvoiceLine], list[BillingSchedule]]:
    """One-time lines invoice in full immediately; due subscription periods
    (`period_start <= today`, still `scheduled`) invoice now and flip to `invoiced`."""
    line_reads, _ = build_quote_line_reads(db, quotation)
    reads_by_id = {lr.id: lr for lr in line_reads}
    today = date.today()
    invoice_lines: list[InvoiceLine] = []

    for line in quotation.lines:
        if line.line_type != "one_time":
            continue
        read = reads_by_id.get(line.id)
        if read is None:
            continue
        invoice_lines.append(
            InvoiceLine(
                description=read.product_name,
                quantity=read.quantity,
                unit_price_minor=read.unit_price_minor,
                tax_minor=read.tax_minor,
                amount_minor=read.net_minor,
            )
        )

    due = db.scalars(
        select(BillingSchedule).where(
            BillingSchedule.quotation_id == quotation.id,
            BillingSchedule.status == BillingScheduleStatus.SCHEDULED.value,
            BillingSchedule.period_start <= today,
        )
    ).all()
    product_names = _product_names_for_lines(db, {d.line_id for d in due})
    consumed: list[BillingSchedule] = []
    for row in due:
        # Tax on a prorated period is scaled by the same ratio as the amount.
        base_read = reads_by_id.get(row.line_id)
        tax = 0
        if base_read and base_read.net_minor:
            tax = base_read.tax_minor * row.amount_minor // base_read.net_minor
        invoice_lines.append(
            InvoiceLine(
                description=(
                    f"{product_names.get(row.line_id, 'Subscription')} "
                    f"({row.period_start.isoformat()} – {row.period_end.isoformat()})"
                ),
                quantity=1,
                unit_price_minor=row.amount_minor,
                tax_minor=tax,
                amount_minor=row.amount_minor,
            )
        )
        consumed.append(row)

    return invoice_lines, consumed


def generate_invoice(db: Session, quotation: Quotation, actor: User) -> Invoice:
    if quotation.status not in (
        QuoteStatus.CONFIRMED.value,
        QuoteStatus.FULFILLING.value,
        QuoteStatus.INVOICED.value,
    ):
        raise ConflictException(
            f"Quotation {quotation.reference} is {quotation.status}; it must be confirmed "
            "before it can be invoiced.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )

    lines, consumed_schedule = _build_invoice_lines_from_quote(db, quotation)
    if not lines:
        raise ValidationException("Nothing is due to invoice on this quotation right now.")

    subtotal = sum(ln.amount_minor for ln in lines)
    tax = sum(ln.tax_minor for ln in lines)
    invoice = Invoice(
        number=_next_number(db, DocumentType.INVOICE.value),
        document_type=DocumentType.INVOICE.value,
        quotation_id=quotation.id,
        customer_id=quotation.customer_id,
        status=InvoiceStatus.ISSUED.value,
        issued_at=datetime.now(timezone.utc),
        subtotal_minor=subtotal,
        tax_minor=tax,
        total_minor=subtotal + tax,
        currency=quotation.currency,
    )
    invoice.lines = lines
    db.add(invoice)
    db.flush()

    for row in consumed_schedule:
        row.status = BillingScheduleStatus.INVOICED.value
        row.invoice_id = invoice.id

    _render_and_store_pdf(db, invoice)

    record_event(
        db,
        quotation,
        EventType.QUOTE_INVOICED,
        actor,
        summary=f"{actor.full_name} issued invoice {invoice.number} for "
        f"{invoice.total_minor / 100:.2f} {invoice.currency}.",
        payload={"invoice_id": invoice.id, "number": invoice.number, "total_minor": invoice.total_minor},
    )

    _advance_quote_to_invoiced(db, quotation, actor)

    db.commit()
    db.refresh(invoice)
    return invoice


def _advance_quote_to_invoiced(db: Session, quotation: Quotation, actor: User) -> None:
    from app.quotations.transitions import transition

    if quotation.status == QuoteStatus.INVOICED.value:
        return
    if quotation.status == QuoteStatus.CONFIRMED.value:
        # A subscription-only order never enters fulfilment — allowed by the
        # `confirmed -> invoiced` edge added for Phase 3.
        transition(db, quotation, QuoteStatus.INVOICED.value, actor, expected_version=quotation.version)
    elif quotation.status == QuoteStatus.FULFILLING.value:
        transition(db, quotation, QuoteStatus.INVOICED.value, actor, expected_version=quotation.version)


# ----------------------------------------------------------------------- payments


def record_payment(
    db: Session, invoice: Invoice, amount_minor: int, method: str, reference: str | None, actor: User
) -> Invoice:
    if invoice.status not in (InvoiceStatus.ISSUED.value,):
        raise ConflictException(
            f"Invoice {invoice.number} is {invoice.status}; payments can only be recorded "
            "against an issued invoice.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )
    if amount_minor <= 0:
        raise ValidationException("Payment amount must be positive.")

    db.add(
        Payment(
            invoice_id=invoice.id,
            amount_minor=amount_minor,
            method=method,
            reference=reference,
            recorded_by_id=actor.id,
        )
    )
    invoice.paid_minor += amount_minor

    quotation = db.get(Quotation, invoice.quotation_id)
    fully_paid = invoice.paid_minor >= invoice.total_minor
    if fully_paid:
        invoice.status = InvoiceStatus.PAID.value

    if quotation is not None:
        record_event(
            db,
            quotation,
            EventType.QUOTE_PAYMENT_RECORDED,
            actor,
            summary=(
                f"{actor.full_name} recorded a {amount_minor / 100:.2f} {invoice.currency} payment "
                f"on {invoice.number}"
                + (" — paid in full." if fully_paid else ".")
            ),
            payload={"invoice_id": invoice.id, "amount_minor": amount_minor, "fully_paid": fully_paid},
        )
        if fully_paid and quotation.status == QuoteStatus.INVOICED.value:
            from app.quotations.transitions import transition

            transition(db, quotation, QuoteStatus.PAID.value, actor, expected_version=quotation.version)

    db.commit()
    db.refresh(invoice)
    return invoice


# ---------------------------------------------------------------------- supersede


def supersede_invoice(
    db: Session, original: Invoice, reason: str, lines: list[SupersedeLine], actor: User
) -> tuple[Invoice, Invoice]:
    if original.status in (InvoiceStatus.SUPERSEDED.value, InvoiceStatus.VOID.value):
        raise ConflictException(
            f"Invoice {original.number} is already {original.status}.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )
    if original.document_type != DocumentType.INVOICE.value:
        raise ValidationException("Only an invoice can be superseded, not a credit note.")
    if not lines:
        raise ValidationException("The corrected invoice needs at least one line.")

    now = datetime.now(timezone.utc)

    # 1. Credit note reversing the original in full.
    credit_note = Invoice(
        number=_next_number(db, DocumentType.CREDIT_NOTE.value),
        document_type=DocumentType.CREDIT_NOTE.value,
        quotation_id=original.quotation_id,
        customer_id=original.customer_id,
        status=InvoiceStatus.ISSUED.value,
        issued_at=now,
        subtotal_minor=original.subtotal_minor,
        tax_minor=original.tax_minor,
        total_minor=original.total_minor,
        currency=original.currency,
        supersedes_invoice_id=original.id,
    )
    credit_note.lines = [
        InvoiceLine(
            description=f"Reversal — {ln.description}",
            quantity=ln.quantity,
            unit_price_minor=ln.unit_price_minor,
            tax_minor=ln.tax_minor,
            amount_minor=ln.amount_minor,
        )
        for ln in original.lines
    ]
    db.add(credit_note)
    db.flush()

    # 3. Corrected invoice.
    subtotal = sum(ln.amount_minor for ln in lines)
    tax = sum(ln.tax_minor for ln in lines)
    new_invoice = Invoice(
        number=_next_number(db, DocumentType.INVOICE.value),
        document_type=DocumentType.INVOICE.value,
        quotation_id=original.quotation_id,
        customer_id=original.customer_id,
        status=InvoiceStatus.ISSUED.value,
        issued_at=now,
        subtotal_minor=subtotal,
        tax_minor=tax,
        total_minor=subtotal + tax,
        currency=original.currency,
        supersedes_invoice_id=original.id,
    )
    new_invoice.lines = [
        InvoiceLine(
            description=ln.description,
            quantity=ln.quantity,
            unit_price_minor=ln.unit_price_minor,
            tax_minor=ln.tax_minor,
            amount_minor=ln.amount_minor,
        )
        for ln in lines
    ]
    db.add(new_invoice)
    db.flush()

    # 2. Point the original at both. Only mutable-after-draft columns change.
    original.status = InvoiceStatus.SUPERSEDED.value
    original.superseded_by_invoice_id = new_invoice.id
    original.credit_note_id = credit_note.id

    _render_and_store_pdf(db, credit_note)
    _render_and_store_pdf(db, new_invoice)

    quotation = db.get(Quotation, original.quotation_id)
    if quotation is not None:
        record_event(
            db,
            quotation,
            EventType.QUOTE_INVOICE_SUPERSEDED,
            actor,
            summary=(
                f"{actor.full_name} superseded {original.number}: credit note {credit_note.number} "
                f"issued, replaced by {new_invoice.number}. Reason: \"{reason}\""
            ),
            payload={
                "original_invoice_id": original.id,
                "credit_note_id": credit_note.id,
                "new_invoice_id": new_invoice.id,
                "reason": reason,
            },
        )

    db.commit()
    db.refresh(credit_note)
    db.refresh(new_invoice)
    return credit_note, new_invoice


def get_lineage(db: Session, invoice: Invoice) -> list[InvoiceRead]:
    """Walk the supersession chain both directions, oldest → newest."""
    # Back to the root.
    root = invoice
    seen: set[int] = set()
    while root.supersedes_invoice_id is not None and root.supersedes_invoice_id not in seen:
        seen.add(root.id)
        parent = db.get(Invoice, root.supersedes_invoice_id)
        if parent is None or parent.document_type != DocumentType.INVOICE.value:
            break
        root = parent

    chain: list[Invoice] = [root]
    seen = {root.id}
    cursor = root
    while cursor.superseded_by_invoice_id is not None and cursor.superseded_by_invoice_id not in seen:
        nxt = db.get(Invoice, cursor.superseded_by_invoice_id)
        if nxt is None:
            break
        chain.append(nxt)
        seen.add(nxt.id)
        cursor = nxt

    return [_to_invoice_read(inv) for inv in chain]


# -------------------------------------------------------------------------- reads


def list_invoices(
    db: Session, *, page: int, page_size: int, quotation_id: int | None, status: str | None
) -> tuple[list[Invoice], int]:
    stmt = select(Invoice)
    if quotation_id is not None:
        stmt = stmt.where(Invoice.quotation_id == quotation_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundException("Invoice not found")
    return invoice


def get_quotation_or_404(db: Session, quotation_id: int) -> Quotation:
    quotation = db.get(Quotation, quotation_id)
    if quotation is None:
        raise NotFoundException("Quotation not found")
    return quotation


def run_subscription_invoice_job(db: Session) -> int:
    """Scheduled: issue an invoice for every quotation with a due, still-scheduled
    billing period. Idempotent — a period flips to `invoiced` the first time."""
    due_quote_ids = db.scalars(
        select(BillingSchedule.quotation_id)
        .where(
            BillingSchedule.status == BillingScheduleStatus.SCHEDULED.value,
            BillingSchedule.period_start <= date.today(),
        )
        .distinct()
    ).all()
    system_actor = db.scalar(select(User).where(User.is_org_owner.is_(True)))
    issued = 0
    for quotation_id in due_quote_ids:
        quotation = db.get(Quotation, quotation_id)
        if quotation is None or quotation.status in (
            QuoteStatus.CANCELLED.value,
            QuoteStatus.REJECTED.value,
        ):
            continue
        try:
            generate_invoice(db, quotation, system_actor or _fake_actor())
            issued += 1
        except (ConflictException, ValidationException):
            db.rollback()
        except Exception:
            logger.exception("subscription invoice job failed for quotation %s", quotation_id)
            db.rollback()
    return issued


def _fake_actor() -> User:
    user = User(id=0, email="system@dealflow", full_name="System", hashed_password="")
    return user
