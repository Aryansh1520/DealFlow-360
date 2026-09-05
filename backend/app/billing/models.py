from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BillingScheduleStatus, DocumentType, InvoiceStatus
from app.core.exceptions import ConflictException, ErrorCode
from app.db.base import Base, OrgScopedMixin


class BillingSchedule(Base, OrgScopedMixin):
    """One concrete billing period for one subscription line. The unique
    `(line_id, period_start)` constraint is what makes the subscription-invoice
    job idempotent — a second run inserts nothing."""

    __tablename__ = "billing_schedule"
    __table_args__ = (
        UniqueConstraint("line_id", "period_start", name="uq_billing_schedule_line_period"),
        Index("ix_billing_schedule_quotation_id", "quotation_id"),
        Index("ix_billing_schedule_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("quote_lines.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_prorated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proration_days: Mapped[int | None] = mapped_column(Integer)
    proration_basis_days: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BillingScheduleStatus.SCHEDULED.value
    )
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Invoice(Base, OrgScopedMixin):
    """Append-only after `draft`: the `before_update` listener below refuses any
    column change except `status`, `paid_minor`, `superseded_by_invoice_id`,
    `credit_note_id`. Corrections go through `POST /invoices/{id}/supersede`."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("org_id", "number", name="uq_invoices_org_number"),
        Index("ix_invoices_quotation_id", "quotation_id"),
        Index("ix_invoices_customer_id", "customer_id"),
        Index("ix_invoices_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DocumentType.INVOICE.value
    )
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InvoiceStatus.DRAFT.value
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    paid_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    supersedes_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    superseded_by_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    credit_note_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    # Object key of the rendered PDF in MinIO. Never served off disk — only streamed
    # back through GET /invoices/{id}/pdf after the caller passes the ownership check.
    pdf_object_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.id",
        lazy="selectin",
    )

    @property
    def balance_minor(self) -> int:
        return self.total_minor - self.paid_minor

    @property
    def is_immutable(self) -> bool:
        return self.status != InvoiceStatus.DRAFT.value


class InvoiceLine(Base, OrgScopedMixin):
    __tablename__ = "invoice_lines"
    __table_args__ = (Index("ix_invoice_lines_invoice_id", "invoice_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)

    invoice: Mapped[Invoice] = relationship(Invoice, back_populates="lines")


class Payment(Base, OrgScopedMixin):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_invoice_id", "invoice_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255))
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# Columns still writable once an invoice has left `draft`. Everything else is frozen.
_MUTABLE_AFTER_DRAFT = {
    "status",
    "paid_minor",
    "superseded_by_invoice_id",
    "credit_note_id",
    "pdf_object_key",
}


@event.listens_for(Invoice, "before_update")
def _enforce_invoice_immutability(mapper, connection, target: Invoice) -> None:
    """Make the ORM itself refuse a mutation the contract forbids — don't rely on
    every call site remembering the rule. `BACKEND_PHASE_3.md` Task 4."""
    state = sa_inspect(target)
    status_history = state.attrs.status.history
    # The status as it was loaded from the DB (before this flush's change, if any).
    original_status = (
        status_history.deleted[0]
        if status_history.deleted
        else (status_history.unchanged[0] if status_history.unchanged else target.status)
    )
    if original_status == InvoiceStatus.DRAFT.value:
        return

    changed = [
        attr.key
        for attr in state.attrs
        if attr.key not in _MUTABLE_AFTER_DRAFT and attr.history.has_changes()
    ]
    if changed:
        raise ConflictException(
            f"Invoice {target.number} is issued and immutable; refused change to "
            f"{', '.join(sorted(changed))}. Use POST /invoices/{{id}}/supersede.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )
