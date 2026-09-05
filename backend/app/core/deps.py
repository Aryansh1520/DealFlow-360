"""Shared FastAPI dependencies: current user and permission checks."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import ACCESS_TOKEN, decode_token
from app.db.session import get_db
from app.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedException("Not authenticated")

    payload = decode_token(credentials.credentials, expected_type=ACCESS_TOKEN)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permissions(*required: str):
    """Dependency factory enforcing RBAC permissions.

    Permissions are plain strings on the user's role (e.g. "users:read").
    A role holding "*" is granted everything.

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
