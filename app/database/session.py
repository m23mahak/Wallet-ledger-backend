"""Async engine and session factory."""
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.configuration.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
)

# expire_on_commit=False: objects stay readable after commit (important in async).
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Services own commit/rollback for financial operations."""
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection() -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
