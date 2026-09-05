from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, OrgScopedMixin, TimestampMixin


class Customer(Base, TimestampMixin, OrgScopedMixin):
    """A portal user (the customer side of DealFlow360). Holds no RBAC role or
    permissions — the portal's capability set is fixed, unlike internal `User`s."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Globally unique, like `users.email` — portal login has no org selector.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    # bronze | silver | gold — drives the discount ceiling, not catalog pricing.
    tier: Mapped[str] = mapped_column(String(20), default="bronze", nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    portal_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
