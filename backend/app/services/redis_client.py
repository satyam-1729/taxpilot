from redis.asyncio import Redis

from app.core.config import get_settings

_client: Redis | None = None


async def init_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        await _client.ping()
    return _client


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError("Redis not initialised — lifespan did not run")
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def incr_with_ttl(key: str, ttl_seconds: int) -> int:
    """Atomic increment with TTL on first touch. Returns the current count."""
    client = get_redis()
    async with client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, nx=True)
        count, _ = await pipe.execute()
    return int(count)
