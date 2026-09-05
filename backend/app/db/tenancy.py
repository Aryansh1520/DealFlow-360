"""Automatic tenant isolation, wired once onto the session factory.

Two SQLAlchemy session events do all the work so feature code never has to think
about ``org_id``:

* ``do_orm_execute`` — every ORM ``SELECT`` (``Session.get`` included) gets an
  implicit ``WHERE org_id = :current_org`` for any entity mixing in
  ``OrgScopedMixin``, whenever the session has a tenant pinned.
* ``before_flush`` — every new ``OrgScopedMixin`` row is stamped with the current
  org; a row that would be written with no tenant pinned (and no explicit org) is
  a bug and raises rather than leaking across tenants.

Unauthenticated paths (login, register, health, portal magic-link) and the seed
script run with no tenant pinned — reads are unscoped and writes must pin one
first via ``app/core/tenant_context.set_current_org``.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.core.tenant_context import get_current_org
from app.db.base import OrgScopedMixin


def _scope_reads(orm_execute_state) -> None:
    if not orm_execute_state.is_select:
        return
    # Secondary lazy-loads already target rows reachable from an in-org parent;
    # re-applying criteria there fights eager loaders. Only scope top-level SELECTs.
    if orm_execute_state.is_relationship_load or orm_execute_state.is_column_load:
        return

    org_id = get_current_org(orm_execute_state.session)
    if org_id is None:
        return

    orm_execute_state.statement = orm_execute_state.statement.options(
        with_loader_criteria(
            OrgScopedMixin,
            lambda cls: cls.org_id == org_id,
            include_aliases=True,
        )
    )


def _stamp_writes(session: Session, flush_context, instances) -> None:
    org_id = get_current_org(session)

    for obj in session.new:
        if not isinstance(obj, OrgScopedMixin):
            continue
        if getattr(obj, "org_id", None) is None:
            if org_id is None:
                raise RuntimeError(
                    f"Refusing to persist {type(obj).__name__} with no organization "
                    "pinned — set_current_org() must run first."
                )
            obj.org_id = org_id
        elif org_id is not None and obj.org_id != org_id:
            raise RuntimeError(
                f"{type(obj).__name__}.org_id={obj.org_id} does not match the pinned "
                f"organization ({org_id})."
            )

    if org_id is not None:
        for obj in session.dirty:
            if isinstance(obj, OrgScopedMixin) and obj.org_id not in (None, org_id):
                raise RuntimeError(
                    f"{type(obj).__name__}.org_id={obj.org_id} does not match the pinned "
                    f"organization ({org_id})."
                )


def register_tenancy(session_factory) -> None:
    event.listen(session_factory, "do_orm_execute", _scope_reads)
    event.listen(session_factory, "before_flush", _stamp_writes)
