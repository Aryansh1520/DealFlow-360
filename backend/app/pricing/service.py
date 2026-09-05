"""The price resolver — the only place a unit price is computed from a price list.

Pure function, no DB access: the caller (Phase 2's `build_evaluation_inputs`) passes in
the price lists it already loaded. Do not change this signature later — the engine
depends on it exactly as specified in `BACKEND_PHASE_1.md` Task 4.

`build_evaluation_inputs` below is Phase 2's boundary function — the *only* place that
touches the DB to turn raw (product_id, variant_id, quantity, discount_bps) tuples into
the frozen `EvaluatedLineInput`s the engine consumes. One query for products, one for
price lists, per `BACKEND_PHASE_2.md` Task 1 / Task 4.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.catalog.models import Product, ProductVariant
from app.core.exceptions import NotFoundException, ValidationException
from app.pricing.models import PriceList

if TYPE_CHECKING:
    from app.pricing.engine import EvaluatedLineInput


def _find_entry(price_list: PriceList, product_id: int, variant_id: int | None):
    if variant_id is not None:
        for entry in price_list.entries:
            if entry.product_id == product_id and entry.variant_id == variant_id:
                return entry
    for entry in price_list.entries:
        if entry.product_id == product_id and entry.variant_id is None:
            return entry
    return None


def resolve_unit_price(
    product: Product,
    variant: ProductVariant | None,
    customer_tier: str,
    price_lists: list[PriceList],
) -> int:
    """1. find the tier-matching price list; fall back to the default list
    2. if an entry overrides the price, use it; else `product.list_price_minor`
    3. add `variant.extra_price_minor`
    4. return paise

    `entry.extra_discount_bps` is not applied here — it feeds into the engine's
    discount maths (Phase 2), not the base unit price.
    """
    price_list = next((pl for pl in price_lists if pl.tier == customer_tier), None)
    if price_list is None:
        price_list = next((pl for pl in price_lists if pl.is_default), None)

    base_price = product.list_price_minor
    if price_list is not None:
        entry = _find_entry(price_list, product.id, variant.id if variant else None)
        if entry is not None and entry.override_price_minor is not None:
            base_price = entry.override_price_minor

    variant_extra = variant.extra_price_minor if variant is not None else 0
    return base_price + variant_extra


@dataclass(frozen=True)
class RawLineInput:
    """What a caller (the quotations service, a preview payload, the upsell scorer)
    has on hand before prices are resolved."""

    product_id: int
    variant_id: int | None
    quantity: int
    discount_bps: int
    line_id: int | None = None
    added_from_suggestion: bool = False


def build_evaluation_inputs(
    db: Session,
    *,
    customer_tier: str,
    raw_lines: list[RawLineInput],
) -> "list[EvaluatedLineInput]":
    """The only place in Phase 2 that touches the DB to build the engine's inputs.
    One query for products (with category + variants eagerly loaded), one for price
    lists — see `BACKEND_PHASE_2.md` Task 4's preview budget."""
    from app.pricing.engine import EvaluatedLineInput  # local import: avoids a cycle with engine.py

    if not raw_lines:
        return []

    product_ids = {raw.product_id for raw in raw_lines}
    products = {
        p.id: p
        for p in db.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .options(joinedload(Product.category), selectinload(Product.variants))
        ).unique()
    }
    price_lists = list(db.scalars(select(PriceList).options(selectinload(PriceList.entries))))

    evaluated: list[EvaluatedLineInput] = []
    for raw in raw_lines:
        product = products.get(raw.product_id)
        if product is None:
            raise NotFoundException(f"Product {raw.product_id} not found")

        variant = None
        if raw.variant_id is not None:
            variant = next((v for v in product.variants if v.id == raw.variant_id), None)
            if variant is None:
                raise NotFoundException(f"Variant {raw.variant_id} not found on product {raw.product_id}")

        if raw.quantity <= 0:
            raise ValidationException("Line quantity must be positive")

        unit_price_minor = resolve_unit_price(product, variant, customer_tier, price_lists)

        evaluated.append(
            EvaluatedLineInput(
                line_id=raw.line_id,
                product_id=product.id,
                product_name=product.name,
                variant_id=raw.variant_id,
                category_id=product.category_id,
                category_name=product.category.name,
                line_type=product.line_type,
                subscription_plan_id=product.subscription_plan_id,
                quantity=raw.quantity,
                unit_price_minor=unit_price_minor,
                cost_price_minor=product.cost_price_minor,
                discount_bps=raw.discount_bps,
                added_from_suggestion=raw.added_from_suggestion,
            )
        )
    return evaluated


def tax_bps_by_product(db: Session, product_ids: set[int]) -> dict[int, int]:
    """Small helper so callers who already know the product ids (the quotations
    service, mostly) don't have to re-derive them from `EvaluatedLineInput`."""
    if not product_ids:
        return {}
    rows = db.execute(select(Product.id, Product.tax_bps).where(Product.id.in_(product_ids)))
    return dict(rows.all())
