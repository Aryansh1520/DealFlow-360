from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import (
    LoginRequest,
    MeResponse,
    MeUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.core.deps import CurrentPrincipal, CurrentUser
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.responses import SuccessResponse, ok
from app.core.security import (
    CUSTOMER,
    INTERNAL,
    REFRESH_TOKEN,
    UserType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.tenant_context import set_current_org
from app.customers.models import Customer
from app.db.seed import ADMIN_ROLE, seed_organization, unique_slug
from app.db.session import get_db
from app.organizations.models import Organization
from app.roles.models import Role
from app.users.models import User
from app.users.schemas import UserRead

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


def _token_pair(subject_id: int, user_type: UserType) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject_id, user_type),
        refresh_token=create_refresh_token(subject_id, user_type),
        user_type=user_type,
    )


@router.post(
    "/register",
    response_model=SuccessResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: DbSession):
    """Creates a brand-new organization and its first user, who becomes the org's
    super admin (the org's Administrator role, permissions ["*"], `is_org_owner`).

    This is the *only* way an organization is created. Additional staff members
    are added via `POST /users` and customers via `POST /customers`, both scoped
    to the caller's organization — never here."""
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise ConflictException("A user with this email already exists")

    organization = Organization(
        name=payload.organization_name,
        slug=unique_slug(db, payload.organization_name),
    )
    db.add(organization)
    db.flush()  # assign organization.id

    # Pin every subsequent write in this request to the new tenant.
    set_current_org(db, organization.id)
    seed_organization(db, organization)

    admin_role = db.scalar(select(Role).where(Role.name == ADMIN_ROLE))
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=admin_role,
        is_org_owner=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok(user, "Organization created successfully.")


@router.post("/login", response_model=SuccessResponse[TokenResponse])
def login(payload: LoginRequest, db: DbSession):
    """Single login for both sides of the system. An email is looked up as an
    internal user first, then as a customer — whichever table it belongs to is the
    only one checked against the password, so the two identities can never be
    cross-authenticated against each other's hash."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None:
        if not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedException("This account is inactive")
        return ok(_token_pair(user.id, INTERNAL), "Logged in successfully.")

    customer = db.scalar(select(Customer).where(Customer.email == payload.email))
    if customer is not None and customer.portal_enabled:
        if not verify_password(payload.password, customer.hashed_password):
            raise UnauthorizedException("Incorrect email or password")
        return ok(_token_pair(customer.id, CUSTOMER), "Logged in successfully.")

    raise UnauthorizedException("Incorrect email or password")


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
def refresh(payload: RefreshRequest, db: DbSession):
    token_payload = decode_token(payload.refresh_token, expected_type=REFRESH_TOKEN)
    user_type = token_payload.get("user_type")
    subject_id = int(token_payload["sub"])

    if user_type == INTERNAL:
        user = db.get(User, subject_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("User not found or inactive")
        return ok(_token_pair(user.id, INTERNAL), "Token refreshed successfully.")

    if user_type == CUSTOMER:
        customer = db.get(Customer, subject_id)
        if customer is None or not customer.portal_enabled:
            raise UnauthorizedException("Customer not found or portal access disabled")
        return ok(_token_pair(customer.id, CUSTOMER), "Token refreshed successfully.")

    raise UnauthorizedException("Invalid token")


@router.get("/me", response_model=SuccessResponse[MeResponse])
def read_me(principal: CurrentPrincipal, db: DbSession):
    profile = principal.user if principal.user_type == INTERNAL else principal.customer
    organization = db.get(Organization, profile.org_id)
    if principal.user_type == INTERNAL:
        me = MeResponse(user_type=INTERNAL, internal=principal.user, organization=organization)
    else:
        me = MeResponse(user_type=CUSTOMER, customer=principal.customer, organization=organization)
    return ok(me, "Current user retrieved successfully.")


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
