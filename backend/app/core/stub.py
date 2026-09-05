"""The Task 0 stub pass: every Phase 2/3 endpoint exists with the right path and
`response_model` from hour one, so `openapi.json` is complete and final before any of
the logic behind it is written. See `BACKEND_PHASE_1.md` Task 0.
"""

from fastapi import HTTPException


def not_implemented() -> None:
    raise HTTPException(status_code=501, detail="Not implemented", headers=None)
