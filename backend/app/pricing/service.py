"""The price resolver — the only place a unit price is computed from a price list.

Pure function, no DB access: the caller (Phase 2's `build_evaluation_inputs`) passes in
the price lists it already loaded. Do not change this signature later — the engine
depends on it exactly as specified in `BACKEND_PHASE_1.md` Task 4.
"""

from app.catalog.models import Product, ProductVariant
from app.pricing.models import PriceList


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
