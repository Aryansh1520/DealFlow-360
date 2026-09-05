from typing import Annotated

from fastapi import APIRouter, Header

from app.core.deps import CurrentUser
from app.core.responses import SuccessResponse
from app.core.stub import not_implemented
from app.fulfillment.schemas import (
    FulfillmentAcceptRequest,
    FulfillmentConsolidateRequest,
    FulfillmentOverrideRequest,
    FulfillmentPlan,
)
from app.quotations.schemas import QuotationRead

router = APIRouter()

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


@router.get("/{quotation_id}/fulfillment/plan", response_model=SuccessResponse[FulfillmentPlan])
def get_fulfillment_plan(quotation_id: int, current_user: CurrentUser):
    """Computed live, writes nothing."""
    not_implemented()


@router.post("/{quotation_id}/fulfillment/accept", response_model=SuccessResponse[QuotationRead])
def accept_fulfillment_plan(
    quotation_id: int,
    payload: FulfillmentAcceptRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
):
    not_implemented()


@router.post("/{quotation_id}/fulfillment/override", response_model=SuccessResponse[QuotationRead])
def override_fulfillment_plan(
    quotation_id: int,
    payload: FulfillmentOverrideRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
):
    not_implemented()


@router.post("/{quotation_id}/fulfillment/consolidate", response_model=SuccessResponse[QuotationRead])
def consolidate_backorders(
    quotation_id: int,
    payload: FulfillmentConsolidateRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
):
    not_implemented()
