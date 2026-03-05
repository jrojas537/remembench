"""
Remembench — Redis Caching Layer

Provides a global asynchronous Redis client based on settings.redis_url.
"""

import asyncio
import weakref
from collections.abc import AsyncGenerator
import redis.asyncio as redis

from app.config import settings
from app.logging import get_logger

logger = get_logger("cache")

# Maintain connection pools perfectly isolated per event loop
# FastAPI natively uses one main loop, mapping to exactly 1 permanent global pool.
# Celery spawns a unique loop per task, keeping concurrent background jobs strictly memory-safe.
_loop_pools = weakref.WeakKeyDictionary()

def _get_pool() -> redis.ConnectionPool:
    loop = asyncio.get_running_loop()
    if loop not in _loop_pools:
        _loop_pools[loop] = redis.ConnectionPool.from_url(
            settings.redis_url, 
            decode_responses=True,
            max_connections=50,
            socket_timeout=5.0
        )
    return _loop_pools[loop]

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Yields an async Redis client securely bound to the active thread's loop."""
    client = redis.Redis(connection_pool=_get_pool())
    try:
        yield client
    finally:
        await client.aclose()
