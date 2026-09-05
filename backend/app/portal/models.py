from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, OrgScopedMixin


class PortalMagicLink(Base, OrgScopedMixin):
    """A single-use, 24h portal entry token. Only the SHA-256 hash of the token is
    stored — the raw token exists solely in the email/link handed to the customer.
    Generated as a side effect of transitioning a quotation to `sent`; redeemed at
    `POST /portal/magic-link/redeem`, which marks it used and issues normal
    customer tokens."""

    __tablename__ = "portal_magic_links"

    token_hash: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
