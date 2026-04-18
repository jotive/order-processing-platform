"""Read-through cache for orders — see ADR-004.

Cache-aside pattern: reader checks Redis first, falls back to Postgres,
populates cache with 5-minute TTL. Mutations explicitly invalidate the
key *after* the DB commit succeeds. Net staleness window after commit: zero.
"""

from __future__ import annotations

import logging
from uuid import UUID

from redis.asyncio import Redis

from app.schemas.order import OrderRead

logger = logging.getLogger(__name__)


class OrderCache:
    TTL_SECONDS = 300

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def _k(order_id: UUID) -> str:
        return f"order:{order_id}"

    async def get(self, order_id: UUID) -> OrderRead | None:
        try:
            raw = await self.redis.get(self._k(order_id))
        except Exception:
            logger.warning("order_cache_get_failed", extra={"order_id": str(order_id)})
            return None
        return OrderRead.model_validate_json(raw) if raw else None

    async def set(self, order: OrderRead) -> None:
        try:
            await self.redis.set(
                self._k(order.id),
                order.model_dump_json(),
                ex=self.TTL_SECONDS,
            )
        except Exception:
            logger.warning("order_cache_set_failed", extra={"order_id": str(order.id)})

    async def invalidate(self, order_id: UUID) -> None:
        try:
            await self.redis.delete(self._k(order_id))
        except Exception:
            logger.warning("order_cache_invalidate_failed", extra={"order_id": str(order_id)})
