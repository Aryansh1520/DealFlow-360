from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentPrincipal
from app.core.stub import not_implemented

router = APIRouter()


@router.get("/stream")
def stream(scope: Annotated[str, Query()], principal: CurrentPrincipal):
    """`text/event-stream` (Phase 3). Scope authorisation — a customer may only
    subscribe to `quote:{id}` for a quote they own; internal reps need
    `quotations:read` — is enforced once the real handler lands in `app/events/stream.py`."""
    not_implemented()
