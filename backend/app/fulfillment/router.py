from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_permissions
from app.core.idempotency import begin_idempotent, finish_idempotent
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.fulfillment import service
from app.fulfillment.schemas import (
    FulfillmentAcceptRequest,
    FulfillmentConsolidateRequest,
    FulfillmentOverrideRequest,
    FulfillmentPlan,
)
from app.quotations.schemas import QuotationRead
from app.quotations.serialization import to_quotation_read

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]
FulfillmentRead = Depends(require_permissions("fulfillment:read"))
FulfillmentWrite = Depends(require_permissions("fulfillment:write"))


@router.get(
    "/{quotation_id}/fulfillment/plan",
    response_model=SuccessResponse[FulfillmentPlan],
    dependencies=[FulfillmentRead],
)
def get_fulfillment_plan(quotation_id: int, current_user: CurrentUser, db: DbSession):
    """Computed live, writes nothing."""
    quotation = service.get_quotation_or_404(db, quotation_id)
    return ok(service.get_plan(db, quotation), "Fulfilment plan computed.")


@router.post(
    "/{quotation_id}/fulfillment/accept",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[FulfillmentWrite],
)
async def accept_fulfillment_plan(
    quotation_id: int,
    payload: FulfillmentAcceptRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "fulfillment.accept"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.accept_plan(
        db, quotation, payload.expected_version, payload.plan_hash, current_user
    )
    response = ok(to_quotation_read(db, updated), "Fulfilment plan accepted.")
    finish_idempotent(
        db,
        key=idempotency_key,
        endpoint=endpoint,
        request_hash=request_hash,
        status_code=200,
        response_json=jsonable_encoder(response),
    )
    db.commit()
    return response


@router.post(
    "/{quotation_id}/fulfillment/override",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[FulfillmentWrite],
)
async def override_fulfillment_plan(
    quotation_id: int,
    payload: FulfillmentOverrideRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "fulfillment.override"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.override_plan(
        db, quotation, payload.expected_version, payload.allocations, current_user
    )
    response = ok(to_quotation_read(db, updated), "Fulfilment plan overridden.")
    finish_idempotent(
        db,
        key=idempotency_key,
        endpoint=endpoint,
        request_hash=request_hash,
        status_code=200,
        response_json=jsonable_encoder(response),
    )
    db.commit()
    return response


@router.post(
    "/{quotation_id}/fulfillment/consolidate",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[FulfillmentWrite],
)
async def consolidate_backorders(
    quotation_id: int,
    payload: FulfillmentConsolidateRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "fulfillment.consolidate"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.consolidate_backorders(db, quotation, payload.expected_version, current_user)
    response = ok(to_quotation_read(db, updated), "Backorders consolidated.")
    finish_idempotent(
        db,
        key=idempotency_key,
        endpoint=endpoint,
        request_hash=request_hash,
        status_code=200,
        response_json=jsonable_encoder(response),
    )
    db.commit()
    return response
