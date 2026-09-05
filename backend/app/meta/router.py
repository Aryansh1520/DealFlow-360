from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.deps import CurrentPrincipal
from app.core.enums import QUOTE_TRANSITIONS, enum_labels, enum_values
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db
from app.meta.schemas import HealthStatus, MetaEnums

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/enums", response_model=SuccessResponse[MetaEnums])
def get_enums(principal: CurrentPrincipal):
    """Public to any authenticated principal — internal or customer."""
    payload = MetaEnums(
        contract_version=settings.contract_version,
        customer_tier=enum_values("customer_tier"),
        quote_status=enum_values("quote_status"),
        approval_level=enum_values("approval_level"),
        approval_action=enum_values("approval_action"),
        line_type=enum_values("line_type"),
        billing_interval=enum_values("billing_interval"),
        event_type=enum_values("event_type"),
        risk_rule_code=enum_values("risk_rule_code"),
        fulfillment_status=enum_values("fulfillment_status"),
        invoice_status=enum_values("invoice_status"),
        document_type=enum_values("document_type"),
        alert_type=enum_values("alert_type"),
        transitions=QUOTE_TRANSITIONS,
        labels=enum_labels(),
    )
    return ok(payload, "Enums retrieved successfully.")


health_router = APIRouter()


@health_router.get("/health", response_model=SuccessResponse[HealthStatus])
def health():
    return ok(HealthStatus(status="ok"), "Healthy.")


@health_router.get("/health/ready", response_model=SuccessResponse[HealthStatus])
def health_ready(db: DbSession):
    db.execute(text("SELECT 1"))
    return ok(HealthStatus(status="ok"), "Ready.")
