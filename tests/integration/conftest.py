from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://opp:opp@localhost:5432/opp_test",
)


_schema_ready = False


@pytest_asyncio.fixture
async def engine():
    # NullPool: pytest-asyncio gives each test a fresh event loop. Any connection
    # pooled from a prior test is bound to a dead loop and blows up with
    # "Future attached to a different loop" on the next reuse.
    global _schema_ready
    eng = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    if not _schema_ready:
        from app.db.base import Base
        from app.models import Order, OrderItem  # noqa: F401

        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _schema_ready = True
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
def fake_redis() -> AsyncMock:
    """In-memory fake for Redis. Cache tests verify behavior end-to-end;
    rate-limit/idempotency wire through but we don't exercise Redis semantics here."""
    store: dict[str, str] = {}

    async def _get(k):
        return store.get(k)

    async def _set(k, v, ex=None, nx=False):
        if nx and k in store:
            return None
        store[k] = v
        return True

    async def _delete(k):
        store.pop(k, None)
        return 1

    async def _evalsha(*_a, **_kw):
        return [1, "999", 0]

    async def _script_load(_):
        return "sha"

    async def _aclose():
        return None

    redis = AsyncMock()
    redis.get.side_effect = _get
    redis.set.side_effect = _set
    redis.delete.side_effect = _delete
    redis.evalsha.side_effect = _evalsha
    redis.script_load.side_effect = _script_load
    redis.aclose.side_effect = _aclose
    return redis


@pytest_asyncio.fixture
async def client(engine, fake_redis) -> AsyncIterator[AsyncClient]:
    from app.api.v1.dependencies import db_session as db_session_dep
    from app.api.v1.dependencies import redis_client
    from app.main import app

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _db_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[db_session_dep] = _db_override
    app.dependency_overrides[redis_client] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
