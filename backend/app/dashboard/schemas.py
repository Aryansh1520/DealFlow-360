from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.types import Bps, MoneyMinor

AlertSeverity = Literal["low", "medium", "high"]


class DealHealthRow(BaseModel):
    quotation_id: int
    reference: str
    customer_name: str
    owner_rep_name: str
    stage: str
    total_minor: MoneyMinor
    margin_bps: Bps
    risk_score: int
    days_inactive: int
    flags: list[str]
    last_activity_at: datetime
    currency: str


class AlertRead(BaseModel):
    id: int
    alert_type: str
    quotation_id: int
    quotation_reference: str
    severity: AlertSeverity
    title: str
    detail: str
    metrics: dict[str, float]
    acknowledged: bool
    created_at: datetime
