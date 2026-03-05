"""
Database session management.
Provides async SQLAlchemy engine and session factory.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=30,          # Boosted from 10 to support concurrent deep scraper tests natively
    max_overflow=50,       # Boosted from 20 to handle burst ingestion
    pool_timeout=60.0,     # Give the queue longer to find a connection before throwing Errno 61
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


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
