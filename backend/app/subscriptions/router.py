from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.crud import CRUDBase
from app.core.deps import require_permissions
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.subscriptions.models import SubscriptionPlan
from app.subscriptions.schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanRead,
    SubscriptionPlanUpdate,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

plan_crud = CRUDBase(SubscriptionPlan, search_fields=["name"])

SubscriptionsRead = Depends(require_permissions("subscriptions:read"))
SubscriptionsWrite = Depends(require_permissions("subscriptions:write"))


@router.get("", response_model=SuccessResponse[Page[SubscriptionPlanRead]], dependencies=[SubscriptionsRead])
def list_plans(db: DbSession, params: Annotated[PageParams, Depends()]):
    items, total = plan_crud.list(db, params=params)
    return ok(Page[SubscriptionPlanRead].create(items, total, params), "Plans retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[SubscriptionPlanRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[SubscriptionsWrite],
)
def create_plan(payload: SubscriptionPlanCreate, db: DbSession):
    plan = plan_crud.create(db, payload.model_dump())
    return ok(plan, "Plan created successfully.")


@router.get("/{plan_id}", response_model=SuccessResponse[SubscriptionPlanRead], dependencies=[SubscriptionsRead])
def get_plan(plan_id: int, db: DbSession):
    return ok(plan_crud.get_or_404(db, plan_id), "Plan retrieved successfully.")


@router.patch("/{plan_id}", response_model=SuccessResponse[SubscriptionPlanRead], dependencies=[SubscriptionsWrite])
def update_plan(plan_id: int, payload: SubscriptionPlanUpdate, db: DbSession):
    plan = plan_crud.get_or_404(db, plan_id)
    updated = plan_crud.update(db, plan, payload.model_dump(exclude_unset=True))
    return ok(updated, "Plan updated successfully.")


@router.delete("/{plan_id}", response_model=SuccessResponse[None], dependencies=[SubscriptionsWrite])
def delete_plan(plan_id: int, db: DbSession):
    plan = plan_crud.get_or_404(db, plan_id)
    plan_crud.delete(db, plan)
    return ok(None, "Plan deleted successfully.")
