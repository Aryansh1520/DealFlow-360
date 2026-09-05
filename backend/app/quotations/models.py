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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        Index("ix_quotations_status_updated", "status", "updated_at"),
        Index("ix_quotations_owner_created", "owner_rep_id", "created_at"),
        # Tiny, hottest-read partial index — the approval queue.
        Index(
            "ix_quotations_pending_approval",
            "status",
            postgresql_where=text("status IN ('pending_l1', 'pending_l2')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    order_number: Mapped[str | None] = mapped_column(String(32))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    owner_rep_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # quote_status — see app/core/enums.py::QuoteStatus. Only app/quotations/transitions.py
    # ever writes this column — see the comment on `transition()`.
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # (product_id, variant_id, quantity, discount_bps) hash as of the last submit —
    # see app/quotations/service.py::line_hash and DECISION_ENGINE.md §8 "Golden rule".
    approved_line_hash: Mapped[str | None] = mapped_column(String(64))
    order_discount_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    valid_until: Mapped[date | None] = mapped_column(Date)
    # Phase 3 owns fulfilment; this column exists now purely so QuotationRead has
    # somewhere to point. Always null until Phase 3.
    fulfillment_status: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship("Customer", lazy="joined")  # noqa: F821
    owner_rep: Mapped["User"] = relationship("User", lazy="joined")  # noqa: F821
    lines: Mapped[list["QuoteLine"]] = relationship(
        "QuoteLine",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuoteLine.position",
        lazy="selectin",
    )


class QuoteLine(Base):
    __tablename__ = "quote_lines"
    __table_args__ = (Index("ix_quote_lines_quotation_id", "quotation_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    # "one_time" | "subscription" — see app/core/enums.py::LineType.
    line_type: Mapped[str] = mapped_column(String(20), nullable=False, default="one_time")
    subscription_plan_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_plans.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_from_suggestion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    quotation: Mapped[Quotation] = relationship(Quotation, back_populates="lines")
    product: Mapped["Product"] = relationship("Product", lazy="joined")  # noqa: F821
