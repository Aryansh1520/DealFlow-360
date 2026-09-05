"""Submission routing + the approval chain — `BACKEND_PHASE_2.md` Task 6.

`route_quotation` is shared by `submit()` (a rep-initiated submission) and
`revalidate_after_line_change` (the golden-rule re-route after a post-approval edit) —
one function decides "what happens after the engine has run", regardless of who or
what triggered the re-evaluation.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.approvals.models import QuoteApproval
from app.core.enums import ApprovalLevel, ApprovalStatus, ErrorCode, EventType, QuoteStatus
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.customers.models import Customer
from app.quotations.models import Quotation
from app.quotations.serialization import compute_quotation
from app.quotations.service import line_hash
from app.quotations.transitions import transition
from app.users.models import User

_NOT_YET_APPROVED_STATUSES = {QuoteStatus.DRAFT, QuoteStatus.RETURNED_FOR_REVISION}


def route_quotation(
    db: Session,
    quotation: Quotation,
    actor: User | Customer,
    *,
    expected_version: int,
    force: bool = False,
    reason: str | None = None,
) -> Quotation:
    """Re-runs the engine on the quotation's currently-saved lines and applies the
    routing decision: auto-approve, or open an approval chain starting at L1.
    Raises `422 POLICY_VIOLATION` (writing nothing) if any line is below cost."""
    computation = compute_quotation(db, quotation)
    if computation.trace.outcome == "blocked":
        raise ValidationException(
            "This quotation has a line priced below cost — fix it before submitting.",
            code=ErrorCode.POLICY_VIOLATION,
        )

    required = computation.required_approvals
    if not required:
        transition(
            db, quotation, QuoteStatus.APPROVED, actor, expected_version=expected_version, reason=reason, force=force
        )
    else:
        first_level = required[0]
        db.add(
            QuoteApproval(
                quotation_id=quotation.id,
                level=first_level,
                sequence=1,
                status=ApprovalStatus.PENDING.value,
                risk_score=computation.risk_score,
            )
        )
        target_status = QuoteStatus.PENDING_L1 if first_level == ApprovalLevel.L1_SALES_MANAGER else QuoteStatus.PENDING_L2
        transition(db, quotation, target_status, actor, expected_version=expected_version, reason=reason, force=force)

    quotation.approved_line_hash = line_hash(quotation)
    return quotation


def submit(db: Session, quotation: Quotation, actor: User, expected_version: int) -> Quotation:
    route_quotation(db, quotation, actor, expected_version=expected_version)
    db.commit()
    db.refresh(quotation)
    return quotation


def revalidate_after_line_change(db: Session, quotation: Quotation, actor: User | Customer) -> None:
    """The golden rule: once a quote has an `approved_line_hash`, any line change
    that alters it skips every non-terminal approval and re-routes the quote through
    the same submission logic. See `DECISION_ENGINE.md` §8."""
    if quotation.approved_line_hash is None:
        return
    new_hash = line_hash(quotation)
    if new_hash == quotation.approved_line_hash:
        return

    pending = db.scalars(
        select(QuoteApproval).where(
            QuoteApproval.quotation_id == quotation.id, QuoteApproval.status == ApprovalStatus.PENDING.value
        )
    ).all()
    for approval in pending:
        approval.status = ApprovalStatus.SKIPPED.value

    quotation.approved_line_hash = None
    route_quotation(
        db,
        quotation,
        actor,
        expected_version=quotation.version,
        force=True,
        reason="A line changed after approval — re-routed for review.",
    )


def get_approval_or_404(db: Session, approval_id: int) -> QuoteApproval:
    approval = db.get(QuoteApproval, approval_id)
    if approval is None:
        raise NotFoundException("Approval not found")
    return approval


_LEVEL_PERMISSION = {
    ApprovalLevel.L1_SALES_MANAGER.value: "approvals:l1",
    ApprovalLevel.L2_FINANCE.value: "approvals:l2",
}


def require_level_permission(actor: User, level: str) -> None:
    permission = _LEVEL_PERMISSION[level]
    granted = set(actor.role.permissions) if actor.role else set()
    if "*" in granted or permission in granted:
        return
    raise ForbiddenException(f"Missing permission: {permission}")


def act_on_approval(db: Session, approval: QuoteApproval, action: str, reason: str | None, actor: User) -> Quotation:
    if approval.status != ApprovalStatus.PENDING.value:
        raise ConflictException(
            "This approval has already been acted on.", code=ErrorCode.ILLEGAL_TRANSITION
        )

    quotation = approval.quotation
    approval.acted_by_id = actor.id
    approval.acted_at = datetime.now(timezone.utc)
    approval.reason = reason

    if action == "approve":
        approval.status = ApprovalStatus.APPROVED.value
        computation = compute_quotation(db, quotation)
        if approval.level == ApprovalLevel.L1_SALES_MANAGER.value and ApprovalLevel.L2_FINANCE.value in computation.required_approvals:
            db.add(
                QuoteApproval(
                    quotation_id=quotation.id,
                    level=ApprovalLevel.L2_FINANCE.value,
                    sequence=approval.sequence + 1,
                    status=ApprovalStatus.PENDING.value,
                    risk_score=computation.risk_score,
                )
            )
            transition(db, quotation, QuoteStatus.PENDING_L2, actor, expected_version=quotation.version)
        else:
            transition(db, quotation, QuoteStatus.APPROVED, actor, expected_version=quotation.version)
        quotation.approved_line_hash = line_hash(quotation)

    elif action == "reject":
        if not reason:
            raise ValidationException("A reason is required to reject.")
        approval.status = ApprovalStatus.REJECTED.value
        transition(db, quotation, QuoteStatus.REJECTED, actor, expected_version=quotation.version, reason=reason)
        quotation.approved_line_hash = None

    elif action == "return_for_revision":
        if not reason:
            raise ValidationException("A reason is required to return for revision.")
        approval.status = ApprovalStatus.RETURNED.value
        transition(
            db, quotation, QuoteStatus.RETURNED_FOR_REVISION, actor, expected_version=quotation.version, reason=reason
        )
        quotation.approved_line_hash = None

    else:
        raise ValidationException(f"Unknown approval action: {action}")

    db.commit()
    db.refresh(quotation)
    return quotation
