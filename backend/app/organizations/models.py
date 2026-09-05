from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    """A tenant. Every other tenant-owned row carries an `org_id` FK to this table
    (see `app/db/base.py::OrgScopedMixin`). Created only by `POST /auth/register`,
    which also makes the registrant the organization's super admin."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
