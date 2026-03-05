"""
Database session management.
Provides async SQLAlchemy engine and session factory.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

import asyncio
import weakref
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings

# Maintain database connection engines isolated per event loop
# FastAPI uses one main loop natively mapping to exactly one engine.
# Celery spawns unique loops per task natively isolating its pools dynamically!
_loop_engines = weakref.WeakKeyDictionary()

def _get_engine():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop is not None:
        if loop not in _loop_engines:
            _loop_engines[loop] = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                pool_size=30,          # Boosted to support concurrent deep scraper tests
                max_overflow=50,       # Boosted to handle burst ingestion
                pool_timeout=60.0,     # Give the queue longer to find a connection
                pool_pre_ping=True,
            )
        return _loop_engines[loop]
    else:
        # Fallback explicitly isolated per call if no loop is running
        return create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=30,
            max_overflow=50,
            pool_timeout=60.0,
            pool_pre_ping=True,
        )

def async_session_factory() -> AsyncSession:
    """
    Factory function returning an isolated AsyncSession bound explicitly
    to the globally scoped engine instantiated dynamically above matching the active loop natively.
    """
    engine = _get_engine()
    return AsyncSession(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is automatically committed on success or rolled back
    The context manager handles closing - no explicit
    close() needed (avoids double-close). Routing that mutates
    data must explicitly call await db.commit().
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
