from typing import Literal

from pydantic import BaseModel

from app.core.security import UserType
from app.core.types import Bps, MoneyMinor


class PortalQuoteLine(BaseModel):
    id: int
    product_name: str
    quantity: int
    unit_price_minor: MoneyMinor
    discount_bps: Bps
    net_minor: MoneyMinor
    tax_minor: MoneyMinor


class PortalTotals(BaseModel):
    gross_minor: MoneyMinor
    discount_total_minor: MoneyMinor
    net_minor: MoneyMinor
    tax_minor: MoneyMinor
    total_minor: MoneyMinor


class PortalTimelineEntry(BaseModel):
    event_type: str
    summary: str
    created_at: str
    actor_label: str


class PortalQuotationRead(BaseModel):
    id: int
    reference: str
    status: str
    version: int
    currency: str
    valid_until: str | None
    customer_name: str
    lines: list[PortalQuoteLine]
    totals: PortalTotals
    timeline: list[PortalTimelineEntry]
    can_confirm: bool
    can_counter: bool


class PortalCommentRequest(BaseModel):
    line_id: int | None = None
    body: str


class PortalCounterRequest(BaseModel):
    requested_discount_bps: Bps
    line_id: int | None = None
    message: str | None = None


class PortalConfirmRequest(BaseModel):
    expected_version: int


class PortalConfirmResponse(BaseModel):
    status: str
    re_entered_approval: bool


class MagicLinkRedeemRequest(BaseModel):
    token: str


class MagicLinkRedeemResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_type: UserType
    quotation_id: int
