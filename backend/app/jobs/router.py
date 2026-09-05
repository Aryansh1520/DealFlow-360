from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.responses import SuccessResponse, ok
from app.jobs.scheduler import JOBS, run_job

router = APIRouter()


def require_org_admin(current_user: CurrentUser) -> None:
    granted = set(current_user.role.permissions) if current_user.role else set()
    if "*" not in granted:
        raise ForbiddenException("This action requires a full-access role.")


@router.get(
    "/jobs", response_model=SuccessResponse[list[str]], dependencies=[Depends(require_org_admin)]
)
def list_jobs():
    return ok(sorted(JOBS), "Available jobs.")


@router.post(
    "/jobs/{name}/run",
    response_model=SuccessResponse[dict],
    dependencies=[Depends(require_org_admin)],
)
def trigger_job(name: str):
    """Run a scheduled job right now instead of waiting for its interval tick."""
    if name not in JOBS:
        raise NotFoundException(f"Unknown job: {name}")
    return ok(run_job(name), f"Job '{name}' executed.")
