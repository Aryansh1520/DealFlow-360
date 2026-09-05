"""multi-tenant: organizations + org_id on every tenant table

Revision ID: 0005_multi_tenant
Revises: adbde9f67905
Create Date: 2026-09-05

Adds the `organizations` tenant root and an `org_id` FK to every tenant-owned
table. Existing rows are backfilled to a single "Demo Org" so the migration is
safe on a populated database; on a fresh database the tables are empty and the
seed script creates the same organization by slug.

Single-column unique constraints that must now be unique *per organization* are
swapped for composite `(org_id, ...)` constraints. `users.email` and
`customers.email` stay globally unique — login has no organization selector.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_multi_tenant"
down_revision: str | None = "adbde9f67905"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Every tenant-owned table gets an `org_id` column, FK and index.
TENANT_TABLES = [
    "users",
    "roles",
    "customers",
    "categories",
    "products",
    "product_variants",
    "price_lists",
    "price_list_entries",
    "warehouses",
    "stock",
    "stock_movements",
    "subscription_plans",
    "discount_policies",
    "policy_tier_ceilings",
    "policy_category_ceilings",
    "quotations",
    "quote_lines",
    "quote_approvals",
    "quote_events",
    "product_affinity",
    "idempotency_keys",
]

# old single-column unique constraint  ->  (table, [composite columns], new name)
UNIQUE_SWAPS = [
    ("roles_name_key", "roles", ["org_id", "name"], "uq_roles_org_name"),
    ("categories_code_key", "categories", ["org_id", "code"], "uq_categories_org_code"),
    ("products_sku_key", "products", ["org_id", "sku"], "uq_products_org_sku"),
    ("warehouses_code_key", "warehouses", ["org_id", "code"], "uq_warehouses_org_code"),
    (
        "discount_policies_version_key",
        "discount_policies",
        ["org_id", "version"],
        "uq_discount_policies_org_version",
    ),
    ("quotations_reference_key", "quotations", ["org_id", "reference"], "uq_quotations_org_reference"),
]

_DEMO_ORG = "(SELECT id FROM organizations WHERE slug = 'demo')"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.execute(
        "INSERT INTO organizations (name, slug, is_active, created_at, updated_at) "
        "VALUES ('Demo Org', 'demo', true, now(), now())"
    )

    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("org_id", sa.Integer(), nullable=True))
        op.execute(f"UPDATE {table} SET org_id = {_DEMO_ORG}")
        op.alter_column(table, "org_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_org_id", table, "organizations", ["org_id"], ["id"], ondelete="CASCADE"
        )
        op.create_index(f"ix_{table}_org_id", table, ["org_id"])

    for old_name, table, columns, new_name in UNIQUE_SWAPS:
        op.drop_constraint(old_name, table, type_="unique")
        op.create_unique_constraint(new_name, table, columns)

    # "one active discount policy" — now per organization.
    op.drop_index(
        "ix_discount_policies_is_active",
        table_name="discount_policies",
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_discount_policies_is_active",
        "discount_policies",
        ["org_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.add_column(
        "users",
        sa.Column("is_org_owner", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE users SET is_org_owner = true "
        "WHERE id IN (SELECT min(id) FROM users GROUP BY org_id)"
    )


def downgrade() -> None:
    op.drop_column("users", "is_org_owner")

    op.drop_index(
        "ix_discount_policies_is_active",
        table_name="discount_policies",
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_discount_policies_is_active",
        "discount_policies",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    for old_name, table, _columns, new_name in UNIQUE_SWAPS:
        op.drop_constraint(new_name, table, type_="unique")
        op.create_unique_constraint(old_name, table, [_columns[-1]])

    for table in TENANT_TABLES:
        op.drop_index(f"ix_{table}_org_id", table_name=table)
        op.drop_constraint(f"fk_{table}_org_id", table, type_="foreignkey")
        op.drop_column(table, "org_id")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")
