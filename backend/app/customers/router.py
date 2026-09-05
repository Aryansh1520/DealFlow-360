from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crud import CRUDBase
from app.core.deps import require_permissions
from app.core.exceptions import ConflictException
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.core.security import hash_password
from app.customers.models import Customer
from app.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from app.db.session import get_db

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

customer_crud = CRUDBase(Customer, search_fields=["name", "email", "company"])


def _prepare_customer_data(data: dict) -> dict:
    """Convert the plain `password` field into `hashed_password`."""
    password = data.pop("password", None)
    if password is not None:
        data["hashed_password"] = hash_password(password)
    return data


@router.get(
    "",
    response_model=SuccessResponse[Page[CustomerRead]],
    dependencies=[Depends(require_permissions("customers:read"))],
)
def list_customers(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    tier: Annotated[str | None, Query()] = None,
    portal_enabled: Annotated[bool | None, Query()] = None,
):
    items, total = customer_crud.list(
        db, params=params, filters={"tier": tier, "portal_enabled": portal_enabled}
    )
    return ok(Page[CustomerRead].create(items, total, params), "Customers retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[CustomerRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("customers:write"))],
)
def create_customer(payload: CustomerCreate, db: DbSession):
    if db.scalar(select(Customer).where(Customer.email == payload.email)):
        raise ConflictException("A customer with this email already exists")
    customer = customer_crud.create(db, _prepare_customer_data(payload.model_dump()))
    return ok(customer, "Customer created successfully.")


@router.get(
    "/{customer_id}",
    response_model=SuccessResponse[CustomerRead],
    dependencies=[Depends(require_permissions("customers:read"))],
)
def get_customer(customer_id: int, db: DbSession):
    return ok(customer_crud.get_or_404(db, customer_id), "Customer retrieved successfully.")


@router.patch(
    "/{customer_id}",
    response_model=SuccessResponse[CustomerRead],
    dependencies=[Depends(require_permissions("customers:write"))],
)
def update_customer(customer_id: int, payload: CustomerUpdate, db: DbSession):
    customer = customer_crud.get_or_404(db, customer_id)
    updated = customer_crud.update(
        db, customer, _prepare_customer_data(payload.model_dump(exclude_unset=True))
    )
    return ok(updated, "Customer updated successfully.")


@router.delete(
    "/{customer_id}",
    response_model=SuccessResponse[None],
    dependencies=[Depends(require_permissions("customers:write"))],
)
def delete_customer(customer_id: int, db: DbSession):
    customer = customer_crud.get_or_404(db, customer_id)
    customer_crud.delete(db, customer)
    return ok(None, "Customer deleted successfully.")
