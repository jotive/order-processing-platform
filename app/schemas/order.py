from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, description="Must be positive")
    unit_price: float = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: UUID
    items: list[OrderItemCreate] = Field(min_length=1)
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    product_id: UUID
    quantity: int
    unit_price: float
    subtotal: float


class OrderRead(BaseModel):
    id: UUID
    customer_id: UUID
    status: OrderStatus
    items: list[OrderItemRead]
    total: float
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedOrders(BaseModel):
    data: list[OrderRead]
    next_cursor: str | None = Field(default=None, description="Opaque cursor for next page. Null when no more pages.")
    size: int
