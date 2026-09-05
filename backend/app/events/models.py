from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, OrgScopedMixin


class QuoteEvent(Base, OrgScopedMixin):
    """Append-only ledger. No `updated_at` — no UPDATE or DELETE, ever."""

    __tablename__ = "quote_events"
    __table_args__ = (
        Index("ix_quote_events_quotation_created", "quotation_id", "created_at"),
        Index("ix_quote_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # "internal" | "customer" | "system" — see app/core/enums.py::ActorType.
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(Integer)
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
