from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.rate_limit import TokenBucketLimiter

_EXEMPT_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, limiter: TokenBucketLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_id = self._client_id(request)
        result = await self.limiter.acquire(client_id)

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "/errors/429",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Rate limit exceeded",
                    "instance": str(request.url.path),
                },
                headers={"Retry-After": str(result.retry_after_seconds)},
                media_type="application/problem+json",
            )

        response = await call_next(request)
        if result.tokens_remaining >= 0:
            response.headers["X-RateLimit-Remaining"] = str(int(result.tokens_remaining))
        return response

    @staticmethod
    def _client_id(request: Request) -> str:
        # TODO: switch to authenticated principal when auth lands.
        return request.client.host if request.client else "unknown"
