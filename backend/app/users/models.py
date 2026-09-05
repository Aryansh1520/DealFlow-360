from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, OrgScopedMixin, TimestampMixin
from app.roles.models import Role


class User(Base, TimestampMixin, OrgScopedMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Email stays globally unique: `/auth/login` and `/auth/refresh` look a user up
    # by email alone, with no organization selector.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # The user who created the organization via `POST /auth/register`. Cannot be
    # deleted or demoted out of the Administrator role — see `app/users/router.py`.
    is_org_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))

    role: Mapped[Role | None] = relationship(Role, lazy="joined")
