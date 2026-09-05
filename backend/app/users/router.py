from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crud import CRUDBase
from app.core.deps import CurrentUser, require_permissions
from app.core.exceptions import BadRequestException, ConflictException
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.core.security import hash_password
from app.db.session import get_db
from app.users.models import User
from app.users.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

user_crud = CRUDBase(User, search_fields=["email", "full_name"])


def _prepare_user_data(data: dict) -> dict:
    """Convert the plain `password` field into `hashed_password`."""
    password = data.pop("password", None)
    if password is not None:
        data["hashed_password"] = hash_password(password)
    return data


@router.get(
    "",
    response_model=SuccessResponse[Page[UserRead]],
    dependencies=[Depends(require_permissions("users:read"))],
)
def list_users(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    role_id: Annotated[int | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
):
    items, total = user_crud.list(
        db, params=params, filters={"role_id": role_id, "is_active": is_active}
    )
    return ok(Page[UserRead].create(items, total, params), "Users retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("users:write"))],
)
def create_user(payload: UserCreate, db: DbSession):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise ConflictException("A user with this email already exists")
    user = user_crud.create(db, _prepare_user_data(payload.model_dump()))
    return ok(user, "User created successfully.")


@router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserRead],
    dependencies=[Depends(require_permissions("users:read"))],
)
def get_user(user_id: int, db: DbSession):
    return ok(user_crud.get_or_404(db, user_id), "User retrieved successfully.")


@router.patch(
    "/{user_id}",
    response_model=SuccessResponse[UserRead],
    dependencies=[Depends(require_permissions("users:write"))],
)
def update_user(user_id: int, payload: UserUpdate, db: DbSession):
    user = user_crud.get_or_404(db, user_id)
    updated = user_crud.update(db, user, _prepare_user_data(payload.model_dump(exclude_unset=True)))
    return ok(updated, "User updated successfully.")


@router.delete(
    "/{user_id}",
    response_model=SuccessResponse[None],
    dependencies=[Depends(require_permissions("users:write"))],
)
def delete_user(user_id: int, db: DbSession, current_user: CurrentUser):
    if user_id == current_user.id:
        raise BadRequestException("You cannot delete your own account")
    user = user_crud.get_or_404(db, user_id)
    user_crud.delete(db, user)
    return ok(None, "User deleted successfully.")
