"""Database access layer (Neon Postgres + PostGIS)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings


class Base(DeclarativeBase):
    pass


def _async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


settings = get_settings()
engine = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None

if settings.database_url:
    engine = create_async_engine(
        _async_database_url(settings.database_url),
        pool_pre_ping=True,
    )
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        raise RuntimeError("Database session is not configured. Set DATABASE_URL.")
    async with SessionLocal() as session:
        yield session
