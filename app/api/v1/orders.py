from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.schemas.errors import ProblemDetail
from app.schemas.order import (
    OrderCreate,
    OrderRead,
    OrderStatus,
    OrderStatusUpdate,
    PaginatedOrders,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderRead,
    responses={
        409: {"model": ProblemDetail, "description": "Duplicate idempotency key with different payload"},
        422: {"model": ProblemDetail, "description": "Validation error"},
    },
    summary="Create order",
    description=(
        "Creates an order. **Idempotent**: repeat the same `Idempotency-Key` header to "
        "retrieve the original result without re-executing side effects.\n\n"
        "The key is cached for 24 hours. See ADR-006 (idempotency strategy)."
    ),
)
async def create_order(
    body: OrderCreate,
    idempotency_key: Annotated[UUID, Header(description="Unique key for idempotent creation")],
) -> OrderRead:
    raise HTTPException(status_code=501, detail="Not implemented yet — wiring in Bloque 3")


@router.get(
    "",
    response_model=PaginatedOrders,
    summary="List orders (cursor pagination)",
    description=(
        "Returns a page of orders ordered by `created_at DESC`. **Cursor-based pagination** — "
        "see ADR-002 for trade-off vs offset.\n\n"
        "Pass `cursor` from a previous response to fetch the next page. Absent cursor fetches the first page."
    ),
)
async def list_orders(
    customer_id: UUID | None = Query(default=None),
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None, description="Opaque cursor from previous response"),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedOrders:
    raise HTTPException(status_code=501, detail="Not implemented yet — wiring in Bloque 3")


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    responses={404: {"model": ProblemDetail, "description": "Order not found"}},
    summary="Get order by ID",
)
async def get_order(order_id: UUID) -> OrderRead:
    raise HTTPException(status_code=501, detail="Not implemented yet — wiring in Bloque 3")


@router.put(
    "/{order_id}/status",
    response_model=OrderRead,
    responses={
        404: {"model": ProblemDetail, "description": "Order not found"},
        409: {"model": ProblemDetail, "description": "Invalid status transition"},
    },
    summary="Update order status",
    description=(
        "Idempotent status update. Valid transitions: "
        "`pending → confirmed → processing → shipped → delivered`. "
        "Cancellation allowed from any non-terminal state."
    ),
)
async def update_order_status(order_id: UUID, body: OrderStatusUpdate) -> OrderRead:
    raise HTTPException(status_code=501, detail="Not implemented yet — wiring in Bloque 3")


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel order (idempotent soft-delete)",
)
async def cancel_order(order_id: UUID) -> None:
    raise HTTPException(status_code=501, detail="Not implemented yet — wiring in Bloque 3")
