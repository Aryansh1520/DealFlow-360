"""Pure day-count proration for subscription billing schedules.
`BACKEND_PHASE_3.md` Task 4 — "Proration is a pure day-count function".

The invariant every caller relies on: for one subscription line,
`Σ schedule.amount_minor == line_net_minor` **exactly**. The floor division loses
a few paise per period; the largest-remainder pass hands those back, and any first
-period proration shortfall is reconciled onto the final period.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from app.core.money import distribute_largest_remainder

_INTERVAL_MONTHS = {"monthly": 1, "quarterly": 3, "yearly": 12}
_DEFAULT_CYCLES = {"monthly": 12, "quarterly": 4, "yearly": 3}


def add_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@dataclass(frozen=True)
class SchedulePeriod:
    period_start: date
    period_end: date  # exclusive
    amount_minor: int
    is_prorated: bool
    proration_days: int | None
    proration_basis_days: int | None


def build_periods(
    *,
    line_net_minor: int,
    start: date,
    interval: str,
    billing_cycles: int | None,
    proration_enabled: bool,
) -> list[SchedulePeriod]:
    months = _INTERVAL_MONTHS.get(interval, 1)
    cycles = billing_cycles or _DEFAULT_CYCLES.get(interval, 12)
    cycles = max(1, cycles)

    # Nominal even split of the whole contract value across the cycles.
    nominal = distribute_largest_remainder(line_net_minor, [1] * cycles)

    # Period boundaries, aligned to the subscription start date.
    boundaries = [add_months(start, k * months) for k in range(cycles + 1)]

    periods: list[SchedulePeriod] = []
    carried = 0  # paise pulled out of a prorated first period, owed to the final one
    for k in range(cycles):
        p_start, p_end = boundaries[k], boundaries[k + 1]
        amount = nominal[k]
        is_prorated = False
        pdays = basis = None

        if k == 0 and proration_enabled and start.day != 1:
            # First period runs from the real start date to a clean month boundary.
            clean_end = add_months(date(start.year, start.month, 1), months)
            basis = (clean_end - date(start.year, start.month, 1)).days
            pdays = (clean_end - start).days
            if 0 < pdays < basis:
                prorated = nominal[0] * pdays // basis
                carried += nominal[0] - prorated
                amount = prorated
                is_prorated = True
                p_end = clean_end
                boundaries[1] = clean_end  # keep the chain contiguous

        periods.append(
            SchedulePeriod(
                period_start=p_start,
                period_end=p_end,
                amount_minor=amount,
                is_prorated=is_prorated,
                proration_days=pdays if is_prorated else None,
                proration_basis_days=basis if is_prorated else None,
            )
        )

    # Reconcile: everything held back from the first period lands on the last one,
    # so the sum is exact.
    if carried:
        last = periods[-1]
        periods[-1] = SchedulePeriod(
            period_start=last.period_start,
            period_end=last.period_end,
            amount_minor=last.amount_minor + carried,
            is_prorated=last.is_prorated,
            proration_days=last.proration_days,
            proration_basis_days=last.proration_basis_days,
        )

    assert sum(p.amount_minor for p in periods) == line_net_minor
    return periods
