"""
Remembench — Redis Caching Layer

Provides a global asynchronous Redis client based on settings.redis_url.
"""

from collections.abc import AsyncGenerator
import redis.asyncio as redis

from app.config import settings
from app.logging import get_logger

logger = get_logger("cache")

# Maintain a single connection pool globally
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url, 
    decode_responses=True,
    max_connections=10
)

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI dependency that yields an async Redis client."""
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
