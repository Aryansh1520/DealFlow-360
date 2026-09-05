"""The canonical permission catalogue — the single source of truth for every
`resource:action` string `require_permissions()` checks anywhere in this app.

Seeded roles (`app/db/seed.py`) build their permission lists from `ALL_PERMISSIONS`
below, and `GET /meta/enums` serves `PERMISSION_RESOURCES` as `permission_resources`
so the frontend's role editor can render a resource × action checkbox grid instead
of asking an admin to type `quotations:write` by hand. One place a new permission
gets invented; everything else reads from here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionResource:
    resource: str
    label: str
    actions: tuple[str, ...]


# Mirrors every `require_permissions("<resource>:<action>")` call in the codebase —
# see API_CONTRACT.md §5, plus the starter's own users/roles/customers permissions,
# which predate (and aren't repeated in) that table.
PERMISSION_RESOURCES: tuple[PermissionResource, ...] = (
    PermissionResource("catalog", "Catalogue", ("read", "write")),
    PermissionResource("pricing", "Pricing", ("read", "write")),
    PermissionResource("policies", "Discount Policy", ("read", "write")),
    PermissionResource("warehouses", "Warehouses", ("read", "write")),
    PermissionResource("subscriptions", "Subscription Plans", ("read", "write")),
    PermissionResource("customers", "Customers", ("read", "write")),
    PermissionResource("quotations", "Quotations", ("read", "write")),
    PermissionResource("approvals", "Approvals", ("l1", "l2")),
    PermissionResource("fulfillment", "Fulfilment", ("read", "write")),
    PermissionResource("billing", "Billing & Invoices", ("read", "write")),
    PermissionResource("dashboard", "Dashboard", ("read",)),
    PermissionResource("reports", "Reports", ("read", "export")),
    PermissionResource("users", "Users", ("read", "write")),
    PermissionResource("roles", "Roles", ("read", "write")),
)

ALL_PERMISSIONS: tuple[str, ...] = tuple(
    f"{resource.resource}:{action}" for resource in PERMISSION_RESOURCES for action in resource.actions
)
