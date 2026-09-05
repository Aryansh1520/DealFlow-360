from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.catalog.models import Product
from app.db.base import Base, OrgScopedMixin, TimestampMixin


class Warehouse(Base, TimestampMixin, OrgScopedMixin):
    __tablename__ = "warehouses"
    __table_args__ = (UniqueConstraint("org_id", "code", name="uq_warehouses_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    # Relative weight used by the (Phase 3) allocator to rank warehouses and to
    # estimate shipping cost. 1..100, enforced at the schema layer.
    shipping_cost_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    replenishment_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Stock(Base, OrgScopedMixin):
    __tablename__ = "stock"
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product: Mapped[Product] = relationship(Product, lazy="joined")
    warehouse: Mapped[Warehouse] = relationship(Warehouse, lazy="joined")


class StockMovement(Base, OrgScopedMixin):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
