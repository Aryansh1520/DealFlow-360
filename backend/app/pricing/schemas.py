from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Bps, MoneyMinor

CustomerTier = Literal["bronze", "silver", "gold"]


class PriceListEntryCreate(BaseModel):
    product_id: int
    variant_id: int | None = None
    override_price_minor: MoneyMinor | None = None
    extra_discount_bps: Bps = 0


class PriceListEntryUpdate(BaseModel):
    override_price_minor: MoneyMinor | None = None
    extra_discount_bps: Bps | None = None


class PriceListEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price_list_id: int
    product_id: int
    variant_id: int | None
    override_price_minor: MoneyMinor | None
    extra_discount_bps: Bps


class PriceListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    tier: CustomerTier | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    is_default: bool = False
    valid_from: date | None = None
    valid_to: date | None = None


class PriceListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tier: CustomerTier | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_default: bool | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class PriceListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tier: CustomerTier | None
    currency: str
    is_default: bool
    valid_from: date | None
    valid_to: date | None
    entries: list[PriceListEntryRead]
