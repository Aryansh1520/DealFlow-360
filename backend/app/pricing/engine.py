"""The pricing & risk engine — `DECISION_ENGINE.md` in code.

Pure function, zero I/O: `evaluate()` takes only its arguments and returns a
`QuoteComputation`. This is what makes preview and a saved-quote read byte-identical —
both call this same function with the same inputs. No `db`, no `Session`, no
`datetime.now()`, no settings lookup — everything arrives as an argument.

`app/pricing/service.py::build_evaluation_inputs` is the only place that touches the
DB to build the `EvaluatedLineInput` list this function consumes.
"""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.core.money import apply_bps, distribute_largest_remainder, to_bps
from app.policies.service import PolicySnapshot
from app.pricing.trace import build_rules_fired, build_summary
from app.quotations.schemas import (
    DecisionTrace,
    DecisionTraceComponent,
    DecisionTraceLine,
    QuoteComputation,
)


@dataclass(frozen=True)
class EvaluatedLineInput:
    """One quote line, already price-resolved. Frozen — the engine never mutates it."""

    line_id: int | None  # None in preview mode
    product_id: int
    product_name: str
    variant_id: int | None
    category_id: int
    category_name: str
    line_type: str
    subscription_plan_id: int | None
    quantity: int
    unit_price_minor: int
    cost_price_minor: int
    discount_bps: int  # rep-entered, line-level only — the order discount is separate
    added_from_suggestion: bool = False


@dataclass(frozen=True)
class _ComputedLine:
    input: EvaluatedLineInput
    gross_minor: int
    combined_discount_minor: int
    combined_discount_bps: int
    net_minor: int
    cost_minor: int
    margin_minor: int
    margin_bps: int
    tax_minor: int
    tier_ceiling_bps: int
    category_ceiling_bps: int
    effective_ceiling_bps: int
    ceiling_source: str
    overage_bps: int
    margin_floor_bps: int
    margin_shortfall_bps: int
    weight: Decimal


def _floor_bps(numerator: int, denominator: int) -> int:
    """`floor(numerator * 10000 / denominator)`, unlike `to_bps` which truncates
    toward zero. Matters for `margin_bps_i` per `DECISION_ENGINE.md` §3 step 3, where
    a negative margin must floor toward -infinity, not zero."""
    if denominator == 0:
        return 0
    return int((Decimal(numerator) * Decimal(10000) / Decimal(denominator)).quantize(0, rounding=ROUND_FLOOR))


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(0, rounding=ROUND_HALF_UP))


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _empty_computation(policy: PolicySnapshot, customer_tier: str, currency: str) -> QuoteComputation:
    tier_ceiling = policy.tier_ceilings.get(customer_tier, 0)
    trace = DecisionTrace(
        policy_version=policy.version,
        customer_tier=customer_tier,
        tier_ceiling_bps=tier_ceiling,
        lines=[],
        components=[],
        risk_score=0,
        thresholds={
            "t1": policy.thresholds.get("t1_l1_required", 0),
            "t2": policy.thresholds.get("t2_l2_required", 0),
        },
        rules_fired=[],
        required_approvals=[],
        outcome="auto_approved",
        summary="No lines on this quotation yet.",
    )
    return QuoteComputation(
        gross_minor=0,
        discount_total_minor=0,
        net_minor=0,
        tax_minor=0,
        total_minor=0,
        cost_total_minor=0,
        margin_minor=0,
        margin_bps=0,
        effective_discount_bps=0,
        blended_overage_bps=0,
        worst_overage_bps=0,
        risk_score=0,
        required_approvals=[],
        trace=trace,
        currency=currency,
    )


@dataclass(frozen=True)
class LineComputed:
    """Public, per-line money detail — what `QuoteLineRead` needs beyond what
    `DecisionTraceLine` already carries. Built by the same `_build_computed_lines`
    the trace is built from, so there is exactly one source of truth for the maths;
    `evaluate()` itself still returns only `QuoteComputation`, per
    `BACKEND_PHASE_2.md` Task 1's signature."""

    line_id: int | None
    product_id: int
    product_name: str
    variant_id: int | None
    category_id: int
    line_type: str
    subscription_plan_id: int | None
    quantity: int
    unit_price_minor: int
    discount_bps: int  # raw, line-level only — echoes the input
    net_minor: int
    tax_minor: int
    cost_minor: int
    margin_minor: int
    margin_bps: int
    ceiling_bps: int
    overage_bps: int
    added_from_suggestion: bool


def _build_computed_lines(
    lines: list[EvaluatedLineInput],
    policy: PolicySnapshot,
    customer_tier: str,
    order_discount_bps: int,
    tax_bps_by_product: dict[int, int],
) -> list[_ComputedLine]:
    tier_ceiling = policy.tier_ceilings.get(customer_tier, 0)

    # ---- Step: push the order-level discount down to lines, proportionally to
    # gross value, so there is exactly one discount concept in the maths from here on.
    gross_list = [line.quantity * line.unit_price_minor for line in lines]
    gross_total = sum(gross_list)
    order_discount_total = apply_bps(gross_total, order_discount_bps) if gross_total else 0
    order_shares = distribute_largest_remainder(order_discount_total, gross_list)

    computed: list[_ComputedLine] = []
    net_total = 0
    for line, gross, order_share in zip(lines, gross_list, order_shares):
        line_discount_minor = apply_bps(gross, line.discount_bps)
        combined_discount_minor = min(gross, line_discount_minor + order_share)
        combined_discount_bps = to_bps(combined_discount_minor, gross) if gross else 0
        net_minor = gross - combined_discount_minor
        net_total += net_minor

        cost_minor = line.quantity * line.cost_price_minor
        margin_minor = net_minor - cost_minor
        if net_minor > 0:
            margin_bps = _floor_bps(margin_minor, net_minor)
        elif margin_minor < 0:
            # Net revenue is zero (a total discount) but the goods cost money — this
            # is below cost. Report -100% so Hard Gate 1 (`margin_bps < 0`) fires
            # instead of being masked by the divide-by-zero guard.
            margin_bps = -10000
        else:
            margin_bps = 0

        cat_ceiling = policy.category_ceilings.get(line.category_id, {})
        category_ceiling_bps = cat_ceiling.get("ceiling_bps", 0)
        margin_floor_bps = cat_ceiling.get("margin_floor_bps", 0)
        effective_ceiling_bps = min(tier_ceiling, category_ceiling_bps)
        ceiling_source = "tier" if tier_ceiling <= category_ceiling_bps else "category"
        overage_bps = max(0, combined_discount_bps - effective_ceiling_bps)
        margin_shortfall_bps = max(0, margin_floor_bps - margin_bps)

        tax_minor = apply_bps(net_minor, tax_bps_by_product.get(line.product_id, 0))

        computed.append(
            _ComputedLine(
                input=line,
                gross_minor=gross,
                combined_discount_minor=combined_discount_minor,
                combined_discount_bps=combined_discount_bps,
                net_minor=net_minor,
                cost_minor=cost_minor,
                margin_minor=margin_minor,
                margin_bps=margin_bps,
                tax_minor=tax_minor,
                tier_ceiling_bps=tier_ceiling,
                category_ceiling_bps=category_ceiling_bps,
                effective_ceiling_bps=effective_ceiling_bps,
                ceiling_source=ceiling_source,
                overage_bps=overage_bps,
                margin_floor_bps=margin_floor_bps,
                margin_shortfall_bps=margin_shortfall_bps,
                weight=Decimal(0),  # filled in below, once net_total is known
            )
        )

    # Revenue-weight each line. When a total discount collapses net revenue to zero,
    # net-weighting would zero every weight and silently neuter the blended-overage,
    # value and margin risk components — so fall back to gross-weighting, which is
    # never zero for a real quote. (Hard Gate 1 still blocks a genuine below-cost
    # deal regardless; this keeps the score meaningful for the near-total case.)
    gross_total_for_weight = sum(cl.gross_minor for cl in computed)
    weighted: list[_ComputedLine] = []
    for cl in computed:
        if net_total > 0:
            weight = Decimal(cl.net_minor) / Decimal(net_total)
        elif gross_total_for_weight > 0:
            weight = Decimal(cl.gross_minor) / Decimal(gross_total_for_weight)
        else:
            weight = Decimal(0)
        weighted.append(
            _ComputedLine(
                **{**cl.__dict__, "weight": weight}
            )
        )
    return weighted


def line_details(
    lines: list[EvaluatedLineInput],
    policy: PolicySnapshot,
    customer_tier: str,
    order_discount_bps: int,
    tax_bps_by_product: dict[int, int] | None = None,
) -> list[LineComputed]:
    """Per-line money detail for `QuoteLineRead` — quantity, discount, net, tax,
    cost, margin, effective ceiling and overage. Uses the exact same per-line maths
    `evaluate()` uses (via `_build_computed_lines`), so a saved quote's lines and its
    `computation.trace.lines` never disagree."""
    computed = _build_computed_lines(lines, policy, customer_tier, order_discount_bps, tax_bps_by_product or {})
    return [
        LineComputed(
            line_id=cl.input.line_id,
            product_id=cl.input.product_id,
            product_name=cl.input.product_name,
            variant_id=cl.input.variant_id,
            category_id=cl.input.category_id,
            line_type=cl.input.line_type,
            subscription_plan_id=cl.input.subscription_plan_id,
            quantity=cl.input.quantity,
            unit_price_minor=cl.input.unit_price_minor,
            discount_bps=cl.input.discount_bps,
            net_minor=cl.net_minor,
            tax_minor=cl.tax_minor,
            cost_minor=cl.cost_minor,
            margin_minor=cl.margin_minor,
            margin_bps=cl.margin_bps,
            ceiling_bps=cl.effective_ceiling_bps,
            overage_bps=cl.overage_bps,
            added_from_suggestion=cl.input.added_from_suggestion,
        )
        for cl in computed
    ]


def evaluate(
    lines: list[EvaluatedLineInput],
    policy: PolicySnapshot,
    customer_tier: str,
    order_discount_bps: int,
    *,
    currency: str = "INR",
    tax_bps_by_product: dict[int, int] | None = None,
) -> QuoteComputation:
    """Implements `DECISION_ENGINE.md` §3 steps 1-8 exactly, building the
    `DecisionTrace` as it goes. `tax_bps_by_product` is optional purely so callers
    that already loaded the product row can avoid a second lookup; when omitted, tax
    is treated as zero (used by the upsell scorer, which never surfaces tax)."""
    if not lines:
        return _empty_computation(policy, customer_tier, currency)

    tax_bps_by_product = tax_bps_by_product or {}
    tier_ceiling = policy.tier_ceilings.get(customer_tier, 0)
    computed = _build_computed_lines(lines, policy, customer_tier, order_discount_bps, tax_bps_by_product)
    net_total = sum(cl.net_minor for cl in computed)

    # ---- Steps 5-7: aggregates and the score.
    blended_overage_raw = sum((Decimal(cl.overage_bps) * cl.weight for cl in computed), Decimal(0))
    blended_overage_bps = _round_half_up(blended_overage_raw)
    worst_overage_bps = max((cl.overage_bps for cl in computed), default=0)

    weights = policy.weights
    thresholds = policy.thresholds
    w_blended = Decimal(weights.get("w_blended_bps", 4500))
    w_worst = Decimal(weights.get("w_worst_bps", 3500))
    w_value = Decimal(weights.get("w_value_bps", 1000))
    w_margin = Decimal(weights.get("w_margin_bps", 1000))
    scale_overage = Decimal(weights.get("scale_overage_bps", 1000)) or Decimal(1)
    value_reference = Decimal(weights.get("value_reference_minor", 1)) or Decimal(1)
    margin_scale = Decimal(weights.get("margin_scale_bps", 500)) or Decimal(1)

    value_factor = min(Decimal(100), Decimal(net_total * 100) / value_reference)
    margin_shortfall_weighted = sum(
        (Decimal(cl.margin_shortfall_bps) * cl.weight for cl in computed), Decimal(0)
    )
    margin_factor = min(Decimal(100), margin_shortfall_weighted * 100 / margin_scale)

    blended_normalised = min(Decimal(100), Decimal(blended_overage_bps) * 100 / scale_overage)
    worst_normalised = min(Decimal(100), Decimal(worst_overage_bps) * 100 / scale_overage)

    blended_contribution = w_blended / 10000 * blended_normalised
    worst_contribution = w_worst / 10000 * worst_normalised
    value_contribution = w_value / 10000 * value_factor
    margin_contribution = w_margin / 10000 * margin_factor

    risk_score_raw = blended_contribution + worst_contribution + value_contribution + margin_contribution
    risk_score = _clamp(_round_half_up(risk_score_raw), 0, 100)

    # ---- Step 8: routing.
    t1 = thresholds.get("t1_l1_required", 20)
    t2 = thresholds.get("t2_l2_required", 55)
    hard_breach = thresholds.get("hard_breach_bps", 500)
    fin_value_floor = thresholds.get("finance_value_floor_minor", 0)

    gate1_below_cost = any(cl.margin_bps < 0 for cl in computed)
    gate2_hard_breach = worst_overage_bps > hard_breach
    gate3_value_floor = fin_value_floor > 0 and net_total > fin_value_floor

    required: set[str] = set()
    if risk_score >= t2:
        required |= {"l1_sales_manager", "l2_finance"}
    elif risk_score >= t1:
        required |= {"l1_sales_manager"}
    if gate2_hard_breach:
        required |= {"l1_sales_manager"}
    if gate3_value_floor:
        required |= {"l1_sales_manager", "l2_finance"}

    required_order = ["l1_sales_manager", "l2_finance"]
    required_approvals = [level for level in required_order if level in required]

    if gate1_below_cost:
        outcome = "blocked"
        required_approvals = []
    elif "l2_finance" in required_approvals:
        outcome = "l1_l2_required"
    elif "l1_sales_manager" in required_approvals:
        outcome = "l1_required"
    else:
        outcome = "auto_approved"

    # ---- Assemble the trace.
    trace_lines = [
        DecisionTraceLine(
            line_id=cl.input.line_id,
            product_name=cl.input.product_name,
            category_name=cl.input.category_name,
            discount_bps=cl.combined_discount_bps,
            tier_ceiling_bps=cl.tier_ceiling_bps,
            category_ceiling_bps=cl.category_ceiling_bps,
            effective_ceiling_bps=cl.effective_ceiling_bps,
            ceiling_source=cl.ceiling_source,
            overage_bps=cl.overage_bps,
            weight_bps=_round_half_up(cl.weight * 10000),
            weighted_overage_bps=_round_half_up(Decimal(cl.overage_bps) * cl.weight),
            margin_bps=cl.margin_bps,
            margin_floor_bps=cl.margin_floor_bps,
            margin_shortfall_bps=cl.margin_shortfall_bps,
            verdict=(
                "hard_breach"
                if cl.margin_bps < 0 or cl.overage_bps > hard_breach
                else ("over_limit" if cl.overage_bps > 0 else "within_limit")
            ),
        )
        for cl in computed
    ]

    components = [
        DecisionTraceComponent(
            key="blended",
            label=f"Blended overage across {len(computed)} line{'s' if len(computed) != 1 else ''}",
            raw_value=blended_overage_bps,
            normalised=_round_half_up(blended_normalised),
            weight_bps=weights.get("w_blended_bps", 4500),
            contribution=_round_half_up(blended_contribution),
            explanation=(
                f"Revenue-weighted overage across all lines is {blended_overage_bps} bps."
            ),
        ),
        DecisionTraceComponent(
            key="worst",
            label="Worst single-line overage",
            raw_value=worst_overage_bps,
            normalised=_round_half_up(worst_normalised),
            weight_bps=weights.get("w_worst_bps", 3500),
            contribution=_round_half_up(worst_contribution),
            explanation=f"The single worst line is {worst_overage_bps} bps over its ceiling.",
        ),
        DecisionTraceComponent(
            key="value",
            label="Order value",
            raw_value=net_total,
            normalised=_round_half_up(value_factor),
            weight_bps=weights.get("w_value_bps", 1000),
            contribution=_round_half_up(value_contribution),
            explanation=f"Order value is {net_total} minor units against a reference of {int(value_reference)}.",
        ),
        DecisionTraceComponent(
            key="margin",
            label="Margin shortfall vs. category floors",
            raw_value=_round_half_up(margin_shortfall_weighted),
            normalised=_round_half_up(margin_factor),
            weight_bps=weights.get("w_margin_bps", 1000),
            contribution=_round_half_up(margin_contribution),
            explanation="Revenue-weighted shortfall below each line's category margin floor.",
        ),
    ]

    rules_fired = build_rules_fired(
        computed_lines=computed,
        hard_breach=hard_breach,
        gate1_below_cost=gate1_below_cost,
        gate2_hard_breach=gate2_hard_breach,
        gate3_value_floor=gate3_value_floor,
        net_total=net_total,
        fin_value_floor=fin_value_floor,
        risk_score=risk_score,
        t1=t1,
        blended_overage_bps=blended_overage_bps,
    )

    summary = build_summary(
        computed_lines=computed,
        gate1_below_cost=gate1_below_cost,
        gate3_value_floor=gate3_value_floor,
        net_total=net_total,
        fin_value_floor=fin_value_floor,
        risk_score=risk_score,
        required_approvals=required_approvals,
        currency=currency,
    )

    trace = DecisionTrace(
        policy_version=policy.version,
        customer_tier=customer_tier,
        tier_ceiling_bps=tier_ceiling,
        lines=trace_lines,
        components=components,
        risk_score=risk_score,
        thresholds={"t1": t1, "t2": t2},
        rules_fired=rules_fired,
        required_approvals=required_approvals,
        outcome=outcome,
        summary=summary,
    )

    gross_minor = sum(cl.gross_minor for cl in computed)
    discount_total_minor = sum(cl.combined_discount_minor for cl in computed)
    tax_total_minor = sum(cl.tax_minor for cl in computed)
    cost_total_minor = sum(cl.cost_minor for cl in computed)
    margin_total_minor = net_total - cost_total_minor

    return QuoteComputation(
        gross_minor=gross_minor,
        discount_total_minor=discount_total_minor,
        net_minor=net_total,
        tax_minor=tax_total_minor,
        total_minor=net_total + tax_total_minor,
        cost_total_minor=cost_total_minor,
        margin_minor=margin_total_minor,
        margin_bps=(
            to_bps(margin_total_minor, net_total)
            if margin_total_minor >= 0 and net_total > 0
            else _floor_bps(margin_total_minor, net_total)
            if net_total > 0
            else (-10000 if margin_total_minor < 0 else 0)
        ),
        effective_discount_bps=to_bps(discount_total_minor, gross_minor) if gross_minor else 0,
        blended_overage_bps=blended_overage_bps,
        worst_overage_bps=worst_overage_bps,
        risk_score=risk_score,
        required_approvals=required_approvals,
        trace=trace,
        currency=currency,
    )
