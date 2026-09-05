from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.approvals import service
from app.approvals.models import QuoteApproval
from app.approvals.schemas import ApprovalActRequest, ApprovalRead
from app.core.deps import CurrentUser
from app.core.idempotency import begin_idempotent, finish_idempotent
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.quotations.schemas import QuotationRead
from app.quotations.serialization import compute_quotation, to_quotation_read

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


def _to_approval_read(db: Session, approval: QuoteApproval) -> ApprovalRead:
    quotation = approval.quotation
    computation = compute_quotation(db, quotation)
    return ApprovalRead(
        id=approval.id,
        quotation_id=quotation.id,
        quotation_reference=quotation.reference,
        customer_name=quotation.customer.name,
        total_minor=computation.total_minor,
        currency=quotation.currency,
        level=approval.level,
        sequence=approval.sequence,
        status=approval.status,
        risk_score=approval.risk_score,
        acted_by_id=approval.acted_by_id,
        acted_by_name=approval.acted_by.full_name if approval.acted_by else None,
        reason=approval.reason,
        acted_at=approval.acted_at,
        created_at=approval.created_at,
    )


@router.get("/queue", response_model=SuccessResponse[Page[ApprovalRead]])
def approval_queue(
    current_user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    level: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
):
    stmt = select(QuoteApproval)
    if level:
        stmt = stmt.where(QuoteApproval.level == level)
    if status:
        stmt = stmt.where(QuoteApproval.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(QuoteApproval.created_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()
    items = [_to_approval_read(db, a) for a in rows]
    page = Page[ApprovalRead].create(items, total, params)
    return ok(page, "Approval queue retrieved successfully.")


@router.get("/{approval_id}", response_model=SuccessResponse[ApprovalRead])
def get_approval(approval_id: int, current_user: CurrentUser, db: DbSession):
    approval = service.get_approval_or_404(db, approval_id)
    return ok(_to_approval_read(db, approval), "Approval retrieved successfully.")


@router.post("/{approval_id}/act", response_model=SuccessResponse[QuotationRead])
async def act_on_approval(
    approval_id: int,
    payload: ApprovalActRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    """Guarded by `approvals:l1` / `approvals:l2` matching the row's own level — decided
    at runtime once the approval is loaded, so it isn't a static route dependency."""
    endpoint = "approvals.act"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())

    approval = service.get_approval_or_404(db, approval_id)
    service.require_level_permission(current_user, approval.level)
    quotation = service.act_on_approval(db, approval, payload.action, payload.reason, current_user)

    response = ok(to_quotation_read(db, quotation), "Approval action recorded successfully.")
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
