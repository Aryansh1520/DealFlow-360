"""Pure proration tests — the invariant is `Σ amount == line_net_minor` exactly.
`BACKEND_PHASE_3.md` Task 4."""

from datetime import date

import pytest

from app.billing.proration import build_periods


@pytest.mark.parametrize(
    "net,start,interval,cycles,proration",
    [
        (1_200_000, date(2026, 1, 1), "monthly", 12, True),
        (1_200_007, date(2026, 1, 1), "monthly", 12, True),  # non-divisible
        (999_999, date(2026, 3, 17), "monthly", 12, True),  # mid-month start -> prorated
        (5_000_000, date(2026, 6, 10), "quarterly", 4, True),
        (7_777_777, date(2026, 2, 28), "yearly", 1, False),
        (250_000, date(2026, 1, 15), "monthly", 6, False),  # proration disabled
    ],
)
def test_schedule_sums_exactly_to_net(net, start, interval, cycles, proration):
    periods = build_periods(
        line_net_minor=net,
        start=start,
        interval=interval,
        billing_cycles=cycles,
        proration_enabled=proration,
    )
    assert sum(p.amount_minor for p in periods) == net
    assert len(periods) == cycles
    assert all(p.amount_minor >= 0 for p in periods)


def test_mid_month_start_prorates_first_period_only():
    periods = build_periods(
        line_net_minor=1_200_000,
        start=date(2026, 3, 10),
        interval="monthly",
        billing_cycles=12,
        proration_enabled=True,
    )
    assert periods[0].is_prorated
    assert periods[0].proration_days and periods[0].proration_basis_days
    assert periods[0].proration_days < periods[0].proration_basis_days
    assert not any(p.is_prorated for p in periods[1:])


def test_first_of_month_start_is_not_prorated():
    periods = build_periods(
        line_net_minor=1_200_000,
        start=date(2026, 4, 1),
        interval="monthly",
        billing_cycles=12,
        proration_enabled=True,
    )
    assert not any(p.is_prorated for p in periods)
    assert periods[0].amount_minor == 100_000


def test_periods_are_contiguous():
    periods = build_periods(
        line_net_minor=900_000,
        start=date(2026, 5, 20),
        interval="monthly",
        billing_cycles=6,
        proration_enabled=True,
    )
    for earlier, later in zip(periods, periods[1:]):
        assert earlier.period_end == later.period_start
