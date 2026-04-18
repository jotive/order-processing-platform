from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import TokenBucketLimiter
from app.db.redis import get_redis
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    redis = get_redis()
    limiter = TokenBucketLimiter(redis)
    app.state.limiter = limiter
    yield
    await redis.aclose()


app = FastAPI(
    title="Order Processing Platform",
    version="0.1.0",
    description=(
        "Production-grade order processing backend — part of the "
        "[jotive.dev](https://dev.jotive.com.co) technical portfolio.\n\n"
        "See [Architecture Decision Records]"
        "(https://github.com/jotive/order-processing-platform/tree/main/docs/adr) "
        "for design rationale."
    ),
    contact={"name": "Jotive.dev", "url": "https://dev.jotive.com.co"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# Order matters: context first (so logs carry request_id), then rate limit.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=TokenBucketLimiter(get_redis()))

app.include_router(api_v1_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """RFC 7807 — Problem Details for HTTP APIs."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"/errors/{exc.status_code}",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "status": exc.status_code,
            "detail": exc.detail if isinstance(exc.detail, str) else None,
            "instance": str(request.url.path),
        },
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "message": e.get("msg", "")}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "type": "/errors/validation",
            "title": "Validation Error",
            "status": 422,
            "detail": "One or more fields failed validation",
            "instance": str(request.url.path),
            "errors": errors,
        },
        media_type="application/problem+json",
    )


@app.get("/health", tags=["meta"], summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.api_env}
