from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DashboardType
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
    # Which dashboard layout the frontend renders for users holding this role —
    # see app/core/enums.py::DashboardType. Set on the Roles screen; purely a
    # presentation choice, RBAC still gates every dashboard endpoint.
    dashboard_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=DashboardType.GENERIC.value
    )
