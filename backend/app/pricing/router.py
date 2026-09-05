from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.crud import CRUDBase
from app.core.deps import require_permissions
from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.pricing.models import PriceList, PriceListEntry
from app.pricing.schemas import (
    PriceListCreate,
    PriceListEntryCreate,
    PriceListEntryRead,
    PriceListEntryUpdate,
    PriceListRead,
    PriceListUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

price_list_crud = CRUDBase(PriceList, search_fields=["name"])
entry_crud = CRUDBase(PriceListEntry)

PricingRead = Depends(require_permissions("pricing:read"))
PricingWrite = Depends(require_permissions("pricing:write"))


@router.get("", response_model=SuccessResponse[Page[PriceListRead]], dependencies=[PricingRead])
def list_price_lists(db: DbSession, params: Annotated[PageParams, Depends()]):
    items, total = price_list_crud.list(db, params=params)
    return ok(Page[PriceListRead].create(items, total, params), "Price lists retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[PriceListRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[PricingWrite],
)
def create_price_list(payload: PriceListCreate, db: DbSession):
    price_list = price_list_crud.create(db, payload.model_dump())
    return ok(price_list, "Price list created successfully.")


@router.get("/{price_list_id}", response_model=SuccessResponse[PriceListRead], dependencies=[PricingRead])
def get_price_list(price_list_id: int, db: DbSession):
    return ok(price_list_crud.get_or_404(db, price_list_id), "Price list retrieved successfully.")


@router.patch("/{price_list_id}", response_model=SuccessResponse[PriceListRead], dependencies=[PricingWrite])
def update_price_list(price_list_id: int, payload: PriceListUpdate, db: DbSession):
    price_list = price_list_crud.get_or_404(db, price_list_id)
    updated = price_list_crud.update(db, price_list, payload.model_dump(exclude_unset=True))
    return ok(updated, "Price list updated successfully.")


@router.delete("/{price_list_id}", response_model=SuccessResponse[None], dependencies=[PricingWrite])
def delete_price_list(price_list_id: int, db: DbSession):
    price_list = price_list_crud.get_or_404(db, price_list_id)
    price_list_crud.delete(db, price_list)
    return ok(None, "Price list deleted successfully.")


# ---- Entries (nested under price list) -------------------------------------------

@router.get(
    "/{price_list_id}/entries",
    response_model=SuccessResponse[Page[PriceListEntryRead]],
    dependencies=[PricingRead],
)
def list_entries(price_list_id: int, db: DbSession, params: Annotated[PageParams, Depends()]):
    price_list_crud.get_or_404(db, price_list_id)
    items, total = entry_crud.list(db, params=params, filters={"price_list_id": price_list_id})
    return ok(Page[PriceListEntryRead].create(items, total, params), "Entries retrieved successfully.")


@router.post(
    "/{price_list_id}/entries",
    response_model=SuccessResponse[PriceListEntryRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[PricingWrite],
)
def create_entry(price_list_id: int, payload: PriceListEntryCreate, db: DbSession):
    price_list_crud.get_or_404(db, price_list_id)
    existing = db.query(PriceListEntry).filter_by(
        price_list_id=price_list_id,
        product_id=payload.product_id,
        variant_id=payload.variant_id,
    ).first()
    if existing:
        raise ConflictException("An entry for this product/variant already exists in this price list")
    entry = entry_crud.create(db, {**payload.model_dump(), "price_list_id": price_list_id})
    return ok(entry, "Entry created successfully.")


@router.patch(
    "/{price_list_id}/entries/{entry_id}",
    response_model=SuccessResponse[PriceListEntryRead],
    dependencies=[PricingWrite],
)
def update_entry(price_list_id: int, entry_id: int, payload: PriceListEntryUpdate, db: DbSession):
    entry = entry_crud.get_or_404(db, entry_id)
    if entry.price_list_id != price_list_id:
        raise NotFoundException("Entry not found for this price list")
    updated = entry_crud.update(db, entry, payload.model_dump(exclude_unset=True))
    return ok(updated, "Entry updated successfully.")


@router.delete(
    "/{price_list_id}/entries/{entry_id}",
    response_model=SuccessResponse[None],
    dependencies=[PricingWrite],
)
def delete_entry(price_list_id: int, entry_id: int, db: DbSession):
    entry = entry_crud.get_or_404(db, entry_id)
    if entry.price_list_id != price_list_id:
        raise NotFoundException("Entry not found for this price list")
    entry_crud.delete(db, entry)
    return ok(None, "Entry deleted successfully.")
