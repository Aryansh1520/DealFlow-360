"""Upsell suggestions — `BACKEND_PHASE_2.md` Task 7.

`rebuild_affinity` computes `product_affinity` once, from whatever `quote_lines`
exist at the time it's called (seed time, per Phase 2 scope; a scheduled refresh is
Phase 3). `get_suggestions` is the serving path behind `GET /quotations/{id}/suggestions`.
"""

from itertools import combinations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.affinity.models import ProductAffinity
from app.catalog.models import Product
from app.core.money import to_bps
from app.core.tenant_context import require_current_org
from app.policies.service import get_active_policy
from app.pricing.service import RawLineInput
from app.quotations.models import Quotation, QuoteLine
from app.quotations.schemas import SuggestionRead
from app.quotations.service import evaluate_raw_lines, raw_lines_from_saved


def rebuild_affinity(db: Session) -> int:
    """Association-rule affinity over every `quote_lines` row that exists right now,
    grouped by quotation. Real, general-purpose computation — not seed-specific —
    it's just that at Phase 2 seed time it only has whatever historical quotations
    the seed itself created to run against.

    Scoped to the current organization: the `quote_lines` read is filtered by the
    tenant session events and the `product_affinity` wipe is filtered explicitly."""
    org_id = require_current_org(db)
    rows = db.execute(select(QuoteLine.quotation_id, QuoteLine.product_id).distinct()).all()

    by_quotation: dict[int, set[int]] = {}
    for quotation_id, product_id in rows:
        by_quotation.setdefault(quotation_id, set()).add(product_id)

    total_quotations = len(by_quotation)
    db.execute(delete(ProductAffinity).where(ProductAffinity.org_id == org_id))
    if total_quotations == 0:
        db.commit()
        return 0

    product_count: dict[int, int] = {}
    pair_count: dict[tuple[int, int], int] = {}
    for products in by_quotation.values():
        for p in products:
            product_count[p] = product_count.get(p, 0) + 1
        for a, b in combinations(sorted(products), 2):
            pair_count[(a, b)] = pair_count.get((a, b), 0) + 1

    created = 0
    for (a, b), support in pair_count.items():
        for src, dst in ((a, b), (b, a)):
            confidence_bps = to_bps(support, product_count[src])
            lift = (support * total_quotations) / (product_count[src] * product_count[dst])
            db.add(
                ProductAffinity(
                    product_a=src,
                    product_b=dst,
                    support_count=support,
                    confidence_bps=confidence_bps,
                    lift=round(lift, 4),
                )
            )
            created += 1
    db.commit()
    return created


def _norm(value: float, scale: float) -> float:
    return max(0.0, min(100.0, value * scale))


def get_suggestions(
    db: Session, quotation: Quotation, *, limit: int, dismissed_product_ids: set[int]
) -> list[SuggestionRead]:
    cart_product_ids = {line.product_id for line in quotation.lines}
    if not cart_product_ids:
        return []

    affinity_rows = db.scalars(
        select(ProductAffinity)
        .where(ProductAffinity.product_a.in_(cart_product_ids))
        .order_by(ProductAffinity.lift.desc())
    ).all()

    best_by_candidate: dict[int, ProductAffinity] = {}
    for row in affinity_rows:
        if row.product_b in cart_product_ids or row.product_b in dismissed_product_ids:
            continue
        existing = best_by_candidate.get(row.product_b)
        if existing is None or row.lift > existing.lift:
            best_by_candidate[row.product_b] = row
    if not best_by_candidate:
        return []

    policy = get_active_policy(db)
    min_margin_bps = policy.upsell.get("min_margin_bps", 0)
    w_lift = policy.upsell.get("w_lift_bps", 5000)
    w_margin = policy.upsell.get("w_margin_bps", 3000)
    w_promo = policy.upsell.get("w_promo_bps", 2000)

    products = {
        p.id: p
        for p in db.scalars(
            select(Product).where(Product.id.in_(best_by_candidate)).options(selectinload(Product.variants))
        )
    }

    base_raw_lines = raw_lines_from_saved(quotation)
    base_computation = evaluate_raw_lines(db, quotation, base_raw_lines, quotation.order_discount_bps)

    source_names = {line.product_id: line.product.name for line in quotation.lines}

    suggestions: list[SuggestionRead] = []
    for product_id, affinity_row in best_by_candidate.items():
        product = products.get(product_id)
        if product is None or not product.is_active:
            continue

        list_price = product.list_price_minor
        margin_at_list_bps = to_bps(list_price - product.cost_price_minor, list_price) if list_price else 0
        if margin_at_list_bps < min_margin_bps:
            continue

        candidate_raw_lines = base_raw_lines + [
            RawLineInput(product_id=product.id, variant_id=None, quantity=1, discount_bps=0)
        ]
        candidate_computation = evaluate_raw_lines(db, quotation, candidate_raw_lines, quotation.order_discount_bps)
        margin_delta_minor = candidate_computation.margin_minor - base_computation.margin_minor
        margin_delta_bps = candidate_computation.margin_bps - base_computation.margin_bps

        norm_lift = _norm(float(affinity_row.lift), 20)
        norm_margin = _norm(margin_delta_bps, 0.2)
        promo_score = 100.0 if product.is_promoted else 0.0
        score = round(w_lift / 10000 * norm_lift + w_margin / 10000 * norm_margin + w_promo / 10000 * promo_score)
        score = max(0, min(100, int(score)))

        source_name = source_names.get(affinity_row.product_a, "items in this quote")
        suggestions.append(
            SuggestionRead(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                list_price_minor=product.list_price_minor,
                suggested_quantity=1,
                score=score,
                lift=round(float(affinity_row.lift), 2),
                support_count=affinity_row.support_count,
                margin_delta_minor=margin_delta_minor,
                margin_delta_bps=margin_delta_bps,
                is_promoted=product.is_promoted,
                reason=f"Bought with {source_name} in {affinity_row.support_count} past orders",
                currency=quotation.currency,
            )
        )

    suggestions.sort(key=lambda s: s.score, reverse=True)
    return suggestions[:limit]
