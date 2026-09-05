from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.billing.schemas import (
    BillingScheduleEntry,
    InvoiceRead,
    PaymentRequest,
    SupersedeRequest,
    SupersedeResponse,
)
from app.core.deps import CurrentUser
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse
from app.core.stub import not_implemented

router = APIRouter()

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]

quotation_billing_router = APIRouter()


@quotation_billing_router.get(
    "/{quotation_id}/billing-schedule", response_model=SuccessResponse[list[BillingScheduleEntry]]
)
def get_billing_schedule(quotation_id: int, current_user: CurrentUser):
    not_implemented()


@quotation_billing_router.post(
    "/{quotation_id}/invoices/generate", response_model=SuccessResponse[InvoiceRead]
)
def generate_invoice(quotation_id: int, current_user: CurrentUser, idempotency_key: IdempotencyKey):
    not_implemented()


@router.get("", response_model=SuccessResponse[Page[InvoiceRead]])
def list_invoices(
    current_user: CurrentUser,
    params: Annotated[PageParams, Depends()],
    quotation_id: Annotated[int | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
):
    not_implemented()


@router.get("/{invoice_id}", response_model=SuccessResponse[InvoiceRead])
def get_invoice(invoice_id: int, current_user: CurrentUser):
    not_implemented()


@router.get("/{invoice_id}/lineage", response_model=SuccessResponse[list[InvoiceRead]])
def get_invoice_lineage(invoice_id: int, current_user: CurrentUser):
    """Oldest -> newest, so the UI can show "superseded by INV-…"."""
    not_implemented()


@router.post("/{invoice_id}/payments", response_model=SuccessResponse[InvoiceRead])
def record_payment(
    invoice_id: int, payload: PaymentRequest, current_user: CurrentUser, idempotency_key: IdempotencyKey
):
    not_implemented()


@router.post("/{invoice_id}/supersede", response_model=SuccessResponse[SupersedeResponse])
def supersede_invoice(
    invoice_id: int, payload: SupersedeRequest, current_user: CurrentUser, idempotency_key: IdempotencyKey
):
    not_implemented()
