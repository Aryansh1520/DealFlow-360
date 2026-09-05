"""Rule and summary construction for `DecisionTrace`, split out of `engine.py` to keep
the core maths readable. Still zero I/O — everything here is pure, consuming only the
values `engine.evaluate()` already computed.
"""

from typing import TYPE_CHECKING

from app.core.enums import RiskRuleCode
from app.core.money import format_minor
from app.quotations.schemas import DecisionTraceRule

if TYPE_CHECKING:
    from app.pricing.engine import _ComputedLine


def build_rules_fired(
    *,
    computed_lines: list["_ComputedLine"],
    hard_breach: int,
    gate1_below_cost: bool,
    gate2_hard_breach: bool,
    gate3_value_floor: bool,
    net_total: int,
    fin_value_floor: int,
    risk_score: int,
    t1: int,
    blended_overage_bps: int,
) -> list[DecisionTraceRule]:
    rules: list[DecisionTraceRule] = []

    for cl in computed_lines:
        if cl.margin_bps < 0:
            rules.append(
                DecisionTraceRule(
                    code=RiskRuleCode.MARGIN_FLOOR_BREACH.value,
                    severity="block",
                    message=(
                        f"{cl.input.product_name} is priced below cost "
                        f"(margin {cl.margin_bps / 100:.1f}%)."
                    ),
                    line_id=cl.input.line_id,
                )
            )
        elif cl.margin_shortfall_bps > 0:
            rules.append(
                DecisionTraceRule(
                    code=RiskRuleCode.MARGIN_FLOOR_BREACH.value,
                    severity="warn",
                    message=(
                        f"{cl.input.product_name} margin is {cl.margin_shortfall_bps / 100:.1f} "
                        f"points below its {cl.margin_floor_bps / 100:.0f}% category floor."
                    ),
                    line_id=cl.input.line_id,
                )
            )

        if cl.overage_bps > 0:
            code = RiskRuleCode.LINE_CEILING_BREACH if cl.ceiling_source == "category" else RiskRuleCode.TIER_CEILING_BREACH
            severity = "block" if cl.overage_bps > hard_breach else "warn"
            ceiling_label = "category" if cl.ceiling_source == "category" else "tier"
            rules.append(
                DecisionTraceRule(
                    code=code.value,
                    severity=severity,
                    message=(
                        f"{cl.input.product_name} is discounted {cl.overage_bps / 100:.1f} points "
                        f"above its {cl.effective_ceiling_bps / 100:.0f}% {ceiling_label} ceiling."
                    ),
                    line_id=cl.input.line_id,
                )
            )

    if gate2_hard_breach:
        rules.append(
            DecisionTraceRule(
                code=RiskRuleCode.HARD_BREACH_OVERRIDE.value,
                severity="block",
                message="A line breached its ceiling by more than the hard-breach threshold — Sales Manager approval is forced.",
                line_id=None,
            )
        )

    if gate3_value_floor:
        rules.append(
            DecisionTraceRule(
                code=RiskRuleCode.ORDER_VALUE_FLOOR.value,
                severity="block",
                message=(
                    f"Order value {format_minor(net_total, 'INR')} exceeds the "
                    f"{format_minor(fin_value_floor, 'INR')} finance review floor — Finance approval is forced."
                ),
                line_id=None,
            )
        )

    if not gate1_below_cost and risk_score >= t1:
        rules.append(
            DecisionTraceRule(
                code=RiskRuleCode.BLENDED_THRESHOLD.value,
                severity="warn",
                message=(
                    f"Blended overage ({blended_overage_bps} bps) drove the risk score to "
                    f"{risk_score}/100, crossing the approval threshold."
                ),
                line_id=None,
            )
        )

    return rules


_APPROVAL_LABELS = {
    "l1_sales_manager": "Sales Manager approval required",
    "l2_finance": "Finance approval required",
}


def build_summary(
    *,
    computed_lines: list["_ComputedLine"],
    gate1_below_cost: bool,
    gate3_value_floor: bool,
    net_total: int,
    fin_value_floor: int,
    risk_score: int,
    required_approvals: list[str],
    currency: str,
) -> str:
    if gate1_below_cost:
        worst = min(computed_lines, key=lambda cl: cl.margin_bps)
        return (
            f"{worst.input.product_name} is priced below cost "
            f"(margin {worst.margin_bps / 100:.1f}%). Fix this line before saving."
        )

    if not required_approvals:
        return f"All lines within policy. Risk {risk_score}/100 — auto-approved."

    approval_label = " then ".join(_APPROVAL_LABELS[level] for level in required_approvals)

    worst_overage_line = max(computed_lines, key=lambda cl: cl.overage_bps, default=None)
    if worst_overage_line is not None and worst_overage_line.overage_bps > 0:
        ceiling_label = "category" if worst_overage_line.ceiling_source == "category" else "tier"
        return (
            f"{worst_overage_line.input.product_name} is discounted "
            f"{worst_overage_line.overage_bps / 100:.1f} points above its "
            f"{worst_overage_line.effective_ceiling_bps / 100:.0f}% {ceiling_label} ceiling. "
            f"Risk {risk_score}/100 — {approval_label}."
        )

    if gate3_value_floor:
        return (
            f"All lines within policy, but order value {format_minor(net_total, currency)} "
            f"exceeds the {format_minor(fin_value_floor, currency)} finance review floor."
        )

    return f"Risk {risk_score}/100 — {approval_label}."
