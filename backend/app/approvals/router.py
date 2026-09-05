from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.approvals.schemas import ApprovalActRequest, ApprovalRead
from app.core.deps import CurrentUser
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse
from app.core.stub import not_implemented
from app.quotations.schemas import QuotationRead

router = APIRouter()

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


@router.get("/queue", response_model=SuccessResponse[Page[ApprovalRead]])
def approval_queue(
    current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    level: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
):
    not_implemented()


@router.get("/{approval_id}", response_model=SuccessResponse[ApprovalRead])
def get_approval(approval_id: int, current_user: CurrentUser):
    not_implemented()


@router.post("/{approval_id}/act", response_model=SuccessResponse[QuotationRead])
def act_on_approval(
    approval_id: int,
    payload: ApprovalActRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
):
    """Guarded by `approvals:l1` / `approvals:l2` matching the row's own level — decided
    at runtime once the approval is loaded, so it isn't a static route dependency."""
    not_implemented()
