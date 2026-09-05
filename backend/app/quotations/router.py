from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.core.deps import require_permissions
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse
from app.core.stub import not_implemented
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

router = APIRouter()

QuotationsRead = Depends(require_permissions("quotations:read"))
QuotationsWrite = Depends(require_permissions("quotations:write"))
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]


@router.get("", response_model=SuccessResponse[Page[QuotationRead]], dependencies=[QuotationsRead])
def list_quotations(
    params: Annotated[PageParams, Depends()],
    status: Annotated[str | None, Query()] = None,
    owner_rep_id: Annotated[int | None, Query()] = None,
    customer_id: Annotated[int | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
):
    not_implemented()


@router.post("", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite])
def create_quotation(payload: QuotationCreate):
    not_implemented()


@router.get("/{quotation_id}", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsRead])
def get_quotation(quotation_id: int):
    not_implemented()


@router.patch("/{quotation_id}", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite])
def update_quotation(quotation_id: int, payload: QuotationUpdate):
    not_implemented()


@router.post(
    "/{quotation_id}/lines", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite]
)
def add_line(quotation_id: int, payload: QuoteLineCreate):
    not_implemented()


@router.patch(
    "/{quotation_id}/lines/{line_id}",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[QuotationsWrite],
)
def update_line(quotation_id: int, line_id: int, payload: QuoteLineUpdate):
    not_implemented()


@router.delete(
    "/{quotation_id}/lines/{line_id}",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[QuotationsWrite],
)
def remove_line(quotation_id: int, line_id: int, expected_version: Annotated[int, Query()]):
    not_implemented()


@router.post(
    "/{quotation_id}/preview", response_model=SuccessResponse[QuoteComputation], dependencies=[QuotationsWrite]
)
def preview_quotation(quotation_id: int, payload: PreviewRequest):
    """Dry run — writes nothing. Mirrors the current *unsaved* editor state."""
    not_implemented()


@router.post(
    "/{quotation_id}/submit", response_model=SuccessResponse[QuotationRead], dependencies=[QuotationsWrite]
)
def submit_quotation(quotation_id: int, payload: SubmitRequest, idempotency_key: IdempotencyKey):
    not_implemented()


@router.post(
    "/{quotation_id}/transition",
    response_model=SuccessResponse[QuotationRead],
    dependencies=[QuotationsWrite],
)
def transition_quotation(quotation_id: int, payload: TransitionRequest, idempotency_key: IdempotencyKey):
    not_implemented()


@router.get(
    "/{quotation_id}/events",
    response_model=SuccessResponse[Page[QuoteEventRead]],
    dependencies=[QuotationsRead],
)
def list_events(quotation_id: int, params: Annotated[PageParams, Depends()]):
    not_implemented()


@router.get(
    "/{quotation_id}/decision-trace",
    response_model=SuccessResponse[DecisionTrace],
    dependencies=[QuotationsRead],
)
def get_decision_trace(quotation_id: int):
    not_implemented()


@router.get(
    "/{quotation_id}/suggestions",
    response_model=SuccessResponse[list[SuggestionRead]],
    dependencies=[QuotationsRead],
)
def get_suggestions(quotation_id: int, limit: Annotated[int, Query(ge=1, le=20)] = 5):
    not_implemented()


@router.post(
    "/{quotation_id}/suggestions/{product_id}/dismiss",
    response_model=SuccessResponse[None],
    dependencies=[QuotationsWrite],
)
def dismiss_suggestion(quotation_id: int, product_id: int):
    not_implemented()
