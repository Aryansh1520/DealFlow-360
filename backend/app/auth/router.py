import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MeResponse,
    MeUpdate,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.config.settings import settings
from app.core.deps import CurrentPrincipal, CurrentUser
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.responses import SuccessResponse, ok
from app.core.security import (
    CUSTOMER,
    INTERNAL,
    PASSWORD_RESET,
    REFRESH_TOKEN,
    UserType,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_fingerprint,
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

logger = logging.getLogger(__name__)

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


@router.post(
    "/forgot-password", response_model=SuccessResponse[ForgotPasswordResponse]
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession):
    """Issues a short-lived, single-use password-reset token for the account with
    this email. Mirrors `login`: the address is looked up as an internal user
    first, then as a portal-enabled customer.

    There is no mail transport in this project, so the token is returned in the
    response for the reset screen to use directly (and is also logged). The token
    carries an `fp` claim — a digest of the current password hash — so it stops
    working the moment the password is changed."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None and user.is_active:
        subject_id, user_type, hashed = user.id, INTERNAL, user.hashed_password
    else:
        customer = db.scalar(
            select(Customer).where(Customer.email == payload.email)
        )
        if customer is not None and customer.portal_enabled:
            subject_id = customer.id
            user_type = CUSTOMER
            hashed = customer.hashed_password
        else:
            raise NotFoundException("No account was found for that email address")

    token = create_password_reset_token(subject_id, user_type, hashed)
    expires_in = settings.jwt_password_reset_token_expire_minutes
    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    logger.info(
        "Password reset requested for %s (%s) — link valid %d min: %s",
        payload.email,
        user_type,
        expires_in,
        reset_url,
    )
    print(
        f"\n{'=' * 78}\n"
        f"  PASSWORD RESET  ·  {payload.email}\n"
        f"  {reset_url}\n"
        f"  (single-use · expires in {expires_in} min)\n"
        f"{'=' * 78}\n",
        flush=True,
    )
    return ok(
        ForgotPasswordResponse(reset_token=token, expires_in_minutes=expires_in),
        "If the account exists, a password reset token has been generated.",
    )


@router.post("/reset-password", response_model=SuccessResponse[None])
def reset_password(payload: ResetPasswordRequest, db: DbSession):
    """Consumes a token from `/auth/forgot-password` and sets a new password. The
    token's `fp` claim must still match the account's current password hash, so a
    token is good for exactly one reset and any others issued earlier are voided
    by the same change."""
    token_payload = decode_token(payload.token, expected_type=PASSWORD_RESET)
    user_type = token_payload.get("user_type")
    subject_id = int(token_payload["sub"])

    if user_type == INTERNAL:
        principal = db.get(User, subject_id)
        if principal is None or not principal.is_active:
            raise UnauthorizedException("Invalid or expired reset token")
    elif user_type == CUSTOMER:
        principal = db.get(Customer, subject_id)
        if principal is None or not principal.portal_enabled:
            raise UnauthorizedException("Invalid or expired reset token")
    else:
        raise UnauthorizedException("Invalid or expired reset token")

    if token_payload.get("fp") != password_fingerprint(principal.hashed_password):
        raise UnauthorizedException("This reset link has already been used")

    principal.hashed_password = hash_password(payload.new_password)
    db.add(principal)
    db.commit()
    logger.info("Password reset completed for %s %s", user_type, subject_id)
    return ok(None, "Password reset successfully. You can now sign in.")


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
