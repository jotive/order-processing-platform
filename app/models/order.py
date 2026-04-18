from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','processing','shipped','delivered','cancelled')",
            name="ck_orders_status",
        ),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonneg"),
        UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
        Index("ix_orders_created_at_id", "created_at", "id"),
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonneg"),
        Index("ix_order_items_order_id", "order_id"),
    )
