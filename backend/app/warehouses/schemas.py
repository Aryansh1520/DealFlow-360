from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    shipping_cost_weight: int = Field(default=50, ge=1, le=100)
    replenishment_threshold: int = Field(default=0, ge=0)
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    shipping_cost_weight: int | None = Field(default=None, ge=1, le=100)
    replenishment_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    address: str | None
    shipping_cost_weight: int
    replenishment_threshold: int
    is_active: bool


class StockAdjustRequest(BaseModel):
    product_id: int
    warehouse_id: int
    delta: int
    reason: str = Field(min_length=1, max_length=255)


class StockRead(BaseModel):
    product_id: int
    product_name: str
    warehouse_id: int
    warehouse_name: str
    on_hand: int
    reserved: int
    available: int  # on_hand - reserved, computed here, never stored

    @classmethod
    def from_model(cls, stock) -> "StockRead":
        return cls(
            product_id=stock.product_id,
            product_name=stock.product.name,
            warehouse_id=stock.warehouse_id,
            warehouse_name=stock.warehouse.name,
            on_hand=stock.on_hand,
            reserved=stock.reserved,
            available=stock.on_hand - stock.reserved,
        )
