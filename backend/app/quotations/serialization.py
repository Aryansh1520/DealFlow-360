"""Turns a `Quotation` ORM row into the wire `QuotationRead`, always recomputing
`computation` and every line-level derived field live via the engine — nothing about
pricing is ever read off a stored column. One source of truth, per
`BACKEND_PHASE_2.md` Task 4.
"""

from sqlalchemy.orm import Session

from app.pricing import engine
from app.pricing.service import RawLineInput, build_evaluation_inputs, tax_bps_by_product as load_tax_bps
from app.policies.service import get_policy_snapshot_by_version
from app.quotations.models import Quotation
from app.quotations.schemas import QuoteComputation, QuoteLineRead, QuotationRead


def compute_quotation(db: Session, quotation: Quotation) -> QuoteComputation:
    policy = get_policy_snapshot_by_version(db, quotation.policy_version)
    raw_lines = [
        RawLineInput(
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            discount_bps=line.discount_bps,
            line_id=line.id,
            added_from_suggestion=line.added_from_suggestion,
        )
        for line in quotation.lines
    ]
    evaluated = build_evaluation_inputs(db, customer_tier=quotation.customer.tier, raw_lines=raw_lines)
    tax_bps = load_tax_bps(db, {e.product_id for e in evaluated})
    return engine.evaluate(
        evaluated,
        policy,
        quotation.customer.tier,
        quotation.order_discount_bps,
        currency=quotation.currency,
        tax_bps_by_product=tax_bps,
    )


def build_quote_line_reads(db: Session, quotation: Quotation) -> tuple[list[QuoteLineRead], QuoteComputation]:
    """Computes once, returns both the per-line reads and the order computation so
    callers don't pay for the engine twice."""
    policy = get_policy_snapshot_by_version(db, quotation.policy_version)
    raw_lines = [
        RawLineInput(
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            discount_bps=line.discount_bps,
            line_id=line.id,
            added_from_suggestion=line.added_from_suggestion,
        )
        for line in quotation.lines
    ]
    evaluated = build_evaluation_inputs(db, customer_tier=quotation.customer.tier, raw_lines=raw_lines)
    tax_bps = load_tax_bps(db, {e.product_id for e in evaluated})

    computation = engine.evaluate(
        evaluated,
        policy,
        quotation.customer.tier,
        quotation.order_discount_bps,
        currency=quotation.currency,
        tax_bps_by_product=tax_bps,
    )
    details = engine.line_details(
        evaluated, policy, quotation.customer.tier, quotation.order_discount_bps, tax_bps
    )
    line_reads = [
        QuoteLineRead(
            id=d.line_id,
            quotation_id=quotation.id,
            product_id=d.product_id,
            product_name=d.product_name,
            variant_id=d.variant_id,
            category_id=d.category_id,
            line_type=d.line_type,
            subscription_plan_id=d.subscription_plan_id,
            quantity=d.quantity,
            unit_price_minor=d.unit_price_minor,
            discount_bps=d.discount_bps,
            net_minor=d.net_minor,
            tax_minor=d.tax_minor,
            cost_minor=d.cost_minor,
            margin_minor=d.margin_minor,
            margin_bps=d.margin_bps,
            ceiling_bps=d.ceiling_bps,
            overage_bps=d.overage_bps,
            added_from_suggestion=d.added_from_suggestion,
        )
        for d in details
    ]
    return line_reads, computation


def to_quotation_read(db: Session, quotation: Quotation) -> QuotationRead:
    line_reads, computation = build_quote_line_reads(db, quotation)
    return QuotationRead(
        id=quotation.id,
        reference=quotation.reference,
        order_number=quotation.order_number,
        customer_id=quotation.customer_id,
        customer_name=quotation.customer.name,
        customer_tier=quotation.customer.tier,
        owner_rep_id=quotation.owner_rep_id,
        owner_rep_name=quotation.owner_rep.full_name,
        status=quotation.status,
        version=quotation.version,
        policy_version=quotation.policy_version,
        currency=quotation.currency,
        order_discount_bps=quotation.order_discount_bps,
        valid_until=quotation.valid_until,
        lines=line_reads,
        computation=computation,
        fulfillment_status=quotation.fulfillment_status,
        created_at=quotation.created_at,
        updated_at=quotation.updated_at,
        last_activity_at=quotation.last_activity_at,
    )
