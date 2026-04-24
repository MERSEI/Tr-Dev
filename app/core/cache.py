import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class Cache:
    PREFIX = "analysis:"

    def __init__(self, redis: aioredis.Redis | None = None) -> None:
        self._r = redis or get_redis()

    def _key(self, handle: str) -> str:
        return f"{self.PREFIX}{handle.lower().lstrip('@')}"

    async def get(self, handle: str) -> dict[str, Any] | None:
        raw = await self._r.get(self._key(handle))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("cache_decode_error", handle=handle)
            return None

    async def set(self, handle: str, data: dict[str, Any]) -> None:
        await self._r.setex(
            self._key(handle),
            settings.cache_ttl_seconds,
            json.dumps(data, ensure_ascii=False, default=str),
        )

    async def delete(self, handle: str) -> None:
        await self._r.delete(self._key(handle))


def get_cache() -> Cache:
    return Cache()
