from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.types import MoneyMinor

ApprovalLevel = Literal["l1_sales_manager", "l2_finance"]
ApprovalStatus = Literal["pending", "approved", "rejected", "returned", "skipped"]
ApprovalAction = Literal["approve", "reject", "return_for_revision"]


class ApprovalRead(BaseModel):
    id: int
    quotation_id: int
    quotation_reference: str
    customer_name: str
    total_minor: MoneyMinor
    currency: str
    level: ApprovalLevel
    sequence: int
    status: ApprovalStatus
    risk_score: int
    acted_by_id: int | None
    acted_by_name: str | None
    reason: str | None
    acted_at: datetime | None
    created_at: datetime


class ApprovalActRequest(BaseModel):
    action: ApprovalAction
    reason: str | None = None
