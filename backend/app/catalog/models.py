from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, OrgScopedMixin, TimestampMixin


class Category(Base, TimestampMixin, OrgScopedMixin):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("org_id", "code", name="uq_categories_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))


class Product(Base, TimestampMixin, OrgScopedMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("org_id", "sku", name="uq_products_org_sku"),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_is_promoted", "is_promoted", postgresql_where=text("is_promoted")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="unit")
    # All money in paise (integer minor units) — never Float. See app/core/money.py.
    list_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_promoted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # "one_time" | "subscription" — see app/core/enums.py::LineType.
    line_type: Mapped[str] = mapped_column(String(20), nullable=False, default="one_time")
    subscription_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscription_plans.id"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    category: Mapped[Category] = relationship(Category, lazy="joined")
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )


class ProductVariant(Base, OrgScopedMixin):
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "attribute", "value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    attribute: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    product: Mapped[Product] = relationship(Product, back_populates="variants")
