from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, OrgScopedMixin, TimestampMixin


class PriceList(Base, TimestampMixin, OrgScopedMixin):
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # bronze | silver | gold | null (null == applies regardless of tier)
    tier: Mapped[str | None] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    entries: Mapped[list["PriceListEntry"]] = relationship(
        "PriceListEntry", back_populates="price_list", cascade="all, delete-orphan", lazy="selectin"
    )


class PriceListEntry(Base, OrgScopedMixin):
    __tablename__ = "price_list_entries"
    __table_args__ = (
        UniqueConstraint("price_list_id", "product_id", "variant_id"),
        Index("ix_price_list_entries_price_list_product", "price_list_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    price_list_id: Mapped[int] = mapped_column(ForeignKey("price_lists.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    override_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    extra_discount_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    price_list: Mapped[PriceList] = relationship(PriceList, back_populates="entries")
