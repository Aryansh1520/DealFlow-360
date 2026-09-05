"""Pure allocator tests — no DB. `BACKEND_PHASE_3.md` Task 1."""

from app.fulfillment.allocator import (
    GreedyMinShipmentStrategy,
    LineDemand,
    StockRow,
    WarehouseRow,
)

MAIN = WarehouseRow(warehouse_id=1, name="Main", shipping_cost_weight=30)
EAST = WarehouseRow(warehouse_id=2, name="East", shipping_cost_weight=70)


def test_single_warehouse_covers_everything():
    plan = GreedyMinShipmentStrategy().allocate(
        [LineDemand(10, 100, "Widget", 5)],
        [StockRow(100, 1, 10), StockRow(100, 2, 10)],
        [MAIN, EAST],
    )
    assert len(plan.shipments) == 1
    assert plan.shipments[0].warehouse_id == 1  # cheaper weight breaks the coverage tie
    assert plan.fully_allocatable
    assert not plan.backorders


def test_split_across_two_when_neither_covers_alone():
    # stock 3 in Main, 5 in East, order 6 -> visible split
    plan = GreedyMinShipmentStrategy().allocate(
        [LineDemand(10, 100, "Widget", 6)],
        [StockRow(100, 1, 3), StockRow(100, 2, 5)],
        [MAIN, EAST],
    )
    assert len(plan.shipments) == 2
    assert sum(ln.quantity for s in plan.shipments for ln in s.lines) == 6
    assert plan.fully_allocatable


def test_backorder_when_total_stock_short():
    plan = GreedyMinShipmentStrategy().allocate(
        [LineDemand(10, 100, "Widget", 5)],
        [StockRow(100, 1, 1), StockRow(100, 2, 1)],
        [MAIN, EAST],
    )
    assert not plan.fully_allocatable
    assert plan.backorders[0].quantity == 3
    assert sum(ln.quantity for s in plan.shipments for ln in s.lines) == 2


def test_plan_hash_is_stable_and_order_independent():
    args_a = (
        [LineDemand(1, 100, "A", 2), LineDemand(2, 200, "B", 2)],
        [StockRow(100, 1, 5), StockRow(200, 2, 5)],
        [MAIN, EAST],
    )
    args_b = (
        [LineDemand(2, 200, "B", 2), LineDemand(1, 100, "A", 2)],
        [StockRow(200, 2, 5), StockRow(100, 1, 5)],
        [EAST, MAIN],
    )
    h1 = GreedyMinShipmentStrategy().allocate(*args_a).plan_hash
    h2 = GreedyMinShipmentStrategy().allocate(*args_b).plan_hash
    assert h1 == h2 and len(h1) == 64


def test_estimated_cost_is_base_times_weight_per_shipment():
    plan = GreedyMinShipmentStrategy().allocate(
        [LineDemand(10, 100, "Widget", 6)],
        [StockRow(100, 1, 3), StockRow(100, 2, 5)],
        [MAIN, EAST],
    )
    # base 5000 * (30 + 70)
    assert plan.estimated_shipping_cost_minor == 5000 * (30 + 70)
