from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.types import Bps, MoneyMinor

CustomerTier = Literal["bronze", "silver", "gold"]


class PolicyWeights(BaseModel):
    w_blended_bps: Bps = 4500
    w_worst_bps: Bps = 3500
    w_value_bps: Bps = 1000
    w_margin_bps: Bps = 1000
    scale_overage_bps: Bps = 1000
    value_reference_minor: MoneyMinor = 50_000_000
    margin_scale_bps: Bps = 500


class PolicyThresholds(BaseModel):
    t1_l1_required: int = Field(default=20, ge=0, le=100)
    t2_l2_required: int = Field(default=55, ge=0, le=100)
    hard_breach_bps: Bps = 500
    finance_value_floor_minor: MoneyMinor = 100_000_000


class PolicyUpsell(BaseModel):
    min_margin_bps: Bps = 0
    w_lift_bps: Bps = 0
    w_margin_bps: Bps = 0
    w_promo_bps: Bps = 0


class PolicyAnomaly(BaseModel):
    # Not a percentage-of-a-whole — a scaling factor expressed in bps (20000 == 2.0σ),
    # so unlike other *_bps fields it is intentionally allowed past 10000.
    sigma_multiplier_bps: int = Field(default=20000, ge=0)
    min_sample_size: int = Field(default=5, ge=1)


class TierCeilingInput(BaseModel):
    tier: CustomerTier
    ceiling_bps: Bps


class CategoryCeilingInput(BaseModel):
    category_id: int
    ceiling_bps: Bps
    margin_floor_bps: Bps


class TierCeilingRead(BaseModel):
    tier: str
    ceiling_bps: Bps


class CategoryCeilingRead(BaseModel):
    category_id: int
    category_name: str
    ceiling_bps: Bps
    margin_floor_bps: Bps


class PolicyCreate(BaseModel):
    """Always creates a new draft version — see `POST /policies` in `API_CONTRACT.md` §4.3."""

    tier_ceilings: list[TierCeilingInput]
    category_ceilings: list[CategoryCeilingInput]
    weights: PolicyWeights = PolicyWeights()
    thresholds: PolicyThresholds = PolicyThresholds()
    upsell: PolicyUpsell = PolicyUpsell()
    anomaly: PolicyAnomaly = PolicyAnomaly()
    stalled_after_days: int = Field(default=14, ge=1)


class PolicyRead(BaseModel):
    id: int
    version: int
    is_active: bool
    tier_ceilings: list[TierCeilingRead]
    category_ceilings: list[CategoryCeilingRead]
    weights: PolicyWeights
    thresholds: PolicyThresholds
    upsell: PolicyUpsell
    anomaly: PolicyAnomaly
    stalled_after_days: int
    created_at: datetime
    activated_at: datetime | None

    @classmethod
    def from_model(cls, policy) -> "PolicyRead":
        return cls(
            id=policy.id,
            version=policy.version,
            is_active=policy.is_active,
            tier_ceilings=[
                TierCeilingRead(tier=tc.tier, ceiling_bps=tc.ceiling_bps) for tc in policy.tier_ceilings
            ],
            category_ceilings=[
                CategoryCeilingRead(
                    category_id=cc.category_id,
                    category_name=cc.category.name,
                    ceiling_bps=cc.ceiling_bps,
                    margin_floor_bps=cc.margin_floor_bps,
                )
                for cc in policy.category_ceilings
            ],
            weights=PolicyWeights(**policy.weights),
            thresholds=PolicyThresholds(**policy.thresholds),
            upsell=PolicyUpsell(**policy.upsell),
            anomaly=PolicyAnomaly(**policy.anomaly),
            stalled_after_days=policy.stalled_after_days,
            created_at=policy.created_at,
            activated_at=policy.activated_at,
        )
