from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import Cursor
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate, OrderStatus


class OrderConflict(Exception):
    """Idempotency key collision — same key, different payload."""


class OrderNotFound(Exception):
    pass


class InvalidStatusTransition(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition {current} -> {target}")
        self.current = current
        self.target = target


# Directed graph of legal status moves — see ADR-00X (pending).
_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING.value: {
        OrderStatus.CONFIRMED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.CONFIRMED.value: {
        OrderStatus.PROCESSING.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.PROCESSING.value: {
        OrderStatus.SHIPPED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.SHIPPED.value: {OrderStatus.DELIVERED.value},
    OrderStatus.DELIVERED.value: set(),
    OrderStatus.CANCELLED.value: set(),
}


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, body: OrderCreate, idempotency_key: str | None) -> Order:
        total = sum(
            (item.unit_price * item.quantity for item in body.items),
            start=Decimal("0"),
        )
        order = Order(
            customer_id=body.customer_id,
            currency=body.currency,
            total_amount=total,
            idempotency_key=idempotency_key,
            status=OrderStatus.PENDING.value,
        )
        order.items = [
            OrderItem(
                sku=item.sku,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in body.items
        ]
        self.session.add(order)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            raise OrderConflict("Idempotency key collision") from e
        await self.session.refresh(order, attribute_names=["items"])
        return order

    async def get_by_idempotency_key(self, key: str) -> Order | None:
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.idempotency_key == key)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get(self, order_id: UUID) -> Order:
        order = await self.session.get(
            Order, order_id, options=[selectinload(Order.items)]
        )
        if order is None:
            raise OrderNotFound(str(order_id))
        return order

    async def list_page(
        self,
        *,
        cursor: Cursor | None,
        size: int,
        customer_id: UUID | None = None,
        status: OrderStatus | None = None,
    ) -> tuple[list[Order], Cursor | None]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
        )

        if cursor is not None:
            stmt = stmt.where(
                or_(
                    Order.created_at < cursor.created_at,
                    and_(Order.created_at == cursor.created_at, Order.id < cursor.id),
                )
            )
        if customer_id is not None:
            stmt = stmt.where(Order.customer_id == customer_id)
        if status is not None:
            stmt = stmt.where(Order.status == status.value)

        stmt = stmt.limit(size + 1)
        rows = list((await self.session.execute(stmt)).scalars().all())

        next_cursor: Cursor | None = None
        if len(rows) > size:
            tail = rows[size - 1]
            next_cursor = Cursor(created_at=tail.created_at, id=tail.id)
            rows = rows[:size]
        return rows, next_cursor

    async def update_status(self, order_id: UUID, target: OrderStatus) -> Order:
        order = await self.get(order_id)
        if target.value not in _TRANSITIONS[order.status]:
            raise InvalidStatusTransition(order.status, target.value)
        order.status = target.value
        await self.session.flush()
        return order

    async def cancel(self, order_id: UUID) -> Order:
        return await self.update_status(order_id, OrderStatus.CANCELLED)
