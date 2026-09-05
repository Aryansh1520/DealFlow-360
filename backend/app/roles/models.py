from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, OrgScopedMixin, TimestampMixin


class Role(Base, TimestampMixin, OrgScopedMixin):
    __tablename__ = "roles"
    # Role names are unique per organization — each org has its own "Administrator".
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_roles_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    # Plain permission strings, e.g. ["users:read", "users:write"]. "*" grants everything.
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
