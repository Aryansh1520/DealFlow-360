from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.billing import service
from app.billing.schemas import (
    BillingScheduleEntry,
    InvoiceRead,
    PaymentRequest,
    SupersedeRequest,
    SupersedeResponse,
)
from app.core.deps import CurrentUser, require_permissions
from app.core.idempotency import begin_idempotent, finish_idempotent
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.core.storage import get_object_bytes
from app.db.session import get_db

router = APIRouter()
quotation_billing_router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]
BillingRead = Depends(require_permissions("billing:read"))
BillingWrite = Depends(require_permissions("billing:write"))


@quotation_billing_router.get(
    "/{quotation_id}/billing-schedule",
    response_model=SuccessResponse[list[BillingScheduleEntry]],
    dependencies=[BillingRead],
)
def get_billing_schedule(quotation_id: int, current_user: CurrentUser, db: DbSession):
    quotation = service.get_quotation_or_404(db, quotation_id)
    return ok(service.list_billing_schedule(db, quotation), "Billing schedule retrieved.")


@quotation_billing_router.post(
    "/{quotation_id}/invoices/generate",
    response_model=SuccessResponse[InvoiceRead],
    dependencies=[BillingWrite],
)
async def generate_invoice(
    quotation_id: int,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "billing.generate_invoice"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    quotation = service.get_quotation_or_404(db, quotation_id)
    invoice = service.generate_invoice(db, quotation, current_user)
    response = ok(service._to_invoice_read(invoice), "Invoice generated.")
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


@router.get("", response_model=SuccessResponse[Page[InvoiceRead]], dependencies=[BillingRead])
def list_invoices(
    current_user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    quotation_id: Annotated[int | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
):
    rows, total = service.list_invoices(
        db, page=params.page, page_size=params.page_size, quotation_id=quotation_id, status=status
    )
    page = Page[InvoiceRead].create([service._to_invoice_read(r) for r in rows], total, params)
    return ok(page, "Invoices retrieved.")


@router.get("/{invoice_id}", response_model=SuccessResponse[InvoiceRead], dependencies=[BillingRead])
def get_invoice(invoice_id: int, current_user: CurrentUser, db: DbSession):
    invoice = service.get_invoice_or_404(db, invoice_id)
    return ok(service._to_invoice_read(invoice), "Invoice retrieved.")


@router.get(
    "/{invoice_id}/lineage",
    response_model=SuccessResponse[list[InvoiceRead]],
    dependencies=[BillingRead],
)
def get_invoice_lineage(invoice_id: int, current_user: CurrentUser, db: DbSession):
    invoice = service.get_invoice_or_404(db, invoice_id)
    return ok(service.get_lineage(db, invoice), "Invoice lineage retrieved.")


@router.get("/{invoice_id}/pdf", dependencies=[BillingRead])
def download_invoice_pdf(invoice_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    """Renders the invoice fresh and refreshes the MinIO copy, then streams it —
    never off local disk, and only after this `billing:read` check has passed.
    The PDF is a rendering of immutable data, so re-rendering is safe and keeps the
    template current without a migration."""
    invoice = service.get_invoice_or_404(db, invoice_id)
    service._render_and_store_pdf(db, invoice)
    db.commit()
    data = get_object_bytes(invoice.pdf_object_key) if invoice.pdf_object_key else b""
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice.number}.pdf"'},
    )


@router.post(
    "/{invoice_id}/payments", response_model=SuccessResponse[InvoiceRead], dependencies=[BillingWrite]
)
async def record_payment(
    invoice_id: int,
    payload: PaymentRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "billing.record_payment"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    invoice = service.get_invoice_or_404(db, invoice_id)
    updated = service.record_payment(
        db, invoice, payload.amount_minor, payload.method, payload.reference, current_user
    )
    response = ok(service._to_invoice_read(updated), "Payment recorded.")
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
    "/{invoice_id}/supersede",
    response_model=SuccessResponse[SupersedeResponse],
    dependencies=[BillingWrite],
)
async def supersede_invoice(
    invoice_id: int,
    payload: SupersedeRequest,
    current_user: CurrentUser,
    idempotency_key: IdempotencyKey,
    request: Request,
    db: DbSession,
):
    endpoint = "billing.supersede"
    request_hash = begin_idempotent(db, key=idempotency_key, endpoint=endpoint, body=await request.body())
    original = service.get_invoice_or_404(db, invoice_id)
    credit_note, new_invoice = service.supersede_invoice(
        db, original, payload.reason, payload.lines, current_user
    )
    response = ok(
        SupersedeResponse(
            credit_note=service._to_invoice_read(credit_note),
            new_invoice=service._to_invoice_read(new_invoice),
        ),
        "Invoice superseded.",
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
