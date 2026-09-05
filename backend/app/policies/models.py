from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.catalog.models import Category
from app.db.base import Base, OrgScopedMixin


class DiscountPolicy(Base, OrgScopedMixin):
    __tablename__ = "discount_policies"
    __table_args__ = (
        UniqueConstraint("org_id", "version", name="uq_discount_policies_org_version"),
        # Only one policy can be active at a time *per organization* — enforced by
        # the database, not just application logic. See `BACKEND_PHASE_1.md` Task 7.
        Index(
            "ix_discount_policies_is_active",
            "org_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False)
    upsell: Mapped[dict] = mapped_column(JSONB, nullable=False)
    anomaly: Mapped[dict] = mapped_column(JSONB, nullable=False)
    stalled_after_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tier_ceilings: Mapped[list["PolicyTierCeiling"]] = relationship(
        "PolicyTierCeiling", back_populates="policy", cascade="all, delete-orphan", lazy="selectin"
    )
    category_ceilings: Mapped[list["PolicyCategoryCeiling"]] = relationship(
        "PolicyCategoryCeiling", back_populates="policy", cascade="all, delete-orphan", lazy="selectin"
    )


class PolicyTierCeiling(Base, OrgScopedMixin):
    __tablename__ = "policy_tier_ceilings"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("discount_policies.id"), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    ceiling_bps: Mapped[int] = mapped_column(Integer, nullable=False)

    policy: Mapped[DiscountPolicy] = relationship(DiscountPolicy, back_populates="tier_ceilings")


class PolicyCategoryCeiling(Base, OrgScopedMixin):
    __tablename__ = "policy_category_ceilings"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("discount_policies.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    ceiling_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_floor_bps: Mapped[int] = mapped_column(Integer, nullable=False)

    policy: Mapped[DiscountPolicy] = relationship(DiscountPolicy, back_populates="category_ceilings")
    category: Mapped[Category] = relationship(Category, lazy="joined")
