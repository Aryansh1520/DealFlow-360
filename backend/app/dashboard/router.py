import io
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_permissions
from app.core.money import format_minor
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.core.storage import put_object
from app.dashboard import service
from app.dashboard.schemas import AlertRead, DashboardSummary, DealHealthRow, SalesReportRow
from app.db.session import get_db

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
DashboardRead = Depends(require_permissions("dashboard:read"))
ReportsRead = Depends(require_permissions("reports:read"))
ReportsExport = Depends(require_permissions("reports:export"))


@router.get("/dashboard", response_model=SuccessResponse[DashboardSummary], dependencies=[DashboardRead])
def dashboard_summary(current_user: CurrentUser, db: DbSession):
    """Role-shaped landing payload — layout chosen by `current_user.role.dashboard_type`."""
    return ok(service.dashboard_summary(db, current_user), "Dashboard summary retrieved.")


@router.get(
    "/dashboard/deal-health",
    response_model=SuccessResponse[Page[DealHealthRow]],
    dependencies=[DashboardRead],
)
def deal_health(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    owner_rep_id: Annotated[int | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
    active_since: Annotated[datetime | None, Query()] = None,
):
    rows, total = service.list_deal_health(db, params, owner_rep_id, stage, active_since)
    return ok(Page[DealHealthRow].create(rows, total, params), "Deal health retrieved.")


@router.get("/dashboard/deal-health/export", dependencies=[DashboardRead])
def export_deal_health(
    current_user: CurrentUser,
    db: DbSession,
    format: Annotated[Literal["pdf", "xlsx"], Query()],
    owner_rep_id: Annotated[int | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
    active_since: Annotated[datetime | None, Query()] = None,
) -> Response:
    big_params = PageParams(page=1, page_size=100)
    rows: list[DealHealthRow] = []
    while True:
        page_rows, total = service.list_deal_health(
            db, big_params, owner_rep_id, stage, active_since
        )
        rows.extend(page_rows)
        if big_params.page * big_params.page_size >= total or not page_rows:
            break
        big_params.page += 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if format == "xlsx":
        data = _deal_rows_to_xlsx(rows)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        key = f"exports/deal-health-{stamp}.xlsx"
    else:
        data = _deal_rows_to_pdf(rows)
        media = "application/pdf"
        key = f"exports/deal-health-{stamp}.pdf"

    put_object(key, data, content_type=media)
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{key.split("/")[-1]}"'},
    )


@router.get(
    "/dashboard/alerts", response_model=SuccessResponse[Page[AlertRead]], dependencies=[DashboardRead]
)
def list_alerts(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    type: Annotated[str | None, Query()] = None,
    acknowledged: Annotated[bool | None, Query()] = None,
):
    rows, total = service.list_alerts(db, params, type, acknowledged)
    return ok(Page[AlertRead].create(rows, total, params), "Alerts retrieved.")


@router.post(
    "/dashboard/alerts/{alert_id}/nudge",
    response_model=SuccessResponse[AlertRead],
    dependencies=[DashboardRead],
)
def nudge_alert(alert_id: int, current_user: CurrentUser, db: DbSession):
    alert = service.get_alert_or_404(db, alert_id)
    return ok(service.nudge_alert(db, alert, current_user), "Owner nudged.")


@router.post(
    "/dashboard/alerts/{alert_id}/acknowledge",
    response_model=SuccessResponse[AlertRead],
    dependencies=[DashboardRead],
)
def acknowledge_alert(alert_id: int, current_user: CurrentUser, db: DbSession):
    alert = service.get_alert_or_404(db, alert_id)
    return ok(service.acknowledge_alert(db, alert), "Alert acknowledged.")


@router.get(
    "/reports/sales", response_model=SuccessResponse[Page[SalesReportRow]], dependencies=[ReportsRead]
)
def sales_report(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    period: Annotated[str | None, Query()] = None,
    rep_id: Annotated[int | None, Query()] = None,
    team_id: Annotated[int | None, Query()] = None,
    approval_status: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
):
    rows, total = service.sales_report(
        db, params, period=period, rep_id=rep_id, approval_status=approval_status, category_id=category_id
    )
    return ok(Page[SalesReportRow].create(rows, total, params), "Sales report retrieved.")


@router.get("/reports/sales/export", dependencies=[ReportsExport])
def export_sales_report(
    current_user: CurrentUser,
    db: DbSession,
    format: Annotated[Literal["pdf", "xlsx"], Query()],
    period: Annotated[str | None, Query()] = None,
    rep_id: Annotated[int | None, Query()] = None,
    team_id: Annotated[int | None, Query()] = None,
    approval_status: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
) -> Response:
    big_params = PageParams(page=1, page_size=100)
    rows: list[SalesReportRow] = []
    while True:
        page_rows, total = service.sales_report(
            db, big_params, period=period, rep_id=rep_id, approval_status=approval_status, category_id=category_id
        )
        rows.extend(page_rows)
        if big_params.page * big_params.page_size >= total or not page_rows:
            break
        big_params.page += 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if format == "xlsx":
        data = _rows_to_xlsx(rows)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        key = f"exports/sales-{stamp}.xlsx"
    else:
        data = _rows_to_pdf(rows)
        media = "application/pdf"
        key = f"exports/sales-{stamp}.pdf"

    # Persist the artefact to MinIO (audit / re-download), then stream the bytes back
    # to this authenticated caller.
    put_object(key, data, content_type=media)
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{key.split("/")[-1]}"'},
    )


def _deal_rows_to_xlsx(rows: list[DealHealthRow]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Deal health"
    ws.append(
        ["Reference", "Customer", "Owner", "Stage", "Total", "Margin %", "Risk", "Idle (days)", "Flags"]
    )
    for r in rows:
        ws.append(
            [
                r.reference,
                r.customer_name,
                r.owner_rep_name,
                r.stage,
                r.total_minor / 100,
                round(r.margin_bps / 100, 2),
                r.risk_score,
                r.days_inactive,
                ", ".join(r.flags),
            ]
        )
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _deal_rows_to_pdf(rows: list[DealHealthRow]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, y, "Deal health")
    pdf.setFont("Helvetica", 8)
    y -= 10 * mm
    pdf.drawString(
        20 * mm, y, "Reference        Customer            Owner            Stage         Total       Risk  Idle  Flags"
    )
    y -= 5 * mm
    for r in rows:
        if y < 20 * mm:
            pdf.showPage()
            pdf.setFont("Helvetica", 8)
            y = height - 20 * mm
        pdf.drawString(
            20 * mm,
            y,
            f"{r.reference:<15.15}  {r.customer_name:<18.18}  {r.owner_rep_name:<15.15}  "
            f"{r.stage:<12.12}  {format_minor(r.total_minor, r.currency):>12}  {r.risk_score:>4}  "
            f"{r.days_inactive:>4}  {', '.join(r.flags):.20}",
        )
        y -= 5 * mm
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _rows_to_xlsx(rows: list[SalesReportRow]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Period", "Reference", "Customer", "Owner", "Status", "Total", "Margin %"])
    for r in rows:
        ws.append(
            [
                r.period,
                r.reference,
                r.customer_name,
                r.owner_rep_name,
                r.status,
                r.total_minor / 100,
                round(r.margin_bps / 100, 2),
            ]
        )
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _rows_to_pdf(rows: list[SalesReportRow]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, y, "Sales report")
    pdf.setFont("Helvetica", 8)
    y -= 10 * mm
    pdf.drawString(20 * mm, y, "Period   Reference        Customer            Owner            Status        Total     Margin%")
    y -= 5 * mm
    for r in rows:
        if y < 20 * mm:
            pdf.showPage()
            pdf.setFont("Helvetica", 8)
            y = height - 20 * mm
        pdf.drawString(
            20 * mm,
            y,
            f"{r.period}  {r.reference:<15.15}  {r.customer_name:<18.18}  {r.owner_rep_name:<15.15}  "
            f"{r.status:<12.12}  {format_minor(r.total_minor, r.currency):>12}  {r.margin_bps / 100:>6.1f}",
        )
        y -= 5 * mm
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
