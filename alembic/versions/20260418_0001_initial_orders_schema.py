"""initial orders schema

Revision ID: 0001
Revises:
Create Date: 2026-04-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending','confirmed','processing','shipped','delivered','cancelled')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonneg"),
        sa.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
    )
    op.create_index("ix_orders_created_at_id", "orders", ["created_at", "id"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_qty_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonneg"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_index("ix_orders_created_at_id", table_name="orders")
    op.drop_table("orders")
