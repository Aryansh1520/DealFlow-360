from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import require_permissions
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse
from app.core.stub import not_implemented
from app.dashboard.schemas import AlertRead, DealHealthRow

router = APIRouter()

DashboardRead = Depends(require_permissions("dashboard:read"))
ReportsRead = Depends(require_permissions("reports:read"))
ReportsExport = Depends(require_permissions("reports:export"))


@router.get(
    "/dashboard/deal-health", response_model=SuccessResponse[Page[DealHealthRow]], dependencies=[DashboardRead]
)
def deal_health(
    params: Annotated[PageParams, Depends()],
    owner_rep_id: Annotated[int | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
):
    not_implemented()


@router.get(
    "/dashboard/alerts", response_model=SuccessResponse[Page[AlertRead]], dependencies=[DashboardRead]
)
def list_alerts(
    params: Annotated[PageParams, Depends()],
    type: Annotated[str | None, Query()] = None,
    acknowledged: Annotated[bool | None, Query()] = None,
):
    not_implemented()


@router.post(
    "/dashboard/alerts/{alert_id}/nudge", response_model=SuccessResponse[AlertRead], dependencies=[DashboardRead]
)
def nudge_alert(alert_id: int):
    not_implemented()


@router.post(
    "/dashboard/alerts/{alert_id}/acknowledge",
    response_model=SuccessResponse[AlertRead],
    dependencies=[DashboardRead],
)
def acknowledge_alert(alert_id: int):
    not_implemented()


@router.get("/reports/sales", response_model=SuccessResponse[Page[dict]], dependencies=[ReportsRead])
def sales_report(
    params: Annotated[PageParams, Depends()],
    period: Annotated[str | None, Query()] = None,
    rep_id: Annotated[int | None, Query()] = None,
    team_id: Annotated[int | None, Query()] = None,
    approval_status: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
):
    not_implemented()


@router.get("/reports/sales/export", dependencies=[ReportsExport])
def export_sales_report(
    format: Annotated[Literal["pdf", "xlsx"], Query()],
    period: Annotated[str | None, Query()] = None,
    rep_id: Annotated[int | None, Query()] = None,
    team_id: Annotated[int | None, Query()] = None,
    approval_status: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
) -> Response:
    not_implemented()
