from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BillingInterval = Literal["monthly", "quarterly", "yearly"]
RefundPolicy = Literal["prorated", "none", "credit_note"]


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    interval: BillingInterval
    billing_cycles: int | None = Field(default=None, ge=1)
    proration_enabled: bool = True
    cancellation_notice_days: int = Field(default=0, ge=0)
    refund_policy: RefundPolicy = "prorated"


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    interval: BillingInterval | None = None
    billing_cycles: int | None = Field(default=None, ge=1)
    proration_enabled: bool | None = None
    cancellation_notice_days: int | None = Field(default=None, ge=0)
    refund_policy: RefundPolicy | None = None


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    interval: BillingInterval
    billing_cycles: int | None
    proration_enabled: bool
    cancellation_notice_days: int
    refund_policy: RefundPolicy
