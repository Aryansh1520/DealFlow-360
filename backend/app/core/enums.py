"""Every enum in the system, as `StrEnum`, sourced from `API_CONTRACT.md` §2.

Nothing outside this module defines a status string literal. Models, schemas, the
(Phase 2) state machine and `app/meta/router.py` all import from here.
"""

from enum import StrEnum


class CustomerTier(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    PENDING_L1 = "pending_l1"
    PENDING_L2 = "pending_l2"
    APPROVED = "approved"
    SENT = "sent"
    UNDER_NEGOTIATION = "under_negotiation"
    CONFIRMED = "confirmed"
    FULFILLING = "fulfilling"
    INVOICED = "invoiced"
    PAID = "paid"
    REJECTED = "rejected"
    RETURNED_FOR_REVISION = "returned_for_revision"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalLevel(StrEnum):
    L1_SALES_MANAGER = "l1_sales_manager"
    L2_FINANCE = "l2_finance"


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RETURN_FOR_REVISION = "return_for_revision"


class ActorType(StrEnum):
    """Not part of `MetaEnums` — used inline on `QuoteEventRead.actor_type`."""

    INTERNAL = "internal"
    CUSTOMER = "customer"
    SYSTEM = "system"


class ApprovalStatus(StrEnum):
    """Not part of `MetaEnums` (the contract only lists `approval_level` /
    `approval_action`), but used inline on `ApprovalRead.status`."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    SKIPPED = "skipped"


class LineType(StrEnum):
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"


class BillingInterval(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RefundPolicy(StrEnum):
    """Not in `MetaEnums` — used inline on `SubscriptionPlanRead.refund_policy`."""

    PRORATED = "prorated"
    NONE = "none"
    CREDIT_NOTE = "credit_note"


class EventType(StrEnum):
    QUOTE_CREATED = "quote.created"
    QUOTE_LINE_ADDED = "quote.line_added"
    QUOTE_LINE_UPDATED = "quote.line_updated"
    QUOTE_LINE_REMOVED = "quote.line_removed"
    QUOTE_DISCOUNT_CHANGED = "quote.discount_changed"
    QUOTE_SUBMITTED = "quote.submitted"
    QUOTE_APPROVED = "quote.approved"
    QUOTE_REJECTED = "quote.rejected"
    QUOTE_RETURNED = "quote.returned"
    QUOTE_SENT = "quote.sent"
    QUOTE_CUSTOMER_VIEWED = "quote.customer_viewed"
    QUOTE_CUSTOMER_COMMENTED = "quote.customer_commented"
    QUOTE_CUSTOMER_COUNTERED = "quote.customer_countered"
    QUOTE_COUNTER_REJECTED = "quote.counter_rejected"
    QUOTE_CUSTOMER_CONFIRMED = "quote.customer_confirmed"
    QUOTE_UPSELL_ADDED = "quote.upsell_added"
    QUOTE_UPSELL_DISMISSED = "quote.upsell_dismissed"
    QUOTE_FULFILLMENT_PLANNED = "quote.fulfillment_planned"
    QUOTE_FULFILLMENT_OVERRIDDEN = "quote.fulfillment_overridden"
    QUOTE_BACKORDER_CONSOLIDATED = "quote.backorder_consolidated"
    QUOTE_INVOICED = "quote.invoiced"
    QUOTE_PAYMENT_RECORDED = "quote.payment_recorded"
    QUOTE_INVOICE_SUPERSEDED = "quote.invoice_superseded"
    QUOTE_CANCELLED = "quote.cancelled"


class RiskRuleCode(StrEnum):
    """Upper-snake by contract — the exception to the "lowercase enum" convention,
    consistent with how `ApiError.code` is also upper-snake."""

    LINE_CEILING_BREACH = "LINE_CEILING_BREACH"
    BLENDED_THRESHOLD = "BLENDED_THRESHOLD"
    TIER_CEILING_BREACH = "TIER_CEILING_BREACH"
    MARGIN_FLOOR_BREACH = "MARGIN_FLOOR_BREACH"
    ORDER_VALUE_FLOOR = "ORDER_VALUE_FLOOR"
    HARD_BREACH_OVERRIDE = "HARD_BREACH_OVERRIDE"


class FulfillmentStatus(StrEnum):
    """Not enumerated explicitly in `API_CONTRACT.md` (Phase 3 owns fulfilment) —
    values inferred from `BACKEND_PHASE_3.md`'s shipment/backorder model so
    `/meta/enums` and `QuotationRead.fulfillment_status` have somewhere to point.
    Phase 3 may extend this; it must not repurpose an existing member."""

    PENDING = "pending"
    PLANNED = "planned"
    PARTIAL = "partial"
    FULFILLED = "fulfilled"
    BACKORDERED = "backordered"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"
    SUPERSEDED = "superseded"


class DocumentType(StrEnum):
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"


class AlertType(StrEnum):
    STALLED_DEAL = "stalled_deal"
    DISCOUNT_ANOMALY = "discount_anomaly"
    DELIVERY_SLIPPAGE = "delivery_slippage"
    MARGIN_EROSION = "margin_erosion"


class AlertSeverity(StrEnum):
    """Not in `MetaEnums` — used inline on `AlertRead.severity`."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReservationStatus(StrEnum):
    """Lifecycle of a `stock_reservations` row — `BACKEND_PHASE_3.md` Task 1."""

    HELD = "held"
    COMMITTED = "committed"
    RELEASED = "released"


class ShipmentStatus(StrEnum):
    """Lifecycle of a `shipments` row."""

    PLANNED = "planned"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class BackorderStatus(StrEnum):
    OPEN = "open"
    CONSOLIDATED = "consolidated"
    CANCELLED = "cancelled"


class BillingScheduleStatus(StrEnum):
    SCHEDULED = "scheduled"
    INVOICED = "invoiced"
    PAID = "paid"
    CANCELLED = "cancelled"


class DashboardType(StrEnum):
    """Which dashboard the frontend renders for a principal — chosen by the
    caller's `role.dashboard_type`, set on the Roles screen of the admin panel.
    A *dashboard layout*, not an RBAC concept: permissions still gate every
    endpoint the dashboard calls. `generic` is the safe default for any role
    an admin hasn't explicitly assigned one to."""

    SUPER_ADMIN = "super_admin"
    SALES_MANAGER = "sales_manager"
    FINANCE_OPS = "finance_ops"
    GENERIC = "generic"


class ErrorCode(StrEnum):
    """`ApiError.code` — see `API_CONTRACT.md` §1 "Error envelope"."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    IDEMPOTENCY_REPLAY = "IDEMPOTENCY_REPLAY"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    FORBIDDEN_PRINCIPAL = "FORBIDDEN_PRINCIPAL"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"


# from_status -> allowed to_status[]. Authoritative — `app/quotations/transitions.py`
# (Phase 2) imports this directly rather than redefining it. One definition, two
# consumers, per `BACKEND_PHASE_1.md` Task 2.
QUOTE_TRANSITIONS: dict[str, list[str]] = {
    QuoteStatus.DRAFT: [
        QuoteStatus.PENDING_L1,
        QuoteStatus.PENDING_L2,
        QuoteStatus.APPROVED,
        QuoteStatus.CANCELLED,
    ],
    QuoteStatus.PENDING_L1: [
        QuoteStatus.PENDING_L2,
        QuoteStatus.APPROVED,
        QuoteStatus.REJECTED,
        QuoteStatus.RETURNED_FOR_REVISION,
        QuoteStatus.CANCELLED,
    ],
    QuoteStatus.PENDING_L2: [
        QuoteStatus.APPROVED,
        QuoteStatus.REJECTED,
        QuoteStatus.RETURNED_FOR_REVISION,
        QuoteStatus.CANCELLED,
    ],
    QuoteStatus.RETURNED_FOR_REVISION: [QuoteStatus.DRAFT, QuoteStatus.CANCELLED],
    # `approved -> confirmed`: a customer who already asked to confirm and then had
    # their terms re-approved shouldn't have to wait for a manual re-send; a rep
    # can also confirm straight from approved on the customer's behalf.
    # `approved -> under_negotiation`: the customer can still open a counter-offer
    # from the portal before confirming — that reopens negotiation and the rep
    # re-submits once the terms are agreed.
    QuoteStatus.APPROVED: [
        QuoteStatus.SENT,
        QuoteStatus.UNDER_NEGOTIATION,
        QuoteStatus.CONFIRMED,
        QuoteStatus.CANCELLED,
    ],
    QuoteStatus.SENT: [
        QuoteStatus.UNDER_NEGOTIATION,
        QuoteStatus.CONFIRMED,
        QuoteStatus.EXPIRED,
        QuoteStatus.CANCELLED,
    ],
    QuoteStatus.UNDER_NEGOTIATION: [
        QuoteStatus.PENDING_L1,
        QuoteStatus.PENDING_L2,
        QuoteStatus.SENT,
        QuoteStatus.CONFIRMED,
        QuoteStatus.CANCELLED,
    ],
    # `confirmed -> invoiced` (Phase 3): a subscription-only order is never shipped,
    # so it goes straight from confirmed to invoiced without passing through fulfilling.
    QuoteStatus.CONFIRMED: [QuoteStatus.FULFILLING, QuoteStatus.INVOICED, QuoteStatus.CANCELLED],
    QuoteStatus.FULFILLING: [QuoteStatus.INVOICED],
    QuoteStatus.INVOICED: [QuoteStatus.PAID],
    QuoteStatus.PAID: [],
    QuoteStatus.REJECTED: [],
    QuoteStatus.CANCELLED: [],
    QuoteStatus.EXPIRED: [],
}


def _humanize(value: str) -> str:
    """Fallback label for any enum member not given an explicit override below:
    `"pending_l1"` -> `"Pending L1"`, `"quote.line_added"` -> `"Quote Line Added"`."""
    words = value.replace(".", " ").replace("_", " ").split()
    return " ".join(word.upper() if len(word) <= 2 else word.capitalize() for word in words)


_APPROVAL_LEVEL_LABELS = {
    ApprovalLevel.L1_SALES_MANAGER: "Sales Manager (L1)",
    ApprovalLevel.L2_FINANCE: "Finance (L2)",
}

_RISK_RULE_CODE_LABELS = {
    RiskRuleCode.LINE_CEILING_BREACH: "Line ceiling breach",
    RiskRuleCode.BLENDED_THRESHOLD: "Blended overage threshold",
    RiskRuleCode.TIER_CEILING_BREACH: "Tier ceiling breach",
    RiskRuleCode.MARGIN_FLOOR_BREACH: "Margin floor breach",
    RiskRuleCode.ORDER_VALUE_FLOOR: "Order value floor",
    RiskRuleCode.HARD_BREACH_OVERRIDE: "Hard breach override",
}

# enum_name -> value -> human label, per `MetaEnums.labels`. Anything not given an
# explicit override above is humanized mechanically.
_ENUM_GROUPS: dict[str, type[StrEnum]] = {
    "customer_tier": CustomerTier,
    "quote_status": QuoteStatus,
    "approval_level": ApprovalLevel,
    "approval_action": ApprovalAction,
    "line_type": LineType,
    "billing_interval": BillingInterval,
    "event_type": EventType,
    "risk_rule_code": RiskRuleCode,
    "fulfillment_status": FulfillmentStatus,
    "invoice_status": InvoiceStatus,
    "document_type": DocumentType,
    "alert_type": AlertType,
    "billing_schedule_status": BillingScheduleStatus,
    "dashboard_type": DashboardType,
}

_OVERRIDES: dict[str, dict[str, str]] = {
    "approval_level": _APPROVAL_LEVEL_LABELS,
    "risk_rule_code": _RISK_RULE_CODE_LABELS,
}


def enum_values(name: str) -> list[str]:
    return [member.value for member in _ENUM_GROUPS[name]]


def enum_labels() -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for name, enum_cls in _ENUM_GROUPS.items():
        overrides = _OVERRIDES.get(name, {})
        labels[name] = {
            member.value: overrides.get(member.value, _humanize(member.value))
            for member in enum_cls
        }
    return labels
