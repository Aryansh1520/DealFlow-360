from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core.deps import CurrentCustomer
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse
from app.core.stub import not_implemented
from app.portal.schemas import (
    MagicLinkRedeemRequest,
    MagicLinkRedeemResponse,
    PortalCommentRequest,
    PortalConfirmRequest,
    PortalConfirmResponse,
    PortalCounterRequest,
    PortalQuotationRead,
)

router = APIRouter()

# `/portal/magic-link/redeem` is unauthenticated (it's how a customer principal is
# born), so it lives on its own router mounted without the `CurrentCustomer` guard.
public_router = APIRouter()

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


@public_router.post("/magic-link/redeem", response_model=SuccessResponse[MagicLinkRedeemResponse])
def redeem_magic_link(payload: MagicLinkRedeemRequest):
    not_implemented()


@router.get("/quotations", response_model=SuccessResponse[Page[PortalQuotationRead]])
def list_my_quotations(customer: CurrentCustomer, params: Annotated[PageParams, Depends()]):
    not_implemented()


@router.get("/quotations/{quotation_id}", response_model=SuccessResponse[PortalQuotationRead])
def get_my_quotation(quotation_id: int, customer: CurrentCustomer):
    not_implemented()


@router.post("/quotations/{quotation_id}/comments", response_model=SuccessResponse[PortalQuotationRead])
def add_comment(quotation_id: int, payload: PortalCommentRequest, customer: CurrentCustomer):
    not_implemented()


@router.post("/quotations/{quotation_id}/counter", response_model=SuccessResponse[PortalQuotationRead])
def counter_offer(quotation_id: int, payload: PortalCounterRequest, customer: CurrentCustomer):
    not_implemented()


@router.post("/quotations/{quotation_id}/confirm", response_model=SuccessResponse[PortalConfirmResponse])
def confirm_quotation(
    quotation_id: int,
    payload: PortalConfirmRequest,
    customer: CurrentCustomer,
    idempotency_key: IdempotencyKey,
):
    not_implemented()
