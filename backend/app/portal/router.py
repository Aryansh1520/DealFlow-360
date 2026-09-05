from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.deps import CurrentPrincipal, get_current_customer
from app.core.idempotency import begin_idempotent, finish_idempotent
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.core.security import CUSTOMER, create_access_token, create_refresh_token
from app.core.tenant_context import set_current_org
from app.db.session import get_db
from app.portal import magic_link, service
from app.portal.schemas import (
    MagicLinkRedeemRequest,
    MagicLinkRedeemResponse,
    PortalCommentRequest,
    PortalConfirmRequest,
    PortalConfirmResponse,
    PortalCounterRequest,
    PortalQuotationRead,
)

router = APIRouter(dependencies=[Depends(get_current_customer)])

# `/portal/magic-link/redeem` is how a customer principal is *born*, so it can't sit
# behind the customer guard.
public_router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


@public_router.post("/magic-link/redeem", response_model=SuccessResponse[MagicLinkRedeemResponse])
def redeem_magic_link(payload: MagicLinkRedeemRequest, db: DbSession):
    link = magic_link.redeem(db, payload.token)
    set_current_org(db, link.org_id)
    db.commit()
    body = MagicLinkRedeemResponse(
        access_token=create_access_token(link.customer_id, CUSTOMER),
        refresh_token=create_refresh_token(link.customer_id, CUSTOMER),
        user_type=CUSTOMER,
        quotation_id=link.quotation_id,
    )
    return ok(body, "Link redeemed.")


@router.get("/quotations", response_model=SuccessResponse[Page[PortalQuotationRead]])
def list_my_quotations(
    principal: CurrentPrincipal, db: DbSession, params: Annotated[PageParams, Depends()]
):
    rows, total = service.list_my_quotations(db, principal, params)
    return ok(Page[PortalQuotationRead].create(rows, total, params), "Quotations retrieved.")


@router.get("/quotations/{quotation_id}", response_model=SuccessResponse[PortalQuotationRead])
def get_my_quotation(quotation_id: int, principal: CurrentPrincipal, db: DbSession):
    return ok(service.get_my_quotation(db, quotation_id, principal), "Quotation retrieved.")


@router.post(
    "/quotations/{quotation_id}/comments", response_model=SuccessResponse[PortalQuotationRead]
)
def add_comment(
    quotation_id: int, payload: PortalCommentRequest, principal: CurrentPrincipal, db: DbSession
):
    return ok(service.add_comment(db, quotation_id, principal, payload), "Comment recorded.")


@router.post(
    "/quotations/{quotation_id}/counter", response_model=SuccessResponse[PortalQuotationRead]
)
def counter_offer(
    quotation_id: int, payload: PortalCounterRequest, principal: CurrentPrincipal, db: DbSession
):
    return ok(service.counter_offer(db, quotation_id, principal, payload), "Counter-offer recorded.")


@router.post(
    "/quotations/{quotation_id}/confirm", response_model=SuccessResponse[PortalConfirmResponse]
)
async def confirm_quotation(
    quotation_id: int,
    payload: PortalConfirmRequest,
    principal: CurrentPrincipal,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "portal.confirm"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    status, re_entered = service.confirm(db, quotation_id, principal, payload.expected_version)
    response = ok(
        PortalConfirmResponse(status=status, re_entered_approval=re_entered),
        "Quotation confirmed." if not re_entered else "Quotation re-entered approval.",
    )
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
