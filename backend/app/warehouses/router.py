from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.crud import CRUDBase
from app.core.deps import CurrentUser, require_permissions
from app.core.exceptions import BadRequestException, ConflictException
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.warehouses.models import Stock, StockMovement, Warehouse
from app.warehouses.schemas import (
    StockAdjustRequest,
    StockRead,
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

warehouse_crud = CRUDBase(Warehouse, search_fields=["name", "code"])

WarehousesRead = Depends(require_permissions("warehouses:read"))
WarehousesWrite = Depends(require_permissions("warehouses:write"))


@router.get("", response_model=SuccessResponse[Page[WarehouseRead]], dependencies=[WarehousesRead])
def list_warehouses(db: DbSession, params: Annotated[PageParams, Depends()]):
    items, total = warehouse_crud.list(db, params=params)
    return ok(Page[WarehouseRead].create(items, total, params), "Warehouses retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[WarehouseRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[WarehousesWrite],
)
def create_warehouse(payload: WarehouseCreate, db: DbSession):
    if db.scalar(select(Warehouse).where(Warehouse.code == payload.code)):
        raise ConflictException("A warehouse with this code already exists")
    warehouse = warehouse_crud.create(db, payload.model_dump())
    return ok(warehouse, "Warehouse created successfully.")


@router.get("/{warehouse_id}", response_model=SuccessResponse[WarehouseRead], dependencies=[WarehousesRead])
def get_warehouse(warehouse_id: int, db: DbSession):
    return ok(warehouse_crud.get_or_404(db, warehouse_id), "Warehouse retrieved successfully.")


@router.patch("/{warehouse_id}", response_model=SuccessResponse[WarehouseRead], dependencies=[WarehousesWrite])
def update_warehouse(warehouse_id: int, payload: WarehouseUpdate, db: DbSession):
    warehouse = warehouse_crud.get_or_404(db, warehouse_id)
    updated = warehouse_crud.update(db, warehouse, payload.model_dump(exclude_unset=True))
    return ok(updated, "Warehouse updated successfully.")


@router.delete("/{warehouse_id}", response_model=SuccessResponse[None], dependencies=[WarehousesWrite])
def delete_warehouse(warehouse_id: int, db: DbSession):
    warehouse = warehouse_crud.get_or_404(db, warehouse_id)
    warehouse_crud.delete(db, warehouse)
    return ok(None, "Warehouse deleted successfully.")


@router.get(
    "/{warehouse_id}/stock",
    response_model=SuccessResponse[Page[StockRead]],
    dependencies=[WarehousesRead],
)
def get_warehouse_stock(warehouse_id: int, db: DbSession, params: Annotated[PageParams, Depends()]):
    warehouse_crud.get_or_404(db, warehouse_id)
    stmt = select(Stock).where(Stock.warehouse_id == warehouse_id)
    total = db.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0
    rows = db.scalars(
        stmt.order_by(Stock.id).offset((params.page - 1) * params.page_size).limit(params.page_size)
    ).all()
    page = Page[StockRead].create([StockRead.from_model(s) for s in rows], total, params)
    return ok(page, "Stock retrieved successfully.")


stock_router = APIRouter()


@stock_router.post(
    "/adjust",
    response_model=SuccessResponse[StockRead],
    dependencies=[WarehousesWrite],
)
def adjust_stock(payload: StockAdjustRequest, db: DbSession, current_user: CurrentUser):
    stock = db.scalar(
        select(Stock).where(
            Stock.product_id == payload.product_id, Stock.warehouse_id == payload.warehouse_id
        )
    )
    if stock is None:
        stock = Stock(
            product_id=payload.product_id, warehouse_id=payload.warehouse_id, on_hand=0, reserved=0
        )
        db.add(stock)
        db.flush()

    new_on_hand = stock.on_hand + payload.delta
    if new_on_hand < 0:
        raise BadRequestException("Adjustment would drive on-hand stock below zero")

    stock.on_hand = new_on_hand
    db.add(
        StockMovement(
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            delta=payload.delta,
            reason=payload.reason,
            actor_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(stock)
    return ok(StockRead.from_model(stock), "Stock adjusted successfully.")
