"""Shared FastAPI dependencies: current principal, current user/customer, permission checks."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import ErrorCode
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import ACCESS_TOKEN, CUSTOMER, INTERNAL, decode_token
from app.core.tenant_context import set_current_org
from app.customers.models import Customer
from app.db.session import get_db
from app.organizations.models import Organization
from app.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    """The authenticated caller, tagged by which side of the system they belong to.

    Exactly one of `user` / `customer` is set, matching `user_type`.
    """

    user_type: str
    user: User | None = None
    customer: Customer | None = None


def get_current_principal(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None:
        raise UnauthorizedException("Not authenticated")

    payload = decode_token(credentials.credentials, expected_type=ACCESS_TOKEN)
    user_type = payload.get("user_type")
    subject_id = int(payload["sub"])

    # These lookups run before any tenant context is set, so they hit the global
    # `users` / `customers` tables by primary key. Once the principal is known we
    # pin the request to its organization for every downstream query.
    if user_type == INTERNAL:
        user = db.get(User, subject_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("User not found or inactive")
        _activate_org(db, user.org_id)
        return Principal(user_type=INTERNAL, user=user)

    if user_type == CUSTOMER:
        customer = db.get(Customer, subject_id)
        if customer is None or not customer.portal_enabled:
            raise UnauthorizedException("Customer not found or portal access disabled")
        _activate_org(db, customer.org_id)
        return Principal(user_type=CUSTOMER, customer=customer)

    raise UnauthorizedException("Invalid token")


def _activate_org(db: Session, org_id: int) -> None:
    organization = db.get(Organization, org_id)
    if organization is None or not organization.is_active:
        raise UnauthorizedException("Organization not found or inactive")
    set_current_org(db, org_id)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def get_current_user(principal: CurrentPrincipal) -> User:
    """Requires the caller to be internal staff. Authenticated customers get a 403,
    not a 401 — they're logged in, just not for this side of the system."""
    if principal.user_type != INTERNAL or principal.user is None:
        raise ForbiddenException(
            "This action requires an internal account", code=ErrorCode.FORBIDDEN_PRINCIPAL
        )
    return principal.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_customer(principal: CurrentPrincipal) -> Customer:
    """Requires the caller to be a portal customer. Mirrors `get_current_user`."""
    if principal.user_type != CUSTOMER or principal.customer is None:
        raise ForbiddenException(
            "This action requires a customer account", code=ErrorCode.FORBIDDEN_PRINCIPAL
        )
    return principal.customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]


def require_permissions(*required: str):
    """Dependency factory enforcing RBAC permissions.

    Permissions are plain strings on the user's role (e.g. "users:read").
    A role holding "*" is granted everything. Customers never reach here — they hold
    no role, so this only ever gates internal-user endpoints.

        @router.get("", dependencies=[Depends(require_permissions("users:read"))])
    """

    def checker(user: CurrentUser) -> User:
        granted = set(user.role.permissions) if user.role else set()
        if "*" in granted:
            return user
        missing = [permission for permission in required if permission not in granted]
        if missing:
            raise ForbiddenException(f"Missing permissions: {', '.join(missing)}")
        return user

    return checker
