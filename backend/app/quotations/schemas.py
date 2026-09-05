"""Shapes for `API_CONTRACT.md` §3 and §4.4–§4.5. Phase 1 declares these so the stub
pass (Task 0) produces a complete, final `openapi.json`; Phase 2 fills in the logic
behind the routes in `router.py` without changing a single field here.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.core.types import Bps, MoneyMinor

LineType = Literal["one_time", "subscription"]
ApprovalLevel = Literal["l1_sales_manager", "l2_finance"]


# ---- Decision trace (DECISION_ENGINE.md §4) --------------------------------------

class DecisionTraceLine(BaseModel):
    line_id: int | None
    product_name: str
    category_name: str
    discount_bps: Bps
    tier_ceiling_bps: Bps
    category_ceiling_bps: Bps
    effective_ceiling_bps: Bps
    ceiling_source: Literal["tier", "category"]
    overage_bps: int
    weight_bps: int
    weighted_overage_bps: int
    margin_bps: int
    margin_floor_bps: Bps
    margin_shortfall_bps: int
    verdict: Literal["within_limit", "over_limit", "hard_breach"]


class DecisionTraceComponent(BaseModel):
    key: Literal["blended", "worst", "value", "margin"]
    label: str
    raw_value: int
    normalised: int
    weight_bps: int
    contribution: int
    explanation: str


class DecisionTraceRule(BaseModel):
    code: str
    severity: Literal["info", "warn", "block"]
    message: str
    line_id: int | None


class DecisionTrace(BaseModel):
    policy_version: int
    customer_tier: str
    tier_ceiling_bps: Bps
    lines: list[DecisionTraceLine]
    components: list[DecisionTraceComponent]
    risk_score: int
    thresholds: dict[str, int]
    rules_fired: list[DecisionTraceRule]
    required_approvals: list[str]
    outcome: Literal["auto_approved", "l1_required", "l1_l2_required", "blocked"]
    summary: str


# ---- Quote lines & computation ----------------------------------------------------

class QuoteLineRead(BaseModel):
    id: int
    quotation_id: int
    product_id: int
    product_name: str
    variant_id: int | None
    category_id: int
    line_type: LineType
    subscription_plan_id: int | None
    quantity: int
    unit_price_minor: MoneyMinor
    discount_bps: Bps
    net_minor: MoneyMinor
    tax_minor: MoneyMinor
    cost_minor: MoneyMinor
    margin_minor: int
    margin_bps: int
    ceiling_bps: Bps
    overage_bps: int
    added_from_suggestion: bool


class QuoteComputation(BaseModel):
    gross_minor: MoneyMinor
    discount_total_minor: MoneyMinor
    net_minor: MoneyMinor
    tax_minor: MoneyMinor
    total_minor: MoneyMinor
    cost_total_minor: MoneyMinor
    margin_minor: int
    margin_bps: int
    effective_discount_bps: Bps
    blended_overage_bps: int
    worst_overage_bps: int
    risk_score: int
    required_approvals: list[ApprovalLevel]
    trace: DecisionTrace
    currency: str


class QuotationRead(BaseModel):
    id: int
    reference: str
    order_number: str | None
    customer_id: int
    customer_name: str
    customer_tier: Literal["bronze", "silver", "gold"]
    owner_rep_id: int
    owner_rep_name: str
    status: str
    version: int
    policy_version: int
    currency: str
    valid_until: date | None
    lines: list[QuoteLineRead]
    computation: QuoteComputation
    fulfillment_status: str | None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime


class QuoteEventRead(BaseModel):
    id: int
    quotation_id: int
    event_type: str
    actor_type: Literal["internal", "customer", "system"]
    actor_id: int | None
    actor_name: str
    summary: str
    payload: dict
    created_at: datetime


class SuggestionRead(BaseModel):
    product_id: int
    product_name: str
    sku: str
    list_price_minor: MoneyMinor
    suggested_quantity: int
    score: int
    lift: float  # the one place a float is acceptable — a ratio, not money
    support_count: int
    margin_delta_minor: int
    margin_delta_bps: int
    is_promoted: bool
    reason: str
    currency: str


# ---- Request bodies ---------------------------------------------------------------

class QuotationCreate(BaseModel):
    customer_id: int
    valid_until: date | None = None


class QuotationUpdate(BaseModel):
    expected_version: int
    order_discount_bps: Bps | None = None
    valid_until: date | None = None


class QuoteLineCreate(BaseModel):
    expected_version: int
    product_id: int
    variant_id: int | None = None
    quantity: int
    discount_bps: Bps
    from_suggestion: bool = False


class QuoteLineUpdate(BaseModel):
    expected_version: int
    quantity: int | None = None
    discount_bps: Bps | None = None


class PreviewLine(BaseModel):
    product_id: int
    variant_id: int | None
    quantity: int
    discount_bps: Bps


class PreviewRequest(BaseModel):
    lines: list[PreviewLine]
    order_discount_bps: Bps


class SubmitRequest(BaseModel):
    expected_version: int


class TransitionRequest(BaseModel):
    expected_version: int
    to_status: str
    reason: str | None = None
