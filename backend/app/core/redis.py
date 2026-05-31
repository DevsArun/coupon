"""Redis connection and caching utilities."""
import json
from typing import Optional, Any
import redis.asyncio as redis

from app.core.config import settings

redis_client: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection."""
    global redis_client
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    return redis_client


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


class CacheService:
    """High-level caching operations."""

    def __init__(self, prefix: str = "couponai"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        r = get_redis()
        value = await r.get(self._key(key))
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        r = get_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await r.setex(self._key(key), ttl, serialized)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        r = get_redis()
        await r.delete(self._key(key))

    async def increment(self, key: str, ttl: int = 86400) -> int:
        """Increment counter with TTL."""
        r = get_redis()
        full_key = self._key(key)
        count = await r.incr(full_key)
        if count == 1:
            await r.expire(full_key, ttl)
        return count

    async def get_count(self, key: str) -> int:
        """Get current counter value."""
        r = get_redis()
        val = await r.get(self._key(key))
        return int(val) if val else 0

    async def flush_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        r = get_redis()
        async for key in r.scan_iter(match=self._key(pattern)):
            await r.delete(key)


cache = CacheService()
