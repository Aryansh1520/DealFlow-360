from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.core.types import MoneyMinor

BillingScheduleStatus = Literal["scheduled", "invoiced", "paid", "cancelled"]
DocumentType = Literal["invoice", "credit_note"]
InvoiceStatus = Literal["draft", "issued", "paid", "void", "superseded"]


class BillingScheduleEntry(BaseModel):
    id: int
    quotation_id: int
    line_id: int
    product_name: str
    period_start: date
    period_end: date
    amount_minor: MoneyMinor
    is_prorated: bool
    proration_days: int | None
    proration_basis_days: int | None
    status: BillingScheduleStatus
    invoice_id: int | None
    currency: str


class InvoiceLineRead(BaseModel):
    description: str
    quantity: int
    unit_price_minor: MoneyMinor
    tax_minor: MoneyMinor
    amount_minor: MoneyMinor


class InvoiceRead(BaseModel):
    id: int
    number: str
    document_type: DocumentType
    quotation_id: int
    customer_id: int
    status: InvoiceStatus
    issued_at: datetime | None
    subtotal_minor: MoneyMinor
    tax_minor: MoneyMinor
    total_minor: MoneyMinor
    paid_minor: MoneyMinor
    balance_minor: int
    currency: str
    supersedes_invoice_id: int | None
    superseded_by_invoice_id: int | None
    credit_note_id: int | None
    lines: list[InvoiceLineRead]
    is_immutable: bool


class GenerateInvoiceRequest(BaseModel):
    pass


class PaymentRequest(BaseModel):
    amount_minor: MoneyMinor
    method: str
    reference: str | None = None


class SupersedeLine(BaseModel):
    description: str
    quantity: int
    unit_price_minor: MoneyMinor
    tax_minor: MoneyMinor
    amount_minor: MoneyMinor


class SupersedeRequest(BaseModel):
    reason: str
    lines: list[SupersedeLine]


class SupersedeResponse(BaseModel):
    credit_note: InvoiceRead
    new_invoice: InvoiceRead
