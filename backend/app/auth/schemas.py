from pydantic import BaseModel, EmailStr, Field

from app.core.security import UserType
from app.customers.schemas import CustomerRead
from app.organizations.schemas import OrganizationRead
from app.users.schemas import UserRead


class RegisterRequest(BaseModel):
    """Self-service signup: creates a brand-new organization and its first user,
    who becomes the organization's super admin. Not a path for adding members or
    customers to an existing organization."""

    organization_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """This project has no mail transport, so the reset token is handed straight
    back for the reset screen to use (and is also logged server-side)."""

    reset_token: str
    expires_in_minutes: int


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_type: UserType


class MeResponse(BaseModel):
    """Discriminated on `user_type`: exactly one of `internal` / `customer` is set.
    `organization` is the tenant both principal kinds belong to."""

    user_type: UserType
    internal: UserRead | None = None
    customer: CustomerRead | None = None
    organization: OrganizationRead | None = None


class MeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=72)
