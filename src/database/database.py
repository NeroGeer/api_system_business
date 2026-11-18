import json
from enum import Enum
from typing import Annotated, Type, Callable, Awaitable, Any
from datetime import datetime, UTC, date

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.config import settings
from src.logger.logger import logger

DATABASE_URL: str = str(settings.db.url)

engine = create_async_engine(DATABASE_URL, echo=True)
logger.info(f"Async database engine created for {DATABASE_URL}")

async_session = async_sessionmaker(engine, expire_on_commit=False)
logger.debug("Async session maker initialized")


async def get_session() -> AsyncSession:
    """
    FastAPI dependency that provides an asynchronous SQLAlchemy session.

    Yields:
        AsyncSession: Active database session.

    Notes:
        - Session is automatically closed after request ends.
        - Safe for use in FastAPI dependency injection system.
    """
    async with async_session() as session:
        logger.debug("New database session opened")
        yield session
        logger.debug("Database session closed")


SessionDep: Type[AsyncSession] = Annotated[AsyncSession, Depends(get_session)]

redis_client = Redis(
    host=settings.redis.url, port=settings.redis.port, decode_responses=True
)


async def get_redis_client() -> Redis:
    """
    FastAPI dependency that provides a Redis client instance.

    Returns:
        Redis: Shared async Redis client.

    Notes:
        - Uses a single global Redis connection.
        - Suitable for high-performance caching and pub/sub usage.
    """
    yield redis_client


RedisDep: Type[Redis] = Annotated[Redis, Depends(get_redis_client)]


class RedisKeys(str, Enum):
    """
    Redis key templates used across the application.

    Attributes:
        TASK_COMMENTS:
            Key pattern for storing comments of a specific task.
            Requires `task_id` parameter.

    Example:
        RedisKeys.TASK_COMMENTS.format(task_id=123)
        -> "task:123:comments"
    """

    TASK_COMMENTS = "task:{task_id}:comments"
    TASK_STAGE = "task:{task_id}:stage"
    STAGE_TRANSACTION = "task:{task_id}:stage:transactions"
    TEAM_STAGE_TRANSITIONS = "team:{team_id}:stage:transitions"

    def format(self, **kwargs):
        """
        Formats Redis key with dynamic parameters.

        Args:
            **kwargs: Values to replace placeholders in key template.

        Returns:
            str: Fully formatted Redis key.
        """
        return self.value.format(**kwargs)


class RedisStageService:

    CACHE_TTL = 3600

    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def _json_default(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Enum):
            return value.value

        raise TypeError(
            f"Object of type {type(value).__name__} "
            "is not JSON serializable"
        )

    async def _get_or_set(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
    ) -> Any:
        cached = await self.redis.get(key)

        if cached is not None:
            return json.loads(cached)

        data = await loader()

        await self.redis.set(
            key,
            json.dumps(
                data,
                ensure_ascii=False,
                default=self._json_default,
            ),
            ex=self.CACHE_TTL,
        )

        return data

    async def get_task_transactions(
        self,
        task_id: int,
        loader: Callable[[], Awaitable[list]],
    ) -> list:

        key = RedisKeys.STAGE_TRANSACTION.format(
            task_id=task_id
        )

        return await self._get_or_set(key, loader)

    async def invalidate_task_transactions(
        self,
        task_id: int,
    ) -> None:

        key = RedisKeys.STAGE_TRANSACTION.format(
            task_id=task_id
        )

        await self.redis.delete(key)

    async def get_team_transitions(
        self,
        team_id: int,
        loader: Callable[[], Awaitable[list]],
    ) -> list:

        key = RedisKeys.TEAM_STAGE_TRANSITIONS.format(
            team_id=team_id
        )

        return await self._get_or_set(key, loader)

    async def invalidate_team_transitions(
        self,
        team_id: int,
    ) -> None:

        key = RedisKeys.TEAM_STAGE_TRANSITIONS.format(
            team_id=team_id
        )

        await self.redis.delete(key)

    async def invalidate_team_stage_cache(
        self,
        team_id: int,
    ) -> None:

        keys = [
            RedisKeys.TEAM_STAGE_TRANSITIONS.format(
                team_id=team_id
            )
        ]

        if keys:
            await self.redis.delete(*keys)