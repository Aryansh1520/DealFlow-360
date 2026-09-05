from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, OrgScopedMixin


class DealMetric(Base, OrgScopedMixin):
    """One row per quotation, upserted inside `record_event()` in the same
    transaction as the event — so it is strongly consistent with the ledger
    (`FEATURES.md` §4). Serves `GET /dashboard/deal-health` directly."""

    __tablename__ = "deal_metrics"
    __table_args__ = (
        Index("ix_deal_metrics_last_activity", "last_activity_at"),
        Index("ix_deal_metrics_owner_stage", "owner_rep_id", "stage"),
        Index("ix_deal_metrics_flags", "flags", postgresql_using="gin"),
    )

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), primary_key=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_rep_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    margin_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    days_inactive: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RepDiscountStats(Base, OrgScopedMixin):
    """Running Welford aggregate of effective discount bps per rep, updated on each
    confirmed quote. `sigma = sqrt(m2 / (n - 1))` for n > 1."""

    __tablename__ = "rep_discount_stats"

    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mean_bps: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    m2: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DealAlert(Base, OrgScopedMixin):
    __tablename__ = "deal_alerts"
    __table_args__ = (
        Index("ix_deal_alerts_quotation_id", "quotation_id"),
        Index("ix_deal_alerts_type_ack", "alert_type", "acknowledged"),
        Index("uq_deal_alerts_dedupe", "quotation_id", "dedupe_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(String(1000), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Idempotency key for the scheduled sweeps: "{alert_type}:{date}" so a given
    # alert fires at most once per quotation per day.
    dedupe_key: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
