"""SSE live channel — `BACKEND_PHASE_3.md` Task 2 / `API_CONTRACT.md` §4.11.

`GET /events/stream?scope=...` returns `text/event-stream`. Auth is the normal
`Authorization` header (the frontend uses fetch-based SSE, not `EventSource`).
Scope authorisation is enforced here: a customer principal may only watch a
`quote:{id}` they own; internal reps need `quotations:read` for `approvals` and
`dashboard:read` for `dashboard`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import CurrentPrincipal
from app.core.enums import ErrorCode
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.security import CUSTOMER, INTERNAL
from app.core.tenant_context import require_current_org
from app.db.session import get_db
from app.events.stream import subscribe
from app.quotations.models import Quotation

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _resolve_scope(scope: str, principal: CurrentPrincipal, db: Session) -> str:
    """Map the public scope name to the internal bus key, enforcing authorisation."""
    org_id = require_current_org(db)

    if scope in ("approvals", "dashboard"):
        if principal.user_type != INTERNAL or principal.user is None:
            raise ForbiddenException("This scope is internal-only", code=ErrorCode.FORBIDDEN_PRINCIPAL)
        granted = set(principal.user.role.permissions) if principal.user.role else set()
        needed = "quotations:read" if scope == "approvals" else "dashboard:read"
        if "*" not in granted and needed not in granted:
            raise ForbiddenException(f"Missing permission: {needed}")
        return f"org:{org_id}:{scope}"

    if scope.startswith("quote:"):
        try:
            quotation_id = int(scope.split(":", 1)[1])
        except ValueError:
            raise ValidationException("Malformed scope")
        quotation = db.get(Quotation, quotation_id)
        if quotation is None:
            raise NotFoundException("Quotation not found")
        if principal.user_type == CUSTOMER:
            if principal.customer is None or quotation.customer_id != principal.customer.id:
                raise NotFoundException("Quotation not found")
        elif principal.user_type == INTERNAL:
            granted = set(principal.user.role.permissions) if principal.user and principal.user.role else set()
            if "*" not in granted and "quotations:read" not in granted:
                raise ForbiddenException("Missing permission: quotations:read")
        return f"quote:{quotation_id}"

    raise ValidationException(f"Unknown scope: {scope}")


@router.get("/stream")
def stream(scope: Annotated[str, Query()], principal: CurrentPrincipal, db: DbSession):
    internal_scope = _resolve_scope(scope, principal, db)
    return StreamingResponse(
        subscribe(internal_scope),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
