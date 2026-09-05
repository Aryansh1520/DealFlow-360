from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.affinity.service import get_suggestions as compute_suggestions
from app.approvals.service import submit as submit_quotation_service
from app.core.deps import CurrentUser, require_permissions
from app.core.enums import EventType
from app.core.idempotency import begin_idempotent, finish_idempotent
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.events.models import QuoteEvent
from app.events.service import record_event
from app.quotations import service
from app.quotations.schemas import (
    DecisionTrace,
    PreviewRequest,
    QuoteComputation,
    QuoteEventRead,
    QuoteLineCreate,
    QuoteLineUpdate,
    QuotationCreate,
    QuotationRead,
    QuotationUpdate,
    SubmitRequest,
    SuggestionRead,
    TransitionRequest,
)
from app.quotations.serialization import compute_quotation, to_quotation_read
from app.quotations.transitions import transition as transition_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
QuotationsRead = Depends(require_permissions("quotations:read"))
QuotationsWrite = Depends(require_permissions("quotations:write"))
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


@router.get("", response_model=SuccessResponse[Page[QuotationRead]], dependencies=[QuotationsRead])
def list_quotations(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    status: Annotated[str | None, Query()] = None,
    owner_rep_id: Annotated[int | None, Query()] = None,
    customer_id: Annotated[int | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
):
    items, total = service.list_quotations(
        db, params=params, status=status or stage, owner_rep_id=owner_rep_id, customer_id=customer_id, q=q
    )
    page = Page[QuotationRead].create([to_quotation_read(db, q_) for q_ in items], total, params)
    return ok(page, "Quotations retrieved successfully.")


@router.post("", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite])
def create_quotation(payload: QuotationCreate, db: DbSession, current_user: CurrentUser):
    quotation = service.create_quotation(db, payload, current_user)
    return ok(to_quotation_read(db, quotation), "Quotation created successfully.")


@router.get("/{quotation_id}", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsRead])
def get_quotation(quotation_id: int, db: DbSession):
    quotation = service.get_quotation_or_404(db, quotation_id)
    return ok(to_quotation_read(db, quotation), "Quotation retrieved successfully.")


@router.patch("/{quotation_id}", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite])
def update_quotation(quotation_id: int, payload: QuotationUpdate, db: DbSession, current_user: CurrentUser):
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.update_quotation(db, quotation, payload, current_user)
    return ok(to_quotation_read(db, updated), "Quotation updated successfully.")


@router.post(
    "/{quotation_id}/lines", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite]
)
def add_line(quotation_id: int, payload: QuoteLineCreate, db: DbSession, current_user: CurrentUser):
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.add_line(db, quotation, payload, current_user)
    return ok(to_quotation_read(db, updated), "Line added successfully.")


@router.patch(
    "/{quotation_id}/lines/{line_id}",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[QuotationsWrite],
)
def update_line(quotation_id: int, line_id: int, payload: QuoteLineUpdate, db: DbSession, current_user: CurrentUser):
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.update_line(db, quotation, line_id, payload, current_user)
    return ok(to_quotation_read(db, updated), "Line updated successfully.")


@router.delete(
    "/{quotation_id}/lines/{line_id}",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[QuotationsWrite],
)
def remove_line(
    quotation_id: int, line_id: int, expected_version: Annotated[int, Query()], db: DbSession, current_user: CurrentUser
):
    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = service.remove_line(db, quotation, line_id, expected_version, current_user)
    return ok(to_quotation_read(db, updated), "Line removed successfully.")


@router.post(
    "/{quotation_id}/preview", response_model=SuccessResponse[QuoteComputation], dependencies=[QuotationsWrite]
)
def preview_quotation(quotation_id: int, payload: PreviewRequest, db: DbSession):
    """Dry run — writes nothing. Mirrors the current *unsaved* editor state."""
    quotation = service.get_quotation_or_404(db, quotation_id)
    computation = service.preview(db, quotation, payload)
    return ok(computation, "Preview computed successfully.")


@router.post(
    "/{quotation_id}/submit", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite]
)
async def submit_quotation(
    quotation_id: int, payload: SubmitRequest, idempotency_key: IdempotencyKey, request: Request, db: DbSession, current_user: CurrentUser
):
    endpoint = "quotations.submit"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())

    quotation = service.get_quotation_or_404(db, quotation_id)
    updated = submit_quotation_service(db, quotation, current_user, payload.expected_version)
    response = ok(to_quotation_read(db, updated), "Quotation submitted successfully.")
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
    "/{quotation_id}/transition",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[QuotationsWrite],
)
async def transition_quotation(
    quotation_id: int, payload: TransitionRequest, idempotency_key: IdempotencyKey, request: Request, db: DbSession, current_user: CurrentUser
):
    endpoint = "quotations.transition"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())

    quotation = service.get_quotation_or_404(db, quotation_id)
    transition_service(
        db,
        quotation,
        payload.to_status,
        current_user,
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(quotation)
    response = ok(to_quotation_read(db, quotation), "Quotation transitioned successfully.")
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


@router.get(
    "/{quotation_id}/events",
    response_model=SuccessResponse[Page[QuoteEventRead]],
    dependencies=[QuotationsRead],
)
def list_events(quotation_id: int, db: DbSession, params: Annotated[PageParams, Depends()]):
    service.get_quotation_or_404(db, quotation_id)
    stmt = select(QuoteEvent).where(QuoteEvent.quotation_id == quotation_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(QuoteEvent.created_at.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()
    page = Page[QuoteEventRead].create(rows, total, params)
    return ok(page, "Events retrieved successfully.")


@router.get(
    "/{quotation_id}/decision-trace",
    response_model=SuccessResponse[DecisionTrace],
    dependencies=[QuotationsRead],
)
def get_decision_trace(quotation_id: int, db: DbSession):
    quotation = service.get_quotation_or_404(db, quotation_id)
    computation = compute_quotation(db, quotation)
    return ok(computation.trace, "Decision trace retrieved successfully.")


@router.get(
    "/{quotation_id}/suggestions",
    response_model=SuccessResponse[list[SuggestionRead]],
    dependencies=[QuotationsRead],
)
def get_suggestions(quotation_id: int, db: DbSession, limit: Annotated[int, Query(ge=1, le=20)] = 5):
    quotation = service.get_quotation_or_404(db, quotation_id)
    dismissed_rows = db.scalars(
        select(QuoteEvent.payload).where(
            QuoteEvent.quotation_id == quotation_id, QuoteEvent.event_type == EventType.QUOTE_UPSELL_DISMISSED.value
        )
    ).all()
    dismissed_product_ids = {row.get("product_id") for row in dismissed_rows if row.get("product_id") is not None}
    suggestions = compute_suggestions(db, quotation, limit=limit, dismissed_product_ids=dismissed_product_ids)
    return ok(suggestions, "Suggestions retrieved successfully.")


@router.post(
    "/{quotation_id}/suggestions/{product_id}/dismiss",
    response_model=SuccessResponse[None],
    dependencies=[QuotationsWrite],
)
def dismiss_suggestion(quotation_id: int, product_id: int, db: DbSession, current_user: CurrentUser):
    quotation = service.get_quotation_or_404(db, quotation_id)
    record_event(
        db,
        quotation,
        EventType.QUOTE_UPSELL_DISMISSED,
        current_user,
        summary=f"{current_user.full_name} dismissed an upsell suggestion.",
        payload={"product_id": product_id},
    )
    db.commit()
    return ok(None, "Suggestion dismissed.")
