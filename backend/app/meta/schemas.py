from pydantic import BaseModel


class MetaEnums(BaseModel):
    """`GET /meta/enums` — see `API_CONTRACT.md` §2. The frontend fetches this once on
    boot and renders every badge, filter and action button from it; it never hardcodes
    an enum value or the transition table."""

    contract_version: str
    customer_tier: list[str]
    quote_status: list[str]
    approval_level: list[str]
    approval_action: list[str]
    line_type: list[str]
    billing_interval: list[str]
    event_type: list[str]
    risk_rule_code: list[str]
    fulfillment_status: list[str]
    invoice_status: list[str]
    document_type: list[str]
    alert_type: list[str]
    transitions: dict[str, list[str]]
    labels: dict[str, dict[str, str]]


class HealthStatus(BaseModel):
    status: str
