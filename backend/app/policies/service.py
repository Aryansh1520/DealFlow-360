"""Policy persistence and the frozen snapshot the (Phase 2) engine reads.

`get_active_policy` returns a `PolicySnapshot` — a frozen dataclass, never an ORM
object, so the engine cannot accidentally lazy-load through a detached session.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.policies.models import DiscountPolicy, PolicyCategoryCeiling, PolicyTierCeiling


@dataclass(frozen=True)
class PolicySnapshot:
    id: int
    version: int
    weights: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)
    upsell: dict = field(default_factory=dict)
    anomaly: dict = field(default_factory=dict)
    stalled_after_days: int = 14
    tier_ceilings: dict[str, int] = field(default_factory=dict)
    # category_id -> {"ceiling_bps": int, "margin_floor_bps": int}
    category_ceilings: dict[int, dict[str, int]] = field(default_factory=dict)


def _to_snapshot(policy: DiscountPolicy) -> PolicySnapshot:
    return PolicySnapshot(
        id=policy.id,
        version=policy.version,
        weights=dict(policy.weights),
        thresholds=dict(policy.thresholds),
        upsell=dict(policy.upsell),
        anomaly=dict(policy.anomaly),
        stalled_after_days=policy.stalled_after_days,
        tier_ceilings={tc.tier: tc.ceiling_bps for tc in policy.tier_ceilings},
        category_ceilings={
            cc.category_id: {"ceiling_bps": cc.ceiling_bps, "margin_floor_bps": cc.margin_floor_bps}
            for cc in policy.category_ceilings
        },
    )


def get_active_policy(db: Session) -> PolicySnapshot:
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)))
    if policy is None:
        raise NotFoundException("No active discount policy")
    return _to_snapshot(policy)


def get_policy_snapshot_by_version(db: Session, version: int) -> PolicySnapshot:
    """A quotation stores the `policy_version` it was evaluated under and keeps it for
    its whole lifecycle — activating a new policy must not silently reprice a quote
    already sitting in an approval queue. See `DECISION_ENGINE.md` §8."""
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.version == version))
    if policy is None:
        raise NotFoundException(f"Policy version {version} not found")
    return _to_snapshot(policy)


def get_next_version(db: Session) -> int:
    max_version = db.scalar(select(DiscountPolicy.version).order_by(DiscountPolicy.version.desc()))
    return (max_version or 0) + 1


def create_policy(
    db: Session,
    *,
    tier_ceilings: list[dict],
    category_ceilings: list[dict],
    weights: dict,
    thresholds: dict,
    upsell: dict,
    anomaly: dict,
    stalled_after_days: int,
) -> DiscountPolicy:
    """Always creates a new draft version — an existing policy row is never updated
    after activation. See `BACKEND_PHASE_1.md` Task 7."""
    policy = DiscountPolicy(
        version=get_next_version(db),
        is_active=False,
        weights=weights,
        thresholds=thresholds,
        upsell=upsell,
        anomaly=anomaly,
        stalled_after_days=stalled_after_days,
    )
    policy.tier_ceilings = [
        PolicyTierCeiling(tier=tc["tier"], ceiling_bps=tc["ceiling_bps"]) for tc in tier_ceilings
    ]
    policy.category_ceilings = [
        PolicyCategoryCeiling(
            category_id=cc["category_id"],
            ceiling_bps=cc["ceiling_bps"],
            margin_floor_bps=cc["margin_floor_bps"],
        )
        for cc in category_ceilings
    ]
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def activate_policy(db: Session, policy: DiscountPolicy) -> DiscountPolicy:
    """One transaction: deactivate whatever is currently active, then activate this
    version. The partial unique index on `discount_policies.is_active` is the backstop
    — this is the code path that keeps it satisfied."""
    db.execute(update(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)).values(is_active=False))
    policy.is_active = True
    policy.activated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy
