from app.core.money import (
    apply_bps,
    apply_discount_bps,
    distribute_largest_remainder,
    format_minor,
    to_bps,
)


def test_apply_discount_bps_rounds_half_up():
    # 10000 paise at 12.5% off -> 8750.0 exactly
    assert apply_discount_bps(10000, 1250) == 8750
    # 999 paise at 10% off -> 899.1 -> rounds to 899
    assert apply_discount_bps(999, 1000) == 899
    # 5 paise at 50% off -> 2.5 -> half-up rounds to 3
    assert apply_discount_bps(5, 5000) == 3
    assert apply_discount_bps(10000, 0) == 10000
    assert apply_discount_bps(10000, 10000) == 0


def test_apply_bps():
    assert apply_bps(10000, 1800) == 1800
    assert apply_bps(3, 5000) == 2  # 1.5 -> half-up -> 2


def test_to_bps_floors():
    assert to_bps(1, 3) == 3333
    assert to_bps(0, 100) == 0
    assert to_bps(100, 0) == 0  # denominator 0 -> 0, never a ZeroDivisionError
    assert to_bps(10000, 10000) == 10000


def test_distribute_largest_remainder_sums_exactly():
    weights = [1, 1, 1]
    shares = distribute_largest_remainder(100, weights)
    assert sum(shares) == 100
    assert shares == [34, 33, 33]


def test_distribute_largest_remainder_uneven_weights():
    weights = [70400, 16400]
    total = 86800
    shares = distribute_largest_remainder(total, weights)
    assert sum(shares) == total
    assert shares[0] > shares[1]


def test_distribute_largest_remainder_zero_weights():
    assert distribute_largest_remainder(500, [0, 0, 0]) == [500, 0, 0]


def test_distribute_largest_remainder_empty():
    assert distribute_largest_remainder(500, []) == []


def test_distribute_largest_remainder_many_buckets_exact():
    # A case designed to produce a non-trivial remainder distribution.
    weights = [1] * 7
    shares = distribute_largest_remainder(1000, weights)
    assert sum(shares) == 1000
    assert max(shares) - min(shares) <= 1


def test_format_minor():
    assert format_minor(123456, "INR") == "INR 1,234.56"
    assert format_minor(0, "INR") == "INR 0.00"
    assert format_minor(-500, "INR") == "-INR 5.00"
