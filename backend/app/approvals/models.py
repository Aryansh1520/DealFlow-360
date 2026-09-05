from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuoteApproval(Base):
    __tablename__ = "quote_approvals"
    __table_args__ = (
        Index("ix_quote_approvals_quotation_id", "quotation_id"),
        Index("ix_quote_approvals_status_level", "status", "level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    # "l1_sales_manager" | "l2_finance" — see app/core/enums.py::ApprovalLevel.
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    # "pending" | "approved" | "rejected" | "returned" | "skipped" — ApprovalStatus.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    acted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(1000))
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quotation: Mapped["Quotation"] = relationship("Quotation", lazy="joined")  # noqa: F821
    acted_by: Mapped["User | None"] = relationship("User", lazy="joined")  # noqa: F821
