from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import BackorderStatus, ReservationStatus, ShipmentStatus
from app.db.base import Base, OrgScopedMixin


class StockReservation(Base, OrgScopedMixin):
    """A hold placed on `stock.reserved` when a fulfilment plan is accepted.
    `held` while the shipment is planned, `committed` once dispatched, `released`
    if the plan is overridden or the quote cancelled."""

    __tablename__ = "stock_reservations"
    __table_args__ = (
        Index("ix_stock_reservations_quotation_id", "quotation_id"),
        Index("ix_stock_reservations_product_warehouse", "product_id", "warehouse_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("quote_lines.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReservationStatus.HELD.value
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Shipment(Base, OrgScopedMixin):
    __tablename__ = "shipments"
    __table_args__ = (Index("ix_shipments_quotation_id", "quotation_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ShipmentStatus.PLANNED.value
    )
    estimated_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShipmentLine(Base, OrgScopedMixin):
    __tablename__ = "shipment_lines"
    __table_args__ = (Index("ix_shipment_lines_shipment_id", "shipment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("quote_lines.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class Backorder(Base, OrgScopedMixin):
    __tablename__ = "backorders"
    __table_args__ = (Index("ix_backorders_quotation_status", "quotation_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("quote_lines.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BackorderStatus.OPEN.value
    )
    expected_restock_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
