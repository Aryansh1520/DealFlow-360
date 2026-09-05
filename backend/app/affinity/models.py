from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, PrimaryKeyConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductAffinity(Base):
    """Precomputed co-purchase association between two products, from historical
    `quote_lines`. `lift` is the one place a `Numeric` is acceptable — it's a ratio,
    not money. See `BACKEND_PHASE_2.md` Task 7."""

    __tablename__ = "product_affinity"
    __table_args__ = (
        PrimaryKeyConstraint("product_a", "product_b"),
        Index("ix_product_affinity_a_lift", "product_a", "lift"),
    )

    product_a: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_b: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    support_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    lift: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
