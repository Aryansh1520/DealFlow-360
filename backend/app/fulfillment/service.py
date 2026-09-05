"""Fulfilment: turn a confirmed quotation into shipments, reservations and
backorders. `BACKEND_PHASE_3.md` Task 1.

The allocator (`app/fulfillment/allocator.py`) is pure. This module is the only
place that touches the DB: it loads rows, calls the strategy, and persists the
result under a consistent `FOR UPDATE` lock so two concurrent accepts can never
oversell.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, lazyload

from app.core.enums import (
    BackorderStatus,
    ErrorCode,
    EventType,
    QuoteStatus,
    ReservationStatus,
    ShipmentStatus,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.events.service import record_event
from app.fulfillment.allocator import (
    DEFAULT_STRATEGY,
    LineDemand,
    StockRow,
    WarehouseRow,
    AllocationPlan,
)
from app.fulfillment.models import Backorder, Shipment, ShipmentLine, StockReservation
from app.fulfillment.schemas import (
    AllocationInput,
    BackorderLine,
    FulfillmentPlan,
    ShipmentLine as ShipmentLineSchema,
    ShipmentPlan,
)
from app.quotations.models import Quotation
from app.quotations.transitions import transition
from app.users.models import User
from app.warehouses.models import Stock, Warehouse

# Backorders get a nominal restock ETA so the delivery-slippage alert (Task 5) has
# something to compare `now` against.
DEFAULT_RESTOCK_DAYS = 7


def _line_demand(quotation: Quotation) -> list[LineDemand]:
    demand: list[LineDemand] = []
    for line in quotation.lines:
        if line.line_type != "one_time":
            continue  # subscriptions aren't shipped
        demand.append(
            LineDemand(
                line_id=line.id,
                product_id=line.product_id,
                product_name=line.product.name,
                quantity=line.quantity,
            )
        )
    return demand


def _load_stock_and_warehouses(
    db: Session, product_ids: set[int], *, lock: bool
) -> tuple[list[Stock], list[Warehouse]]:
    if not product_ids:
        return [], []
    stmt = select(Stock).where(Stock.product_id.in_(product_ids)).order_by(Stock.id)
    if lock:
        # Consistent lock ORDER BY id — this is what stops two concurrent accepts
        # deadlocking. `BACKEND_PHASE_3.md` Task 1, "Concurrency".
        # `lazyload("*")` strips Stock's eager product/warehouse joins — Postgres
        # refuses FOR UPDATE on the nullable side of an outer join.
        stmt = stmt.with_for_update().options(lazyload("*"))
    stock_rows = list(db.scalars(stmt).all())
    warehouses = list(db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True))).all())
    return stock_rows, warehouses


def _compute_plan(
    quotation: Quotation, stock_rows: list[Stock], warehouses: list[Warehouse]
) -> AllocationPlan:
    demand = _line_demand(quotation)
    strat_stock = [
        StockRow(product_id=s.product_id, warehouse_id=s.warehouse_id, available=s.on_hand - s.reserved)
        for s in stock_rows
    ]
    strat_warehouses = [
        WarehouseRow(warehouse_id=w.id, name=w.name, shipping_cost_weight=w.shipping_cost_weight)
        for w in warehouses
    ]
    return DEFAULT_STRATEGY.allocate(demand, strat_stock, strat_warehouses)


def _plan_to_schema(quotation: Quotation, plan: AllocationPlan, restock_at: datetime | None) -> FulfillmentPlan:
    return FulfillmentPlan(
        quotation_id=quotation.id,
        plan_hash=plan.plan_hash,
        shipments=[
            ShipmentPlan(
                warehouse_id=s.warehouse_id,
                warehouse_name=s.warehouse_name,
                shipping_cost_weight=s.shipping_cost_weight,
                lines=[
                    ShipmentLineSchema(
                        line_id=ln.line_id,
                        product_id=ln.product_id,
                        product_name=ln.product_name,
                        quantity=ln.quantity,
                    )
                    for ln in s.lines
                ],
            )
            for s in plan.shipments
        ],
        backorders=[
            BackorderLine(
                line_id=b.line_id,
                product_id=b.product_id,
                product_name=b.product_name,
                quantity=b.quantity,
                expected_restock_at=restock_at,
            )
            for b in plan.backorders
        ],
        shipment_count=len(plan.shipments),
        estimated_shipping_cost_minor=plan.estimated_shipping_cost_minor,
        fully_allocatable=plan.fully_allocatable,
        currency=quotation.currency,
    )


def _require_fulfillable(quotation: Quotation) -> None:
    if quotation.status not in (QuoteStatus.CONFIRMED.value, QuoteStatus.FULFILLING.value):
        raise ConflictException(
            f"Quotation {quotation.reference} is {quotation.status}; a fulfilment plan "
            "can only be worked once it is confirmed.",
            code=ErrorCode.ILLEGAL_TRANSITION,
        )


# --------------------------------------------------------------------------- reads


def get_plan(db: Session, quotation: Quotation) -> FulfillmentPlan:
    """Live computation, writes nothing."""
    product_ids = {line.product_id for line in quotation.lines if line.line_type == "one_time"}
    stock_rows, warehouses = _load_stock_and_warehouses(db, product_ids, lock=False)
    plan = _compute_plan(quotation, stock_rows, warehouses)
    restock_at = datetime.now(timezone.utc) + timedelta(days=DEFAULT_RESTOCK_DAYS)
    return _plan_to_schema(quotation, plan, restock_at if plan.backorders else None)


# -------------------------------------------------------------------------- writes


def _clear_existing_fulfillment(db: Session, quotation: Quotation) -> None:
    """Release held reservations and drop planned shipments / open backorders so a
    re-plan (override, or a second accept) starts from a clean slate."""
    reservations = db.scalars(
        select(StockReservation).where(
            StockReservation.quotation_id == quotation.id,
            StockReservation.status == ReservationStatus.HELD.value,
        )
    ).all()
    stock_by_key: dict[tuple[int, int], Stock] = {}
    if reservations:
        keys = {(r.product_id, r.warehouse_id) for r in reservations}
        for s in db.scalars(
            select(Stock)
            .where(Stock.product_id.in_({k[0] for k in keys}))
            .order_by(Stock.id)
            .with_for_update()
            .options(lazyload("*"))
        ).all():
            stock_by_key[(s.product_id, s.warehouse_id)] = s
    for r in reservations:
        row = stock_by_key.get((r.product_id, r.warehouse_id))
        if row is not None:
            row.reserved = max(0, row.reserved - r.quantity)
        r.status = ReservationStatus.RELEASED.value

    for shipment in db.scalars(
        select(Shipment).where(Shipment.quotation_id == quotation.id)
    ).all():
        for sl in db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment.id)).all():
            db.delete(sl)
        db.delete(shipment)

    for bo in db.scalars(
        select(Backorder).where(
            Backorder.quotation_id == quotation.id,
            Backorder.status == BackorderStatus.OPEN.value,
        )
    ).all():
        bo.status = BackorderStatus.CANCELLED.value


def _persist_allocation(
    db: Session,
    quotation: Quotation,
    *,
    shipments: list[tuple[int, int, list[tuple[int, int, int]]]],  # (warehouse_id, weight, [(line_id, product_id, qty)])
    backorders: list[tuple[int, int, int]],  # (line_id, product_id, qty)
    stock_by_key: dict[tuple[int, int], Stock],
    restock_at: datetime,
) -> None:
    for warehouse_id, weight, lines in shipments:
        shipment = Shipment(
            quotation_id=quotation.id,
            warehouse_id=warehouse_id,
            status=ShipmentStatus.PLANNED.value,
            estimated_cost_minor=weight * 5_000,
        )
        db.add(shipment)
        db.flush()
        for line_id, product_id, qty in lines:
            db.add(
                ShipmentLine(
                    shipment_id=shipment.id, line_id=line_id, product_id=product_id, quantity=qty
                )
            )
            db.add(
                StockReservation(
                    quotation_id=quotation.id,
                    line_id=line_id,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=qty,
                    status=ReservationStatus.HELD.value,
                )
            )
            row = stock_by_key[(product_id, warehouse_id)]
            row.reserved += qty

    for line_id, product_id, qty in backorders:
        db.add(
            Backorder(
                quotation_id=quotation.id,
                line_id=line_id,
                product_id=product_id,
                quantity=qty,
                status=BackorderStatus.OPEN.value,
                expected_restock_at=restock_at,
            )
        )


def _set_fulfillment_status(quotation: Quotation, plan_has_backorders: bool, plan_has_shipments: bool) -> None:
    from app.core.enums import FulfillmentStatus

    if plan_has_backorders and plan_has_shipments:
        quotation.fulfillment_status = FulfillmentStatus.PARTIAL.value
    elif plan_has_backorders:
        quotation.fulfillment_status = FulfillmentStatus.BACKORDERED.value
    else:
        quotation.fulfillment_status = FulfillmentStatus.FULFILLED.value


def accept_plan(db: Session, quotation: Quotation, expected_version: int, plan_hash: str, actor: User) -> Quotation:
    _require_fulfillable(quotation)
    if expected_version != quotation.version:
        raise ConflictException(
            "This quotation changed since you loaded it.",
            code=ErrorCode.VERSION_CONFLICT,
            extra={"current_version": quotation.version},
        )

    product_ids = {line.product_id for line in quotation.lines if line.line_type == "one_time"}
    stock_rows, warehouses = _load_stock_and_warehouses(db, product_ids, lock=True)
    stock_by_key = {(s.product_id, s.warehouse_id): s for s in stock_rows}
    plan = _compute_plan(quotation, stock_rows, warehouses)

    if plan.plan_hash != plan_hash:
        raise ConflictException(
            "The fulfilment plan changed since it was shown to you — refetch and retry.",
            code=ErrorCode.ILLEGAL_TRANSITION,
            extra={"current_plan_hash": plan.plan_hash},
        )

    # Re-validate availability against the freshly locked rows.
    shortfalls: list[dict] = []
    for s in plan.shipments:
        for ln in s.lines:
            row = stock_by_key.get((ln.product_id, s.warehouse_id))
            free = (row.on_hand - row.reserved) if row else 0
            if free < ln.quantity:
                shortfalls.append(
                    {
                        "line_id": ln.line_id,
                        "product_id": ln.product_id,
                        "warehouse_id": s.warehouse_id,
                        "requested": ln.quantity,
                        "available": max(0, free),
                    }
                )
    if shortfalls:
        raise ConflictException(
            "Stock moved under this plan — some lines can no longer be reserved.",
            code=ErrorCode.INSUFFICIENT_STOCK,
            extra={"shortfalls": shortfalls},
        )

    if quotation.status == QuoteStatus.FULFILLING.value:
        _clear_existing_fulfillment(db, quotation)

    restock_at = datetime.now(timezone.utc) + timedelta(days=DEFAULT_RESTOCK_DAYS)
    _persist_allocation(
        db,
        quotation,
        shipments=[
            (s.warehouse_id, s.shipping_cost_weight, [(ln.line_id, ln.product_id, ln.quantity) for ln in s.lines])
            for s in plan.shipments
        ],
        backorders=[(b.line_id, b.product_id, b.quantity) for b in plan.backorders],
        stock_by_key=stock_by_key,
        restock_at=restock_at,
    )
    _set_fulfillment_status(quotation, bool(plan.backorders), bool(plan.shipments))

    record_event(
        db,
        quotation,
        EventType.QUOTE_FULFILLMENT_PLANNED,
        actor,
        summary=(
            f"{actor.full_name} accepted a fulfilment plan: {len(plan.shipments)} shipment(s)"
            + (f", {len(plan.backorders)} backordered line(s)" if plan.backorders else "")
            + "."
        ),
        payload={
            "plan_hash": plan.plan_hash,
            "shipment_count": len(plan.shipments),
            "backorder_count": len(plan.backorders),
        },
    )
    if quotation.status == QuoteStatus.CONFIRMED.value:
        transition(db, quotation, QuoteStatus.FULFILLING.value, actor, expected_version=quotation.version)

    db.commit()
    db.refresh(quotation)
    return quotation


def override_plan(
    db: Session, quotation: Quotation, expected_version: int, allocations: list[AllocationInput], actor: User
) -> Quotation:
    _require_fulfillable(quotation)
    if expected_version != quotation.version:
        raise ConflictException(
            "This quotation changed since you loaded it.",
            code=ErrorCode.VERSION_CONFLICT,
            extra={"current_version": quotation.version},
        )

    lines_by_id = {line.id: line for line in quotation.lines}
    per_line: dict[int, int] = {}
    for alloc in allocations:
        if alloc.line_id not in lines_by_id:
            raise ValidationException(f"Line {alloc.line_id} is not on this quotation.")
        if alloc.quantity <= 0:
            raise ValidationException("Allocation quantity must be positive.")
        per_line[alloc.line_id] = per_line.get(alloc.line_id, 0) + alloc.quantity

    for line_id, total in per_line.items():
        if total > lines_by_id[line_id].quantity:
            raise ValidationException(
                f"Line {line_id}: allocated {total} exceeds ordered {lines_by_id[line_id].quantity}."
            )

    product_ids = {line.product_id for line in quotation.lines if line.line_type == "one_time"}
    stock_rows, warehouses = _load_stock_and_warehouses(db, product_ids, lock=True)
    stock_by_key = {(s.product_id, s.warehouse_id): s for s in stock_rows}
    weight_by_wh = {w.id: w.shipping_cost_weight for w in warehouses}

    if quotation.status == QuoteStatus.FULFILLING.value:
        _clear_existing_fulfillment(db, quotation)

    # Group allocations into shipments per warehouse, checking availability.
    grouped: dict[int, list[tuple[int, int, int]]] = {}
    shortfalls: list[dict] = []
    for alloc in allocations:
        line = lines_by_id[alloc.line_id]
        row = stock_by_key.get((line.product_id, alloc.warehouse_id))
        free = (row.on_hand - row.reserved) if row else 0
        if free < alloc.quantity:
            shortfalls.append(
                {
                    "line_id": alloc.line_id,
                    "product_id": line.product_id,
                    "warehouse_id": alloc.warehouse_id,
                    "requested": alloc.quantity,
                    "available": max(0, free),
                }
            )
            continue
        grouped.setdefault(alloc.warehouse_id, []).append((alloc.line_id, line.product_id, alloc.quantity))
        if row is not None:
            row.reserved += alloc.quantity  # tentative — rolled back with the txn on shortfall

    if shortfalls:
        db.rollback()
        raise ConflictException(
            "One or more manual allocations exceed available stock.",
            code=ErrorCode.INSUFFICIENT_STOCK,
            extra={"shortfalls": shortfalls},
        )

    # `row.reserved` was already incremented above; persist rows without touching it again.
    restock_at = datetime.now(timezone.utc) + timedelta(days=DEFAULT_RESTOCK_DAYS)
    for warehouse_id, lines in grouped.items():
        shipment = Shipment(
            quotation_id=quotation.id,
            warehouse_id=warehouse_id,
            status=ShipmentStatus.PLANNED.value,
            estimated_cost_minor=weight_by_wh.get(warehouse_id, 0) * 5_000,
        )
        db.add(shipment)
        db.flush()
        for line_id, product_id, qty in lines:
            db.add(ShipmentLine(shipment_id=shipment.id, line_id=line_id, product_id=product_id, quantity=qty))
            db.add(
                StockReservation(
                    quotation_id=quotation.id,
                    line_id=line_id,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=qty,
                    status=ReservationStatus.HELD.value,
                )
            )

    backordered: list[tuple[int, int, int]] = []
    for line in quotation.lines:
        if line.line_type != "one_time":
            continue
        shortfall = line.quantity - per_line.get(line.id, 0)
        if shortfall > 0:
            backordered.append((line.id, line.product_id, shortfall))
            db.add(
                Backorder(
                    quotation_id=quotation.id,
                    line_id=line.id,
                    product_id=line.product_id,
                    quantity=shortfall,
                    status=BackorderStatus.OPEN.value,
                    expected_restock_at=restock_at,
                )
            )

    _set_fulfillment_status(quotation, bool(backordered), bool(grouped))
    record_event(
        db,
        quotation,
        EventType.QUOTE_FULFILLMENT_OVERRIDDEN,
        actor,
        summary=f"{actor.full_name} manually overrode the fulfilment plan ({len(grouped)} shipment(s)).",
        payload={"shipment_count": len(grouped), "backorder_count": len(backordered)},
    )
    if quotation.status == QuoteStatus.CONFIRMED.value:
        transition(db, quotation, QuoteStatus.FULFILLING.value, actor, expected_version=quotation.version)

    db.commit()
    db.refresh(quotation)
    return quotation


def consolidate_backorders(db: Session, quotation: Quotation, expected_version: int, actor: User) -> Quotation:
    if expected_version != quotation.version:
        raise ConflictException(
            "This quotation changed since you loaded it.",
            code=ErrorCode.VERSION_CONFLICT,
            extra={"current_version": quotation.version},
        )
    open_backorders = db.scalars(
        select(Backorder).where(
            Backorder.quotation_id == quotation.id, Backorder.status == BackorderStatus.OPEN.value
        )
    ).all()
    if not open_backorders:
        raise ValidationException("This quotation has no open backorders to consolidate.")

    product_ids = {b.product_id for b in open_backorders}
    stock_rows, warehouses = _load_stock_and_warehouses(db, product_ids, lock=True)
    stock_by_key = {(s.product_id, s.warehouse_id): s for s in stock_rows}
    weight_by_wh = {w.id: w.shipping_cost_weight for w in warehouses}
    ranked_wh = sorted(warehouses, key=lambda w: (w.shipping_cost_weight, w.id))

    fulfilled: list[Backorder] = []
    plan_lines: dict[int, list[tuple[int, int, int]]] = {}
    for bo in open_backorders:
        remaining = bo.quantity
        for w in ranked_wh:
            if remaining <= 0:
                break
            row = stock_by_key.get((bo.product_id, w.id))
            free = (row.on_hand - row.reserved) if row else 0
            take = min(remaining, free)
            if take <= 0:
                continue
            plan_lines.setdefault(w.id, []).append((bo.line_id, bo.product_id, take))
            row.reserved += take
            db.add(
                StockReservation(
                    quotation_id=quotation.id,
                    line_id=bo.line_id,
                    product_id=bo.product_id,
                    warehouse_id=w.id,
                    quantity=take,
                    status=ReservationStatus.HELD.value,
                )
            )
            remaining -= take
        if remaining <= 0:
            bo.status = BackorderStatus.CONSOLIDATED.value
            fulfilled.append(bo)
        else:
            bo.quantity = remaining  # partial — keep the shortfall open

    if not plan_lines:
        db.rollback()
        raise ConflictException(
            "Stock has not arrived — nothing to consolidate yet.",
            code=ErrorCode.INSUFFICIENT_STOCK,
        )

    for warehouse_id, lines in plan_lines.items():
        shipment = Shipment(
            quotation_id=quotation.id,
            warehouse_id=warehouse_id,
            status=ShipmentStatus.PLANNED.value,
            estimated_cost_minor=weight_by_wh.get(warehouse_id, 0) * 5_000,
        )
        db.add(shipment)
        db.flush()
        for line_id, product_id, qty in lines:
            db.add(ShipmentLine(shipment_id=shipment.id, line_id=line_id, product_id=product_id, quantity=qty))

    still_open = db.scalar(
        select(Backorder).where(
            Backorder.quotation_id == quotation.id, Backorder.status == BackorderStatus.OPEN.value
        )
    )
    _set_fulfillment_status(quotation, still_open is not None, True)
    record_event(
        db,
        quotation,
        EventType.QUOTE_BACKORDER_CONSOLIDATED,
        actor,
        summary=f"{actor.full_name} consolidated {len(fulfilled)} backordered line(s) into a new shipment.",
        payload={"consolidated": len(fulfilled), "shipments": len(plan_lines)},
    )
    db.commit()
    db.refresh(quotation)
    return quotation


def get_quotation_or_404(db: Session, quotation_id: int) -> Quotation:
    quotation = db.get(Quotation, quotation_id)
    if quotation is None:
        raise NotFoundException("Quotation not found")
    return quotation
