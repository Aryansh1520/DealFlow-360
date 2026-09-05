"""`scoped_query()` — the one place a portal read is constrained to the calling
customer's own rows. `BACKEND_PHASE_3.md` Task 3.

Tenant isolation (org_id) is already handled globally by `app/db/tenancy.py`. This
adds the *customer-within-tenant* filter for portal principals: a `SELECT` that can
only ever return rows belonging to `principal.customer`. Every portal read builds
its statement from here.
"""

from __future__ import annotations

from sqlalchemy import Select, select

from app.core.deps import Principal
from app.core.security import CUSTOMER
from app.quotations.models import Quotation


def scoped_query(model, principal: Principal) -> Select:
    """A `Select` on `model` already filtered to `principal.customer`.

    - `Quotation`         → `WHERE customer_id = <me>`
    - anything with a `quotation_id` column → joined to `Quotation` and filtered there
    """
    if principal.user_type != CUSTOMER or principal.customer is None:
        raise ValueError("scoped_query is only for customer principals")

    customer_id = principal.customer.id
    stmt = select(model)

    if model is Quotation:
        return stmt.where(Quotation.customer_id == customer_id)

    if hasattr(model, "quotation_id"):
        return stmt.join(Quotation, Quotation.id == model.quotation_id).where(
            Quotation.customer_id == customer_id
        )

    if hasattr(model, "customer_id"):
        return stmt.where(model.customer_id == customer_id)

    raise TypeError(f"Don't know how to scope {model.__name__} to a customer")
