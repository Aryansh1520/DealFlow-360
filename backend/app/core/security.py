"""Password hashing and JWT token creation/validation."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import jwt

from app.config.settings import settings
from app.core.exceptions import UnauthorizedException

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"
PASSWORD_RESET = "password_reset"

# The two top-level identities in the system. Internal staff (sales rep, manager,
# finance, admin, ...) are all `User` rows distinguished only by their `Role`'s
# permissions; `Customer` rows carry no permissions at all. Embedded as a JWT claim
# because `users.id` and `customers.id` can collide, so `sub` alone is ambiguous.
INTERNAL = "internal"
CUSTOMER = "customer"
UserType = Literal["internal", "customer"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _create_token(
    subject: str,
    token_type: str,
    user_type: UserType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "user_type": user_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject_id: int, user_type: UserType) -> str:
    return _create_token(
        str(subject_id),
        ACCESS_TOKEN,
        user_type,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(subject_id: int, user_type: UserType) -> str:
    return _create_token(
        str(subject_id),
        REFRESH_TOKEN,
        user_type,
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def password_fingerprint(hashed_password: str) -> str:
    """Short digest of the current password hash. Embedded in a reset token as its
    `fp` claim so the token stops validating the moment the password changes —
    single-use semantics without a DB table to track spent tokens."""
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(
    subject_id: int, user_type: UserType, hashed_password: str
) -> str:
    return _create_token(
        str(subject_id),
        PASSWORD_RESET,
        user_type,
        timedelta(minutes=settings.jwt_password_reset_token_expire_minutes),
        extra_claims={"fp": password_fingerprint(hashed_password)},
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising UnauthorizedException on any failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid token")

    if payload.get("type") != expected_type:
        raise UnauthorizedException("Invalid token type")
    return payload
