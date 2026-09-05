from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SubscriptionPlan(Base, TimestampMixin):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "monthly" | "quarterly" | "yearly" — see app/core/enums.py::BillingInterval.
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_cycles: Mapped[int | None] = mapped_column(Integer)
    proration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cancellation_notice_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # "prorated" | "none" | "credit_note" — see app/core/enums.py::RefundPolicy.
    refund_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="prorated")
