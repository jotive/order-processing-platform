from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis, from_url

from app.core.config import get_settings

settings = get_settings()

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = from_url(settings.redis_url, decode_responses=True)
    return _client


class IdempotencyStore:
    """Binds an Idempotency-Key header to the response that was first served.

    Key shape: `idem:{key}`. Value: `{"hash": <sha256 of request body>, "order_id": "..."}`.
    TTL: 24h (clients that retry beyond that get a fresh attempt).
    """

    TTL_SECONDS = 60 * 60 * 24

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def _k(key: str) -> str:
        return f"idem:{key}"

    @staticmethod
    def hash_payload(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get(self, key: str) -> dict[str, str] | None:
        raw = await self.redis.get(self._k(key))
        return json.loads(raw) if raw else None

    async def put(self, key: str, payload_hash: str, order_id: str) -> bool:
        """Returns True if stored, False if key already existed."""
        value = json.dumps({"hash": payload_hash, "order_id": order_id})
        stored = await self.redis.set(self._k(key), value, ex=self.TTL_SECONDS, nx=True)
        return bool(stored)
