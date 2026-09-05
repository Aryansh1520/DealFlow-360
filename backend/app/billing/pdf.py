"""Invoice / credit-note PDF rendering. The bytes are handed straight to MinIO by
`app/billing/service.py` — they are never written to the local filesystem and are
only ever served back through an authenticated endpoint."""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.billing.models import Invoice
from app.core.money import format_minor


def render_invoice_pdf(invoice: Invoice, *, customer_name: str, org_name: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 20 * mm
    y = height - 25 * mm

    heading = "CREDIT NOTE" if invoice.document_type == "credit_note" else "INVOICE"
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(left, y, f"{heading}  {invoice.number}")
    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, org_name)
    y -= 5 * mm
    pdf.drawString(left, y, f"Bill to: {customer_name}")
    y -= 5 * mm
    pdf.drawString(left, y, f"Status: {invoice.status}")
    if invoice.issued_at:
        y -= 5 * mm
        pdf.drawString(left, y, f"Issued: {invoice.issued_at.date().isoformat()}")
    if invoice.supersedes_invoice_id:
        y -= 5 * mm
        pdf.drawString(left, y, f"Supersedes invoice #{invoice.supersedes_invoice_id}")

    y -= 12 * mm
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "Description")
    pdf.drawString(left + 95 * mm, y, "Qty")
    pdf.drawString(left + 110 * mm, y, "Unit")
    pdf.drawString(left + 135 * mm, y, "Tax")
    pdf.drawString(left + 160 * mm, y, "Amount")
    y -= 3 * mm
    pdf.line(left, y, width - left, y)
    y -= 6 * mm

    pdf.setFont("Helvetica", 9)
    for line in invoice.lines:
        if y < 40 * mm:
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            y = height - 25 * mm
        pdf.drawString(left, y, line.description[:55])
        pdf.drawRightString(left + 105 * mm, y, str(line.quantity))
        pdf.drawRightString(left + 130 * mm, y, format_minor(line.unit_price_minor, invoice.currency))
        pdf.drawRightString(left + 155 * mm, y, format_minor(line.tax_minor, invoice.currency))
        pdf.drawRightString(width - left, y, format_minor(line.amount_minor, invoice.currency))
        y -= 6 * mm

    y -= 4 * mm
    pdf.line(left + 120 * mm, y, width - left, y)
    y -= 7 * mm
    pdf.setFont("Helvetica", 10)
    for label, value in (
        ("Subtotal", invoice.subtotal_minor),
        ("Tax", invoice.tax_minor),
        ("Total", invoice.total_minor),
        ("Paid", invoice.paid_minor),
        ("Balance", invoice.balance_minor),
    ):
        pdf.drawString(left + 120 * mm, y, label)
        pdf.drawRightString(width - left, y, format_minor(value, invoice.currency))
        y -= 6 * mm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
