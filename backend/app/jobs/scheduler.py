"""APScheduler background jobs — `BACKEND_PHASE_3.md` Task 7.

Every job runs once per organization (it pins the tenant context, then calls the
same service function an HTTP request would). Every job is wrapped so an exception
logs and never kills the scheduler. `POST /admin/jobs/{name}/run` triggers any job
on demand for the demo.

If Task 7 were cut, the app still works: `days_inactive` is computed on read and
the manual trigger endpoint stays.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.tenant_context import set_current_org
from app.db.session import SessionLocal
from app.organizations.models import Organization

logger = logging.getLogger(__name__)

_scheduler = None


# --------------------------------------------------------------------------- jobs


def _job_stalled_deal_sweep(db: Session) -> int:
    from app.dashboard.service import run_alert_sweep

    return run_alert_sweep(db)


def _job_days_inactive_refresh(db: Session) -> int:
    from app.dashboard.service import recompute_days_inactive

    return recompute_days_inactive(db)


def _job_rep_stats_refresh(db: Session) -> int:
    from app.dashboard.service import rebuild_rep_stats

    return rebuild_rep_stats(db)


def _job_affinity_rebuild(db: Session) -> int:
    from app.affinity.service import rebuild_affinity

    return rebuild_affinity(db)


def _job_subscription_invoice_run(db: Session) -> int:
    from app.billing.service import run_subscription_invoice_job

    return run_subscription_invoice_job(db)


def _job_reservation_expiry(db: Session) -> int:
    from app.core.enums import ReservationStatus
    from app.fulfillment.models import StockReservation
    from app.warehouses.models import Stock

    now = datetime.now(timezone.utc)
    expired = db.scalars(
        select(StockReservation).where(
            StockReservation.status == ReservationStatus.HELD.value,
            StockReservation.expires_at.is_not(None),
            StockReservation.expires_at < now,
        )
    ).all()
    for reservation in expired:
        stock = db.scalar(
            select(Stock).where(
                Stock.product_id == reservation.product_id,
                Stock.warehouse_id == reservation.warehouse_id,
            )
        )
        if stock is not None:
            stock.reserved = max(0, stock.reserved - reservation.quantity)
        reservation.status = ReservationStatus.RELEASED.value
    db.commit()
    return len(expired)


JOBS = {
    "stalled-deal-sweep": _job_stalled_deal_sweep,
    "days-inactive-refresh": _job_days_inactive_refresh,
    "rep-stats-refresh": _job_rep_stats_refresh,
    "affinity-rebuild": _job_affinity_rebuild,
    "subscription-invoice-run": _job_subscription_invoice_run,
    "reservation-expiry": _job_reservation_expiry,
}

_SCHEDULE_MINUTES = {
    "stalled-deal-sweep": 5,
    "days-inactive-refresh": 10,
    "rep-stats-refresh": 10,
    "affinity-rebuild": 15,
    "subscription-invoice-run": 5,
    "reservation-expiry": 2,
}


def run_job(name: str) -> dict:
    """Run one job across every organization. Used by the scheduler tick and by
    `POST /admin/jobs/{name}/run`."""
    if name not in JOBS:
        raise KeyError(name)
    fn = JOBS[name]
    per_org: dict[int, object] = {}
    with SessionLocal() as db:
        orgs = db.scalars(select(Organization).where(Organization.is_active.is_(True))).all()
        for org in orgs:
            set_current_org(db, org.id)
            try:
                per_org[org.id] = fn(db)
            except Exception:
                logger.exception("job %s failed for org %s", name, org.id)
                db.rollback()
                per_org[org.id] = "error"
    return {"job": name, "ran_at": datetime.now(timezone.utc).isoformat(), "per_org": per_org}


def _tick(name: str) -> None:
    try:
        result = run_job(name)
        logger.info("scheduled job %s: %s", name, result["per_org"])
    except Exception:
        logger.exception("scheduled job %s crashed", name)


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled or _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception:
        logger.warning("APScheduler not installed — background jobs disabled")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    for name, minutes in _SCHEDULE_MINUTES.items():
        _scheduler.add_job(
            _tick,
            "interval",
            minutes=minutes,
            args=[name],
            id=name,
            max_instances=1,
            coalesce=True,
        )
    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_SCHEDULE_MINUTES))


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
