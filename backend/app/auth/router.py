from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import (
    LoginRequest,
    MeUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.core.deps import CurrentUser
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.responses import SuccessResponse, ok
from app.core.security import (
    REFRESH_TOKEN,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.seed import DEFAULT_USER_ROLE
from app.db.session import get_db
from app.roles.models import Role
from app.users.models import User
from app.users.schemas import UserRead

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


def _token_pair(user_id: int) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post(
    "/register",
    response_model=SuccessResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: DbSession):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise ConflictException("A user with this email already exists")

    default_role = db.scalar(select(Role).where(Role.name == DEFAULT_USER_ROLE))
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=default_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok(user, "Account created successfully.")


@router.post("/login", response_model=SuccessResponse[TokenResponse])
def login(payload: LoginRequest, db: DbSession):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedException("Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedException("This account is inactive")
    return ok(_token_pair(user.id), "Logged in successfully.")


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
def refresh(payload: RefreshRequest, db: DbSession):
    token_payload = decode_token(payload.refresh_token, expected_type=REFRESH_TOKEN)
    user = db.get(User, int(token_payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    return ok(_token_pair(user.id), "Token refreshed successfully.")


@router.get("/me", response_model=SuccessResponse[UserRead])
def read_me(current_user: CurrentUser):
    return ok(current_user, "Current user retrieved successfully.")


@router.patch("/me", response_model=SuccessResponse[UserRead])
def update_me(payload: MeUpdate, current_user: CurrentUser, db: DbSession):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return ok(current_user, "Profile updated successfully.")
