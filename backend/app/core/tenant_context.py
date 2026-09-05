"""The current request's tenant (organization), carried on the SQLAlchemy
``Session`` itself via ``Session.info``.

Why not a ``ContextVar``: every endpoint here is a sync ``def``, so FastAPI runs
dependencies and the endpoint body in *separate* threadpool tasks, each with its
own copy of the context — a value set from a dependency would not be visible to
the endpoint. The request-scoped ``Session`` (one per request, from
``get_db``) is a shared object that threads through all of them, so it is the
reliable place to pin the tenant.

Set once in ``app/core/deps.py::get_current_principal`` (and in the seed script /
``POST /auth/register`` before they write tenant rows). Read by the session
events in ``app/db/tenancy.py``. Unset (``None``) means "no tenant filter" — the
state before authentication, used by the unauthenticated endpoints.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException

_ORG_KEY = "current_org_id"


def set_current_org(db: Session, org_id: int | None) -> None:
    db.info[_ORG_KEY] = org_id


def get_current_org(db: Session) -> int | None:
    return db.info.get(_ORG_KEY)


def require_current_org(db: Session) -> int:
    org_id = db.info.get(_ORG_KEY)
    if org_id is None:
        raise UnauthorizedException("No organization context")
    return org_id
