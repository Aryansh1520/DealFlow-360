from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.crud import CRUDBase
from app.core.deps import require_permissions
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.roles.models import Role
from app.roles.schemas import RoleCreate, RoleRead, RoleUpdate

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

role_crud = CRUDBase(Role, search_fields=["name", "description"])


@router.get(
    "",
    response_model=SuccessResponse[Page[RoleRead]],
    dependencies=[Depends(require_permissions("roles:read"))],
)
def list_roles(db: DbSession, params: Annotated[PageParams, Depends()]):
    items, total = role_crud.list(db, params=params)
    return ok(Page[RoleRead].create(items, total, params), "Roles retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[RoleRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("roles:write"))],
)
def create_role(payload: RoleCreate, db: DbSession):
    role = role_crud.create(db, payload.model_dump())
    return ok(role, "Role created successfully.")


@router.get(
    "/{role_id}",
    response_model=SuccessResponse[RoleRead],
    dependencies=[Depends(require_permissions("roles:read"))],
)
def get_role(role_id: int, db: DbSession):
    return ok(role_crud.get_or_404(db, role_id), "Role retrieved successfully.")


@router.patch(
    "/{role_id}",
    response_model=SuccessResponse[RoleRead],
    dependencies=[Depends(require_permissions("roles:write"))],
)
def update_role(role_id: int, payload: RoleUpdate, db: DbSession):
    role = role_crud.get_or_404(db, role_id)
    updated = role_crud.update(db, role, payload.model_dump(exclude_unset=True))
    return ok(updated, "Role updated successfully.")


@router.delete(
    "/{role_id}",
    response_model=SuccessResponse[None],
    dependencies=[Depends(require_permissions("roles:write"))],
)
def delete_role(role_id: int, db: DbSession):
    role = role_crud.get_or_404(db, role_id)
    role_crud.delete(db, role)
    return ok(None, "Role deleted successfully.")
