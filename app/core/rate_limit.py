"""Token bucket rate limiter — see ADR-004.

Bucket state (tokens, last_refill_ms) lives in Redis under `rl:{client}`.
Updates are atomic via a Lua script — no race between concurrent requests
from the same client. On Redis unreachable: fail open (log + allow) so a
cache outage never cascades into an API outage.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# KEYS[1] = bucket key
# ARGV[1] = capacity (max tokens)
# ARGV[2] = refill rate (tokens per second)
# ARGV[3] = now (ms since epoch)
# ARGV[4] = cost (tokens to consume)
# Returns: {allowed (0|1), tokens_remaining, retry_after_ms}
_LUA_TOKEN_BUCKET = """
local capacity   = tonumber(ARGV[1])
local rate       = tonumber(ARGV[2])
local now_ms     = tonumber(ARGV[3])
local cost       = tonumber(ARGV[4])

local data = redis.call('HMGET', KEYS[1], 'tokens', 'last_ms')
local tokens  = tonumber(data[1])
local last_ms = tonumber(data[2])

if tokens == nil then
  tokens  = capacity
  last_ms = now_ms
end

local elapsed_ms = math.max(0, now_ms - last_ms)
local refill     = (elapsed_ms / 1000.0) * rate
tokens = math.min(capacity, tokens + refill)

local allowed = 0
local retry_after_ms = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
else
  local deficit = cost - tokens
  retry_after_ms = math.ceil((deficit / rate) * 1000)
end

redis.call('HMSET', KEYS[1], 'tokens', tokens, 'last_ms', now_ms)
redis.call('PEXPIRE', KEYS[1], math.ceil((capacity / rate) * 1000 * 2))

return {allowed, tostring(tokens), retry_after_ms}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    tokens_remaining: float
    retry_after_seconds: int


class TokenBucketLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        capacity: int = 150,
        refill_per_second: float = 100 / 60,  # 100 req/min steady state
    ) -> None:
        self.redis = redis
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._script_sha: str | None = None

    async def _ensure_script(self) -> str:
        if self._script_sha is None:
            self._script_sha = await self.redis.script_load(_LUA_TOKEN_BUCKET)
        return self._script_sha

    async def acquire(self, client_id: str, cost: int = 1) -> RateLimitResult:
        key = f"rl:{client_id}"
        now_ms = int(time.time() * 1000)
        try:
            sha = await self._ensure_script()
            result = await self.redis.evalsha(
                sha,
                1,
                key,
                self.capacity,
                self.refill_per_second,
                now_ms,
                cost,
            )
        except Exception:
            logger.warning("rate_limit_backend_unavailable", extra={"client_id": client_id})
            return RateLimitResult(allowed=True, tokens_remaining=-1, retry_after_seconds=0)

        allowed, tokens, retry_ms = result
        return RateLimitResult(
            allowed=bool(int(allowed)),
            tokens_remaining=float(tokens),
            retry_after_seconds=max(1, int(retry_ms) // 1000) if not int(allowed) else 0,
        )
