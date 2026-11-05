"""Async SQLAlchemy engine + session factory for PostgreSQL (same as Tangent).

DATABASE_URL comes from the environment (docker compose provides it).
Format: postgresql+asyncpg://user:password@host:port/dbname
"""

import logging
import os
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

# Local fallback for running uvicorn outside Docker (dev compose binds 5433).
_DEFAULT_URL = "postgresql+asyncpg://caseduo:caseduo_dev@localhost:5433/caseduo"
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_URL)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one AsyncSession per request."""
    async with async_session_factory() as session:
        yield session


async def ping() -> bool:
    """True if the DB answers. Used by /api/health."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("DB ping failed: %s", exc)
        return False
