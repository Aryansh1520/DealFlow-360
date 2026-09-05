from pydantic import BaseModel, EmailStr, Field

from app.core.security import UserType
from app.customers.schemas import CustomerRead
from app.users.schemas import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_type: UserType


class MeResponse(BaseModel):
    """Discriminated on `user_type`: exactly one of `internal` / `customer` is set."""

    user_type: UserType
    internal: UserRead | None = None
    customer: CustomerRead | None = None


class MeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=72)
