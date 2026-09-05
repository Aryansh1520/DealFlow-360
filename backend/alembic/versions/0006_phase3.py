"""phase 3: fulfilment, billing, portal magic links, deal metrics + alerts

Revision ID: 0006_phase3
Revises: 0005_multi_tenant
Create Date: 2026-09-05

Adds every Phase 3 table plus two column additions:
- `roles.dashboard_type` — which dashboard layout the frontend renders for the role
- (all new tables carry `org_id` — the tenant scoping from 0005 applies unchanged)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase3"
down_revision: str | None = "0005_multi_tenant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _org_column() -> sa.Column:
    return sa.Column(
        "org_id",
        sa.Integer(),
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )


def _org_index(table: str) -> None:
    op.create_index(f"ix_{table}_org_id", table, ["org_id"])


NEW_TABLES = [
    "stock_reservations",
    "shipments",
    "shipment_lines",
    "backorders",
    "portal_magic_links",
    "invoices",
    "invoice_lines",
    "billing_schedule",
    "payments",
    "deal_metrics",
    "rep_discount_stats",
    "deal_alerts",
]


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column(
            "dashboard_type",
            sa.String(length=30),
            nullable=False,
            server_default="generic",
        ),
    )
    # Backfill the seeded roles by name so an existing DB gets sensible dashboards
    # without a re-seed. New orgs get these from app/db/seed.py.
    op.execute(
        """
        UPDATE roles SET dashboard_type = CASE name
            WHEN 'Administrator'  THEN 'super_admin'
            WHEN 'Sales Manager'  THEN 'sales_manager'
            WHEN 'Finance'        THEN 'finance_ops'
            WHEN 'Operations'     THEN 'finance_ops'
            ELSE 'generic'
        END
        """
    )

    # ---- Fulfilment ---------------------------------------------------------------
    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("line_id", sa.Integer(), sa.ForeignKey("quote_lines.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="held"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stock_reservations_quotation_id", "stock_reservations", ["quotation_id"])
    op.create_index(
        "ix_stock_reservations_product_warehouse", "stock_reservations", ["product_id", "warehouse_id"]
    )

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="planned"),
        sa.Column("estimated_cost_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shipments_quotation_id", "shipments", ["quotation_id"])

    op.create_table(
        "shipment_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("line_id", sa.Integer(), sa.ForeignKey("quote_lines.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )
    op.create_index("ix_shipment_lines_shipment_id", "shipment_lines", ["shipment_id"])

    op.create_table(
        "backorders",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("line_id", sa.Integer(), sa.ForeignKey("quote_lines.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("expected_restock_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_backorders_quotation_status", "backorders", ["quotation_id", "status"])

    # ---- Portal -----------------------------------------------------------------
    op.create_table(
        "portal_magic_links",
        sa.Column("token_hash", sa.String(length=64), primary_key=True),
        _org_column(),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- Billing --------------------------------------------------------------
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("number", sa.String(length=32), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False, server_default="invoice"),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("subtotal_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tax_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("paid_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("supersedes_invoice_id", sa.Integer(), sa.ForeignKey("invoices.id")),
        sa.Column("superseded_by_invoice_id", sa.Integer(), sa.ForeignKey("invoices.id")),
        sa.Column("credit_note_id", sa.Integer(), sa.ForeignKey("invoices.id")),
        sa.Column("pdf_object_key", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "number", name="uq_invoices_org_number"),
    )
    op.create_index("ix_invoices_quotation_id", "invoices", ["quotation_id"])
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("tax_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    op.create_table(
        "billing_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("line_id", sa.Integer(), sa.ForeignKey("quote_lines.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("is_prorated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("proration_days", sa.Integer()),
        sa.Column("proration_basis_days", sa.Integer()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("line_id", "period_start", name="uq_billing_schedule_line_period"),
    )
    op.create_index("ix_billing_schedule_quotation_id", "billing_schedule", ["quotation_id"])
    op.create_index("ix_billing_schedule_status", "billing_schedule", ["status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=255)),
        sa.Column("recorded_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])

    # ---- Dashboard read model + anomaly ----------------------------------------
    op.create_table(
        "deal_metrics",
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), primary_key=True),
        _org_column(),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("owner_rep_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("margin_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("days_inactive", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_metrics_last_activity", "deal_metrics", ["last_activity_at"])
    op.create_index("ix_deal_metrics_owner_stage", "deal_metrics", ["owner_rep_id", "stage"])
    op.create_index(
        "ix_deal_metrics_flags", "deal_metrics", ["flags"], postgresql_using="gin"
    )

    op.create_table(
        "rep_discount_stats",
        sa.Column("rep_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        _org_column(),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mean_bps", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("m2", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "deal_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        _org_column(),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("alert_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.String(length=1000), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dedupe_key", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_alerts_quotation_id", "deal_alerts", ["quotation_id"])
    op.create_index("ix_deal_alerts_type_ack", "deal_alerts", ["alert_type", "acknowledged"])
    op.create_index(
        "uq_deal_alerts_dedupe", "deal_alerts", ["quotation_id", "dedupe_key"], unique=True
    )

    for table in NEW_TABLES:
        _org_index(table)


def downgrade() -> None:
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
    op.drop_column("roles", "dashboard_type")
