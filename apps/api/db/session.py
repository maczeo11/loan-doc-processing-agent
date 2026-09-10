"""
Database session and connection management for PostgreSQL with asyncpg and SQLAlchemy 2.x.

Authoritative Persistence Rules:
- PostgreSQL is authoritative for durable business state.
- Transactional operations yield an AsyncSession with auto-rollback on error and clean disposal.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from apps.api.config import settings


def get_async_engine(
    database_url: Optional[str] = None,
    echo: Optional[bool] = None,
) -> AsyncEngine:
    """
    Factory creating a configured SQLAlchemy AsyncEngine.
    """
    url = database_url or settings.DATABASE_URL
    echo_mode = echo if echo is not None else getattr(settings, "DATABASE_ECHO", False)

    if url.startswith("postgresql://"):
        # Bare sync-scheme URL (e.g. worker env): the async engine needs an
        # async driver, and asyncpg is the house driver. Normalize instead of
        # crashing at import with MissingDriver (psycopg2).
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    if url.startswith("sqlite"):
        # SQLite in-memory / file for testing
        return create_async_engine(
            url,
            echo=echo_mode,
            future=True,
        )
    else:
        # PostgreSQL with asyncpg connection pool
        return create_async_engine(
            url,
            echo=echo_mode,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            future=True,
        )


def get_session_factory(bind_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Factory creating an async_sessionmaker bound to the given engine.
    """
    return async_sessionmaker(
        bind=bind_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# Frozen specification: async_engine and async_sessionmaker(bind=async_engine, expire_on_commit=False)
async_engine: AsyncEngine = get_async_engine()
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
engine: AsyncEngine = async_engine  # Alias for backward compatibility


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an active AsyncSession.
    Ensures rollback on exceptions and cleanup on exit.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
