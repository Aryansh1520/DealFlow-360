from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.enums import DashboardType
from app.core.types import Bps, MoneyMinor

AlertSeverity = Literal["low", "medium", "high"]
StatUnit = Literal["currency", "count", "bps", "days"]


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


class DashboardStat(BaseModel):
    key: str
    label: str
    value: int
    unit: StatUnit
    hint: str | None = None


class DashboardSummary(BaseModel):
    """`GET /dashboard` — the role-shaped landing payload. `dashboard_type` comes
    from the caller's `role.dashboard_type` (set on the Roles screen); the frontend
    renders one of four layouts from it. RBAC still gates every underlying endpoint."""

    dashboard_type: DashboardType
    generated_at: datetime
    currency: str
    stats: list[DashboardStat]
    alerts: list[AlertRead]


class SalesReportRow(BaseModel):
    period: str
    quotation_id: int
    reference: str
    customer_name: str
    owner_rep_name: str
    status: str
    total_minor: MoneyMinor
    margin_bps: Bps
    currency: str
