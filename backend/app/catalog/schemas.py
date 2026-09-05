from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Bps, MoneyMinor

LineType = Literal["one_time", "subscription"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProductVariantCreate(BaseModel):
    attribute: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=100)
    extra_price_minor: MoneyMinor = 0


class ProductVariantUpdate(BaseModel):
    attribute: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = Field(default=None, min_length=1, max_length=100)
    extra_price_minor: MoneyMinor | None = None


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    attribute: str
    value: str
    extra_price_minor: MoneyMinor


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    category_id: int
    description: str | None = Field(default=None, max_length=2000)
    unit: str = Field(default="unit", max_length=50)
    list_price_minor: MoneyMinor
    cost_price_minor: MoneyMinor
    tax_bps: Bps = 0
    is_promoted: bool = False
    line_type: LineType = "one_time"
    subscription_plan_id: int | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    is_active: bool = True


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=2000)
    unit: str | None = Field(default=None, max_length=50)
    list_price_minor: MoneyMinor | None = None
    cost_price_minor: MoneyMinor | None = None
    tax_bps: Bps | None = None
    is_promoted: bool | None = None
    line_type: LineType | None = None
    subscription_plan_id: int | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    category_id: int
    category_name: str
    description: str | None
    unit: str
    list_price_minor: MoneyMinor
    cost_price_minor: MoneyMinor
    tax_bps: Bps
    is_promoted: bool
    line_type: LineType
    subscription_plan_id: int | None
    currency: str
    is_active: bool
    variants: list[ProductVariantRead]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, product) -> "ProductRead":
        return cls(
            id=product.id,
            name=product.name,
            sku=product.sku,
            category_id=product.category_id,
            category_name=product.category.name,
            description=product.description,
            unit=product.unit,
            list_price_minor=product.list_price_minor,
            cost_price_minor=product.cost_price_minor,
            tax_bps=product.tax_bps,
            is_promoted=product.is_promoted,
            line_type=product.line_type,
            subscription_plan_id=product.subscription_plan_id,
            currency=product.currency,
            is_active=product.is_active,
            variants=list(product.variants),
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
