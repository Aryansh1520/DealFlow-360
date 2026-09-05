from datetime import datetime

from pydantic import BaseModel

from app.core.types import MoneyMinor


class ShipmentLine(BaseModel):
    line_id: int
    product_id: int
    product_name: str
    quantity: int


class ShipmentPlan(BaseModel):
    warehouse_id: int
    warehouse_name: str
    shipping_cost_weight: int
    lines: list[ShipmentLine]


class BackorderLine(BaseModel):
    line_id: int
    product_id: int
    product_name: str
    quantity: int
    expected_restock_at: datetime | None


class FulfillmentPlan(BaseModel):
    quotation_id: int
    plan_hash: str
    shipments: list[ShipmentPlan]
    backorders: list[BackorderLine]
    shipment_count: int
    estimated_shipping_cost_minor: MoneyMinor
    fully_allocatable: bool
    currency: str


class AllocationInput(BaseModel):
    line_id: int
    warehouse_id: int
    quantity: int


class FulfillmentAcceptRequest(BaseModel):
    expected_version: int
    plan_hash: str


class FulfillmentOverrideRequest(BaseModel):
    expected_version: int
    allocations: list[AllocationInput]


class FulfillmentConsolidateRequest(BaseModel):
    expected_version: int
