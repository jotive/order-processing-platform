from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.v1.dependencies import IdempotencyStoreDep, OrderRepoDep
from app.core.pagination import Cursor, InvalidCursor
from app.schemas.errors import ProblemDetail
from app.schemas.order import (
    OrderCreate,
    OrderRead,
    OrderStatus,
    OrderStatusUpdate,
    PaginatedOrders,
)
from app.services.order_repository import (
    InvalidStatusTransition,
    OrderConflict,
    OrderNotFound,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderRead,
    responses={
        409: {
            "model": ProblemDetail,
            "description": "Idempotency key reused with different payload",
        },
        422: {"model": ProblemDetail, "description": "Validation error"},
    },
    summary="Create order",
    description=(
        "Creates an order. **Idempotent** via `Idempotency-Key` header. "
        "Repeating the same key with the same payload returns the original order. "
        "Reusing a key with a *different* payload returns 409."
    ),
)
async def create_order(
    body: OrderCreate,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Client-generated unique key, max 128 chars",
        ),
    ],
    repo: OrderRepoDep,
    idem: IdempotencyStoreDep,
) -> OrderRead:
    if len(idempotency_key) > 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key exceeds 128 chars")

    payload_hash = idem.hash_payload(body.model_dump(mode="json"))
    cached = await idem.get(idempotency_key)
    if cached is not None:
        if cached["hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key reused with a different payload",
            )
        existing = await repo.get(UUID(cached["order_id"]))
        return OrderRead.model_validate(existing)

    try:
        order = await repo.create(body, idempotency_key=idempotency_key)
    except OrderConflict:
        # Race: another request bound this key between our cache-check and insert.
        cached = await idem.get(idempotency_key)
        if cached is None:
            raise HTTPException(status_code=409, detail="Idempotency conflict") from None
        if cached["hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key reused with a different payload",
            ) from None
        existing = await repo.get(UUID(cached["order_id"]))
        return OrderRead.model_validate(existing)

    await idem.put(idempotency_key, payload_hash, str(order.id))
    return OrderRead.model_validate(order)


@router.get(
    "",
    response_model=PaginatedOrders,
    summary="List orders (cursor pagination)",
    description=(
        "Returns a page ordered by `created_at DESC, id DESC`. Cursor-based — see ADR-002. "
        "Pass `cursor` from a previous response to fetch the next page."
    ),
)
async def list_orders(
    repo: OrderRepoDep,
    customer_id: UUID | None = Query(default=None),
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None, description="Opaque cursor from previous response"),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedOrders:
    parsed: Cursor | None = None
    if cursor is not None:
        try:
            parsed = Cursor.decode(cursor)
        except InvalidCursor as e:
            raise HTTPException(status_code=422, detail=f"Invalid cursor: {e}") from e

    rows, next_cursor = await repo.list_page(
        cursor=parsed, size=size, customer_id=customer_id, status=order_status
    )
    return PaginatedOrders(
        data=[OrderRead.model_validate(r) for r in rows],
        next_cursor=next_cursor.encode() if next_cursor else None,
        size=len(rows),
    )


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    responses={404: {"model": ProblemDetail, "description": "Order not found"}},
    summary="Get order by ID",
)
async def get_order(order_id: UUID, repo: OrderRepoDep) -> OrderRead:
    try:
        order = await repo.get(order_id)
    except OrderNotFound as e:
        raise HTTPException(status_code=404, detail="Order not found") from e
    return OrderRead.model_validate(order)


@router.put(
    "/{order_id}/status",
    response_model=OrderRead,
    responses={
        404: {"model": ProblemDetail, "description": "Order not found"},
        409: {"model": ProblemDetail, "description": "Invalid status transition"},
    },
    summary="Update order status",
    description=(
        "Transitions: `pending → confirmed → processing → shipped → delivered`. "
        "Cancellation allowed from any non-terminal state."
    ),
)
async def update_order_status(
    order_id: UUID, body: OrderStatusUpdate, repo: OrderRepoDep
) -> OrderRead:
    try:
        order = await repo.update_status(order_id, body.status)
    except OrderNotFound as e:
        raise HTTPException(status_code=404, detail="Order not found") from e
    except InvalidStatusTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return OrderRead.model_validate(order)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ProblemDetail, "description": "Order not found"},
        409: {"model": ProblemDetail, "description": "Order cannot be cancelled in current state"},
    },
    summary="Cancel order",
)
async def cancel_order(order_id: UUID, repo: OrderRepoDep) -> None:
    try:
        await repo.cancel(order_id)
    except OrderNotFound as e:
        raise HTTPException(status_code=404, detail="Order not found") from e
    except InvalidStatusTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
