"""Pure, integer-only money helpers. No `Float` / `Decimal` ever crosses these
boundaries as a stored value — `Decimal` is used only as scratch space for exact
rounding, per `DECISION_ENGINE.md` §1.4.

Money is always minor units (paise); percentages are always basis points (bps, 0..10000).
"""

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal


def apply_discount_bps(amount_minor: int, bps: int) -> int:
    """`amount_minor * (10000 - bps) / 10000`, rounded half-up. The net amount after
    applying a discount of `bps` basis points."""
    factor = Decimal(10000 - bps)
    return int((Decimal(amount_minor) * factor / Decimal(10000)).quantize(0, rounding=ROUND_HALF_UP))


def apply_bps(amount_minor: int, bps: int) -> int:
    """`amount_minor * bps / 10000`, rounded half-up. E.g. tax, margin-floor gaps."""
    return int((Decimal(amount_minor) * Decimal(bps) / Decimal(10000)).quantize(0, rounding=ROUND_HALF_UP))


def to_bps(numerator: int, denominator: int) -> int:
    """`numerator / denominator` as basis points, floored. `denominator == 0` -> 0
    (mirrors `DECISION_ENGINE.md`'s `margin_bps_i = 0 if net_i == 0 else ...`)."""
    if denominator == 0:
        return 0
    return int((Decimal(numerator) * Decimal(10000) / Decimal(denominator)).quantize(0, rounding=ROUND_DOWN))


def distribute_largest_remainder(total_minor: int, weights: list[int]) -> list[int]:
    """Split `total_minor` across `len(weights)` buckets proportionally to `weights`,
    so the parts sum **exactly** to `total_minor`. Used for order-level discount
    allocation, warehouse splits, and subscription proration remainders.

    Each bucket gets `floor(total * weight / sum(weights))`; the leftover units (there
    are always fewer than `len(weights)` of them) go one each to the buckets with the
    largest fractional remainder, ties broken by original index.
    """
    if not weights:
        return []
    weight_total = sum(weights)
    if weight_total == 0:
        # Nothing to weight by — first bucket absorbs everything, rest get 0, so the
        # sum is still exact.
        return [total_minor] + [0] * (len(weights) - 1)

    shares: list[int] = []
    remainders: list[Decimal] = []
    for weight in weights:
        exact = Decimal(total_minor) * Decimal(weight) / Decimal(weight_total)
        floor_share = int(exact.quantize(0, rounding=ROUND_DOWN))
        shares.append(floor_share)
        remainders.append(exact - floor_share)

    leftover = total_minor - sum(shares)
    order = sorted(range(len(weights)), key=lambda i: remainders[i], reverse=True)
    for i in order[:leftover]:
        shares[i] += 1
    return shares


def format_minor(amount_minor: int, currency: str) -> str:
    """Backend-side display formatting, for exports (PDF/XLSX) only. The frontend
    never does this — see `API_CONTRACT.md` §1 "Money formatting rule"."""
    sign = "-" if amount_minor < 0 else ""
    major, minor = divmod(abs(amount_minor), 100)
    return f"{sign}{currency} {major:,}.{minor:02d}"
