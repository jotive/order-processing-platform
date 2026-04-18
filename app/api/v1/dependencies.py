from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.db.redis import IdempotencyStore, get_redis
from app.services.order_repository import OrderRepository


async def db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def redis_client() -> Redis:
    return get_redis()


def order_repo(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> OrderRepository:
    return OrderRepository(session)


def idempotency_store(
    redis: Annotated[Redis, Depends(redis_client)],
) -> IdempotencyStore:
    return IdempotencyStore(redis)


DbSession = Annotated[AsyncSession, Depends(db_session)]
OrderRepoDep = Annotated[OrderRepository, Depends(order_repo)]
IdempotencyStoreDep = Annotated[IdempotencyStore, Depends(idempotency_store)]
