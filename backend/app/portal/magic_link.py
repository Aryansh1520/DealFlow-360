"""Portal magic links — `BACKEND_PHASE_3.md` Task 3.

Single-use, 24h expiry, `secrets.token_urlsafe(32)`, **only the SHA-256 hash is
stored**. Minted as a side effect of a quote transitioning to `sent`; redeemed at
the unauthenticated `POST /portal/magic-link/redeem`, which marks it used and
issues normal customer tokens.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.portal.models import PortalMagicLink

if TYPE_CHECKING:
    from app.customers.models import Customer
    from app.quotations.models import Quotation
    from app.users.models import User

logger = logging.getLogger(__name__)

LINK_TTL = timedelta(hours=24)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_for_quotation(
    db: Session, quotation: "Quotation", actor: "User | Customer | None"
) -> str:
    """Create a fresh link for the quote's customer. Returns the raw token (only
    time it exists un-hashed) so the caller can log / email it. Does not commit."""
    from app.events.service import record_event

    token = secrets.token_urlsafe(32)
    db.add(
        PortalMagicLink(
            token_hash=_hash(token),
            customer_id=quotation.customer_id,
            quotation_id=quotation.id,
            expires_at=datetime.now(timezone.utc) + LINK_TTL,
        )
    )
    portal_url = f"{settings.frontend_url.rstrip('/')}/portal/access/{token}"
    record_event(
        db,
        quotation,
        "portal.magic_link_issued",
        actor,
        summary="A single-use portal link was issued for the customer.",
        payload={"portal_url": portal_url, "expires_in_hours": 24},
    )
    # No email transport in the demo — surface the link on stdout so it's testable.
    logger.info("Portal magic link for quotation %s: %s", quotation.reference, portal_url)
    print(
        f"\n{'=' * 78}\n"
        f"  PORTAL MAGIC LINK  ·  {quotation.reference}  ·  {quotation.customer.name}\n"
        f"  {portal_url}\n"
        f"  (single-use · expires in 24h)\n"
        f"{'=' * 78}\n",
        flush=True,
    )
    return token


def redeem(db: Session, token: str) -> PortalMagicLink:
    """Validate and consume a link. Raises 404 for an unknown token, 422 for an
    expired or already-used one. Marks it used; caller issues the token pair."""
    link = db.get(PortalMagicLink, _hash(token))
    if link is None:
        raise NotFoundException("This link is not valid.")
    now = datetime.now(timezone.utc)
    if link.used_at is not None:
        raise ValidationException("This link has already been used.")
    if link.expires_at < now:
        raise ValidationException("This link has expired.")
    link.used_at = now
    return link
