from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_permissions
from app.core.exceptions import NotFoundException
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.policies.models import DiscountPolicy
from app.policies.schemas import PolicyCreate, PolicyRead
from app.policies.service import activate_policy, create_policy

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

PoliciesRead = Depends(require_permissions("policies:read"))
PoliciesWrite = Depends(require_permissions("policies:write"))


def _get_or_404(db: Session, policy_id: int) -> DiscountPolicy:
    policy = db.get(DiscountPolicy, policy_id)
    if policy is None:
        raise NotFoundException("Policy not found")
    return policy


@router.get("", response_model=SuccessResponse[Page[PolicyRead]], dependencies=[PoliciesRead])
def list_policies(db: DbSession, params: Annotated[PageParams, Depends()]):
    stmt = select(DiscountPolicy).order_by(DiscountPolicy.version.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
    ).all()
    page = Page[PolicyRead].create([PolicyRead.from_model(p) for p in rows], total, params)
    return ok(page, "Policies retrieved successfully.")


@router.get("/active", response_model=SuccessResponse[PolicyRead], dependencies=[PoliciesRead])
def get_active(db: DbSession):
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)))
    if policy is None:
        raise NotFoundException("No active discount policy")
    return ok(PolicyRead.from_model(policy), "Active policy retrieved successfully.")


@router.post(
    "",
    response_model=SuccessResponse[PolicyRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[PoliciesWrite],
)
def create_policy_version(payload: PolicyCreate, db: DbSession):
    policy = create_policy(
        db,
        tier_ceilings=[tc.model_dump() for tc in payload.tier_ceilings],
        category_ceilings=[cc.model_dump() for cc in payload.category_ceilings],
        weights=payload.weights.model_dump(),
        thresholds=payload.thresholds.model_dump(),
        upsell=payload.upsell.model_dump(),
        anomaly=payload.anomaly.model_dump(),
        stalled_after_days=payload.stalled_after_days,
    )
    return ok(PolicyRead.from_model(policy), "Policy version created successfully.")


@router.get("/{policy_id}", response_model=SuccessResponse[PolicyRead], dependencies=[PoliciesRead])
def get_policy(policy_id: int, db: DbSession):
    return ok(PolicyRead.from_model(_get_or_404(db, policy_id)), "Policy retrieved successfully.")


@router.post("/{policy_id}/activate", response_model=SuccessResponse[PolicyRead], dependencies=[PoliciesWrite])
def activate(policy_id: int, db: DbSession):
    policy = _get_or_404(db, policy_id)
    activated = activate_policy(db, policy)
    return ok(PolicyRead.from_model(activated), "Policy activated successfully.")
