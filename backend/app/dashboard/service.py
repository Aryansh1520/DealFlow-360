"""Deal-health read model, anomaly alerts, and the role-shaped dashboard summary.
`BACKEND_PHASE_3.md` Task 5.

`deal_metrics` is upserted inside `record_event()` (see `app/events/service.py`) so
it is strongly consistent with the ledger. This module is the *serving* and
*rule-evaluation* side: it reads `deal_metrics`, runs the four alert rules, and
maintains `rep_discount_stats` (Welford) on each confirmed quote.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AlertSeverity, AlertType, DashboardType, QuoteStatus
from app.core.exceptions import NotFoundException
from app.core.pagination import PageParams
from app.customers.models import Customer
from app.dashboard.models import DealAlert, DealMetric, RepDiscountStats
from app.dashboard.schemas import (
    AlertRead,
    DashboardStat,
    DashboardSummary,
    DealHealthRow,
    SalesReportRow,
)
from app.policies.service import get_active_policy
from app.quotations.models import Quotation
from app.quotations.serialization import compute_quotation
from app.users.models import User

logger = logging.getLogger(__name__)

TERMINAL_STATES = {
    QuoteStatus.PAID.value,
    QuoteStatus.REJECTED.value,
    QuoteStatus.CANCELLED.value,
    QuoteStatus.EXPIRED.value,
}


# --------------------------------------------------------------------- Welford stats


def update_rep_discount_stats(db: Session, rep_id: int, effective_discount_bps: int) -> None:
    """One Welford step on a confirmed quote's effective discount.

        n += 1 ; delta = x - mean ; mean += delta/n ; m2 += delta * (x - mean)
    """
    stats = db.get(RepDiscountStats, rep_id)
    x = float(effective_discount_bps)
    if stats is None:
        stats = RepDiscountStats(rep_id=rep_id, sample_count=1, mean_bps=x, m2=0.0)
        db.add(stats)
        return
    n = stats.sample_count + 1
    mean = float(stats.mean_bps)
    delta = x - mean
    mean += delta / n
    m2 = float(stats.m2) + delta * (x - mean)
    stats.sample_count = n
    stats.mean_bps = mean
    stats.m2 = m2


def _sigma(stats: RepDiscountStats) -> float:
    if stats.sample_count < 2:
        return 0.0
    return math.sqrt(float(stats.m2) / (stats.sample_count - 1))


# ------------------------------------------------------------------- alert evaluation


def _weighted_margin_floor_bps(db: Session, quotation: Quotation) -> int:
    policy = get_active_policy(db)
    net_by_cat: dict[int, int] = {}
    for line in quotation.lines:
        net_by_cat[line.category_id] = net_by_cat.get(line.category_id, 0) + max(
            0, line.quantity * line.unit_price_minor
        )
    total = sum(net_by_cat.values())
    if total == 0:
        return 0
    weighted = 0.0
    for category_id, net in net_by_cat.items():
        floor = policy.category_ceilings.get(category_id, {}).get("margin_floor_bps", 0)
        weighted += (net / total) * floor
    return int(weighted)


def _upsert_alert(
    db: Session,
    quotation: Quotation,
    *,
    alert_type: str,
    severity: str,
    title: str,
    detail: str,
    metrics: dict,
    dedupe_key: str,
) -> DealAlert | None:
    exists = db.scalar(
        select(DealAlert).where(
            DealAlert.quotation_id == quotation.id, DealAlert.dedupe_key == dedupe_key
        )
    )
    if exists is not None:
        return None
    alert = DealAlert(
        quotation_id=quotation.id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        detail=detail,
        metrics=metrics,
        acknowledged=False,
        dedupe_key=dedupe_key,
    )
    db.add(alert)
    return alert


def evaluate_quotation_alerts(db: Session, quotation: Quotation, *, actor: User | None = None) -> list[DealAlert]:
    """Run all four rules for one quotation. Idempotent per (quotation, type, day)
    via `dedupe_key`. Refreshes `deal_metrics.flags`. Caller commits."""
    from app.fulfillment.models import Backorder

    today = date.today().isoformat()
    created: list[DealAlert] = []

    try:
        computation = compute_quotation(db, quotation)
    except Exception:
        logger.debug("alerts: computation failed for quotation %s", quotation.id, exc_info=True)
        computation = None

    metric = db.get(DealMetric, quotation.id)

    # ---- discount_anomaly --------------------------------------------------------
    if computation is not None and quotation.status not in (QuoteStatus.DRAFT.value,):
        policy = get_active_policy(db)
        k = policy.anomaly.get("sigma_multiplier_bps", 20000) / 10000
        min_sample = policy.anomaly.get("min_sample_size", 5)
        stats = db.get(RepDiscountStats, quotation.owner_rep_id)
        if stats is not None and stats.sample_count >= min_sample:
            sigma = _sigma(stats)
            mean = float(stats.mean_bps)
            eff = computation.effective_discount_bps
            if sigma > 0 and eff > mean + k * sigma:
                z = (eff - mean) / sigma
                rep = db.get(User, quotation.owner_rep_id)
                rep_name = rep.full_name if rep else "this rep"
                a = self_pct(eff)
                b = self_pct(mean)
                alert = _upsert_alert(
                    db,
                    quotation,
                    alert_type=AlertType.DISCOUNT_ANOMALY.value,
                    severity=AlertSeverity.HIGH.value if z >= 3 else AlertSeverity.MEDIUM.value,
                    title="Discount well above this rep's norm",
                    detail=(
                        f"{a} discount vs {rep_name}'s {b} average across "
                        f"{stats.sample_count} quotes ({z:.1f}σ)"
                    ),
                    metrics={
                        "effective_discount_bps": float(eff),
                        "rep_mean_bps": mean,
                        "rep_sigma_bps": sigma,
                        "z": z,
                        "sample_count": float(stats.sample_count),
                    },
                    dedupe_key=f"{AlertType.DISCOUNT_ANOMALY.value}:{today}",
                )
                if alert:
                    created.append(alert)

    # ---- margin_erosion -------------------------------------------------------
    if computation is not None and quotation.lines:
        floor = _weighted_margin_floor_bps(db, quotation)
        if floor > 0 and computation.margin_bps < floor:
            gap = floor - computation.margin_bps
            alert = _upsert_alert(
                db,
                quotation,
                alert_type=AlertType.MARGIN_EROSION.value,
                severity=AlertSeverity.HIGH.value if gap >= 500 else AlertSeverity.MEDIUM.value,
                title="Order margin below the category floor",
                detail=(
                    f"Order margin {self_pct(computation.margin_bps)} is below the "
                    f"weighted category floor of {self_pct(floor)} ({self_pct(gap)} short)"
                ),
                metrics={"margin_bps": float(computation.margin_bps), "floor_bps": float(floor), "gap_bps": float(gap)},
                dedupe_key=f"{AlertType.MARGIN_EROSION.value}:{today}",
            )
            if alert:
                created.append(alert)

    # ---- stalled_deal ----------------------------------------------------------
    if quotation.status not in TERMINAL_STATES:
        policy = get_active_policy(db)
        stalled_after = policy.stalled_after_days
        days_inactive = (datetime.now(timezone.utc) - quotation.last_activity_at).days
        if days_inactive > stalled_after:
            alert = _upsert_alert(
                db,
                quotation,
                alert_type=AlertType.STALLED_DEAL.value,
                severity=AlertSeverity.HIGH.value if days_inactive > stalled_after * 2 else AlertSeverity.MEDIUM.value,
                title="Deal has gone quiet",
                detail=(
                    f"No activity for {days_inactive} days (policy flags anything over "
                    f"{stalled_after}); still in '{quotation.status}'"
                ),
                metrics={"days_inactive": float(days_inactive), "stalled_after_days": float(stalled_after)},
                dedupe_key=f"{AlertType.STALLED_DEAL.value}:{today}",
            )
            if alert:
                created.append(alert)

    # ---- delivery_slippage ---------------------------------------------------
    now = datetime.now(timezone.utc)
    slipped = db.scalars(
        select(Backorder).where(
            Backorder.quotation_id == quotation.id,
            Backorder.status == "open",
            Backorder.expected_restock_at.is_not(None),
            Backorder.expected_restock_at < now,
        )
    ).all()
    if slipped:
        worst = max((now - b.expected_restock_at).days for b in slipped)
        alert = _upsert_alert(
            db,
            quotation,
            alert_type=AlertType.DELIVERY_SLIPPAGE.value,
            severity=AlertSeverity.HIGH.value if worst >= 7 else AlertSeverity.MEDIUM.value,
            title="Backorder past its restock date",
            detail=(
                f"{len(slipped)} backordered line(s) are past the expected restock date "
                f"by up to {worst} day(s)"
            ),
            metrics={"backordered_lines": float(len(slipped)), "days_late": float(worst)},
            dedupe_key=f"{AlertType.DELIVERY_SLIPPAGE.value}:{today}",
        )
        if alert:
            created.append(alert)

    # ---- refresh flags on the read model ------------------------------------
    if metric is not None:
        db.flush()  # make the just-added alerts visible to the query below
        open_types = db.scalars(
            select(DealAlert.alert_type)
            .where(DealAlert.quotation_id == quotation.id, DealAlert.acknowledged.is_(False))
            .distinct()
        ).all()
        metric.flags = sorted(set(open_types))

    return created


def self_pct(bps: float) -> str:
    return f"{bps / 100:.1f}%"


def run_alert_sweep(db: Session) -> int:
    """Scheduled sweep over every non-terminal quotation in the current org."""
    quotations = db.scalars(
        select(Quotation).where(Quotation.status.not_in(TERMINAL_STATES))
    ).all()
    total = 0
    for quotation in quotations:
        try:
            created = evaluate_quotation_alerts(db, quotation)
            db.commit()
            total += len(created)
        except Exception:
            logger.exception("alert sweep failed for quotation %s", quotation.id)
            db.rollback()
    return total


def recompute_days_inactive(db: Session) -> int:
    now = datetime.now(timezone.utc)
    metrics = db.scalars(select(DealMetric)).all()
    for metric in metrics:
        metric.days_inactive = max(0, (now - metric.last_activity_at).days)
    db.commit()
    return len(metrics)


def rebuild_rep_stats(db: Session) -> int:
    """Full recompute of `rep_discount_stats` from confirmed+ quotations."""
    won = db.scalars(
        select(Quotation).where(
            Quotation.status.in_(
                [
                    QuoteStatus.CONFIRMED.value,
                    QuoteStatus.FULFILLING.value,
                    QuoteStatus.INVOICED.value,
                    QuoteStatus.PAID.value,
                ]
            )
        )
    ).all()
    by_rep: dict[int, list[float]] = {}
    for quotation in won:
        try:
            eff = compute_quotation(db, quotation).effective_discount_bps
        except Exception:
            continue
        by_rep.setdefault(quotation.owner_rep_id, []).append(float(eff))

    for existing in db.scalars(select(RepDiscountStats)).all():
        db.delete(existing)
    db.flush()

    for rep_id, samples in by_rep.items():
        n = len(samples)
        mean = sum(samples) / n
        m2 = sum((x - mean) ** 2 for x in samples)
        db.add(RepDiscountStats(rep_id=rep_id, sample_count=n, mean_bps=mean, m2=m2))
    db.commit()
    return len(by_rep)


# ----------------------------------------------------------------------- serving


def _alert_to_read(db: Session, alert: DealAlert, ref_cache: dict[int, str]) -> AlertRead:
    reference = ref_cache.get(alert.quotation_id)
    if reference is None:
        quotation = db.get(Quotation, alert.quotation_id)
        reference = quotation.reference if quotation else ""
        ref_cache[alert.quotation_id] = reference
    return AlertRead(
        id=alert.id,
        alert_type=alert.alert_type,
        quotation_id=alert.quotation_id,
        quotation_reference=reference,
        severity=alert.severity,
        title=alert.title,
        detail=alert.detail,
        metrics={k: float(v) for k, v in (alert.metrics or {}).items()},
        acknowledged=alert.acknowledged,
        created_at=alert.created_at,
    )


def list_deal_health(
    db: Session, params: PageParams, owner_rep_id: int | None, stage: str | None
) -> tuple[list[DealHealthRow], int]:
    stmt = select(DealMetric)
    if owner_rep_id is not None:
        stmt = stmt.where(DealMetric.owner_rep_id == owner_rep_id)
    if stage:
        stmt = stmt.where(DealMetric.stage == stage)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DealMetric.last_activity_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()

    quotations = {
        q.id: q
        for q in db.scalars(select(Quotation).where(Quotation.id.in_([r.quotation_id for r in rows] or [0])))
    }
    customers = {
        c.id: c for c in db.scalars(select(Customer).where(Customer.id.in_([r.customer_id for r in rows] or [0])))
    }
    reps = {u.id: u for u in db.scalars(select(User).where(User.id.in_([r.owner_rep_id for r in rows] or [0])))}
    now = datetime.now(timezone.utc)

    out = []
    for r in rows:
        quotation = quotations.get(r.quotation_id)
        out.append(
            DealHealthRow(
                quotation_id=r.quotation_id,
                reference=quotation.reference if quotation else "",
                customer_name=customers[r.customer_id].name if r.customer_id in customers else "",
                owner_rep_name=reps[r.owner_rep_id].full_name if r.owner_rep_id in reps else "",
                stage=r.stage,
                total_minor=r.total_minor,
                margin_bps=max(0, r.margin_bps),
                risk_score=r.risk_score,
                days_inactive=max(0, (now - r.last_activity_at).days),
                flags=list(r.flags or []),
                last_activity_at=r.last_activity_at,
                currency=quotation.currency if quotation else "INR",
            )
        )
    return out, total


def list_alerts(
    db: Session, params: PageParams, alert_type: str | None, acknowledged: bool | None
) -> tuple[list[AlertRead], int]:
    stmt = select(DealAlert)
    if alert_type:
        stmt = stmt.where(DealAlert.alert_type == alert_type)
    if acknowledged is not None:
        stmt = stmt.where(DealAlert.acknowledged.is_(acknowledged))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DealAlert.created_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()
    cache: dict[int, str] = {}
    return [_alert_to_read(db, a, cache) for a in rows], total


def get_alert_or_404(db: Session, alert_id: int) -> DealAlert:
    alert = db.get(DealAlert, alert_id)
    if alert is None:
        raise NotFoundException("Alert not found")
    return alert


def nudge_alert(db: Session, alert: DealAlert, actor: User) -> AlertRead:
    quotation = db.get(Quotation, alert.quotation_id)
    if quotation is None:
        raise NotFoundException("Quotation not found")
    from app.events.service import record_event

    record_event(
        db,
        quotation,
        "deal.alert_nudged",
        actor,
        summary=f"{actor.full_name} nudged the owner ({_rep_name(db, quotation.owner_rep_id)}) about: {alert.title}.",
        payload={"alert_id": alert.id, "alert_type": alert.alert_type, "owner_rep_id": quotation.owner_rep_id},
    )
    db.commit()
    cache: dict[int, str] = {}
    return _alert_to_read(db, alert, cache)


def _rep_name(db: Session, rep_id: int) -> str:
    rep = db.get(User, rep_id)
    return rep.full_name if rep else "the owner"


def acknowledge_alert(db: Session, alert: DealAlert) -> AlertRead:
    alert.acknowledged = True
    metric = db.get(DealMetric, alert.quotation_id)
    if metric is not None:
        open_types = db.scalars(
            select(DealAlert.alert_type)
            .where(DealAlert.quotation_id == alert.quotation_id, DealAlert.acknowledged.is_(False))
            .distinct()
        ).all()
        metric.flags = sorted(set(open_types))
    db.commit()
    cache: dict[int, str] = {}
    return _alert_to_read(db, alert, cache)


# ------------------------------------------------------------------ reports


def sales_report(
    db: Session,
    params: PageParams,
    *,
    period: str | None,
    rep_id: int | None,
    approval_status: str | None,
    category_id: int | None,
) -> tuple[list[SalesReportRow], int]:
    stmt = select(Quotation)
    if rep_id is not None:
        stmt = stmt.where(Quotation.owner_rep_id == rep_id)
    if approval_status:
        stmt = stmt.where(Quotation.status == approval_status)
    if period:
        stmt = stmt.where(func.to_char(Quotation.created_at, "YYYY-MM") == period)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Quotation.created_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()

    reps = {u.id: u for u in db.scalars(select(User).where(User.id.in_([q.owner_rep_id for q in rows] or [0])))}
    out: list[SalesReportRow] = []
    for q in rows:
        if category_id is not None and not any(line.category_id == category_id for line in q.lines):
            continue
        try:
            computation = compute_quotation(db, q)
            total_minor, margin_bps = computation.total_minor, max(0, computation.margin_bps)
        except Exception:
            total_minor, margin_bps = 0, 0
        out.append(
            SalesReportRow(
                period=q.created_at.strftime("%Y-%m"),
                quotation_id=q.id,
                reference=q.reference,
                customer_name=q.customer.name,
                owner_rep_name=reps[q.owner_rep_id].full_name if q.owner_rep_id in reps else "",
                status=q.status,
                total_minor=total_minor,
                margin_bps=margin_bps,
                currency=q.currency,
            )
        )
    return out, total


# --------------------------------------------------------------- dashboard summary


def _money(db: Session, statuses: set[str]) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(DealMetric.total_minor), 0)).where(DealMetric.stage.in_(statuses))
        )
        or 0
    )


def _count(db: Session, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(DealMetric).where(*conditions)) or 0)


def dashboard_summary(db: Session, user: User) -> DashboardSummary:
    dtype = DashboardType(user.role.dashboard_type) if user.role else DashboardType.GENERIC
    now = datetime.now(timezone.utc)

    open_states = {
        QuoteStatus.DRAFT.value,
        QuoteStatus.PENDING_L1.value,
        QuoteStatus.PENDING_L2.value,
        QuoteStatus.APPROVED.value,
        QuoteStatus.SENT.value,
        QuoteStatus.UNDER_NEGOTIATION.value,
    }
    won_states = {
        QuoteStatus.CONFIRMED.value,
        QuoteStatus.FULFILLING.value,
        QuoteStatus.INVOICED.value,
        QuoteStatus.PAID.value,
    }

    stats: list[DashboardStat] = []

    def stat(key, label, value, unit, hint=None):
        stats.append(DashboardStat(key=key, label=label, value=int(value), unit=unit, hint=hint))

    pending = _count(db, DealMetric.stage.in_([QuoteStatus.PENDING_L1.value, QuoteStatus.PENDING_L2.value]))
    open_pipeline = _money(db, open_states)
    won_value = _money(db, won_states)
    stalled = _count(db, DealMetric.flags.any(AlertType.STALLED_DEAL.value))  # type: ignore[attr-defined]
    open_alerts = int(db.scalar(select(func.count()).select_from(DealAlert).where(DealAlert.acknowledged.is_(False))) or 0)

    if dtype == DashboardType.SUPER_ADMIN:
        team_size = int(db.scalar(select(func.count()).select_from(User)) or 0)
        stat("open_pipeline", "Open pipeline", open_pipeline, "currency")
        stat("won_value", "Won value", won_value, "currency")
        stat("pending_approvals", "Awaiting approval", pending, "count")
        stat("open_alerts", "Open alerts", open_alerts, "count", hint=f"{team_size} team members")
    elif dtype == DashboardType.SALES_MANAGER:
        stat("pending_approvals", "Awaiting your approval", pending, "count")
        stat("open_pipeline", "Open pipeline", open_pipeline, "currency")
        stat("stalled_deals", "Stalled deals", stalled, "count")
        stat("open_alerts", "Open alerts", open_alerts, "count")
    elif dtype == DashboardType.FINANCE_OPS:
        from app.billing.models import Invoice

        unpaid = int(
            db.scalar(
                select(func.coalesce(func.sum(Invoice.total_minor - Invoice.paid_minor), 0)).where(
                    Invoice.status.in_(["issued"])
                )
            )
            or 0
        )
        stat("outstanding_ar", "Outstanding receivables", unpaid, "currency")
        stat("won_value", "Confirmed value", won_value, "currency")
        stat("pending_l2", "Awaiting L2 sign-off", _count(db, DealMetric.stage == QuoteStatus.PENDING_L2.value), "count")
        stat("open_alerts", "Open alerts", open_alerts, "count")
    else:  # GENERIC
        stat("my_open", "Open deals", _count(db, DealMetric.stage.in_(list(open_states))), "count")
        stat("open_pipeline", "Open pipeline", open_pipeline, "currency")
        stat("open_alerts", "Open alerts", open_alerts, "count")

    alert_rows = db.scalars(
        select(DealAlert).where(DealAlert.acknowledged.is_(False)).order_by(DealAlert.created_at.desc()).limit(10)
    ).all()
    cache: dict[int, str] = {}
    return DashboardSummary(
        dashboard_type=dtype,
        generated_at=now,
        currency="INR",
        stats=stats,
        alerts=[_alert_to_read(db, a, cache) for a in alert_rows],
    )
