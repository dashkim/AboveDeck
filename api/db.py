"""Database access layer (Neon Postgres + PostGIS)."""

from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings


class Base(DeclarativeBase):
    pass


_SSL_QUERY_KEYS = frozenset({"ssl", "sslmode"})


def _async_database_url(url: str) -> tuple[str, dict]:
    """Normalize DATABASE_URL for asyncpg.

    Neon (and many Postgres providers) ship URLs with ``sslmode=require`` or
    ``ssl=require``. Those query params are valid for libpq/psycopg, but asyncpg
    rejects ``sslmode`` as an unexpected connect() kwarg. Strip SSL query keys
    and pass ``connect_args={"ssl": True}`` instead.
    """
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    connect_args: dict = {}
    kept: list[tuple[str, str]] = []
    for key, value in query_pairs:
        if key.lower() in _SSL_QUERY_KEYS:
            # Any explicit ssl/sslmode value means TLS is required (Neon default).
            if value.lower() not in {"disable", "false", "0"}:
                connect_args["ssl"] = True
            continue
        kept.append((key, value))

    cleaned = urlunparse(parsed._replace(query=urlencode(kept)))
    return cleaned, connect_args


settings = get_settings()
engine = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None

if settings.database_url:
    async_url, connect_args = _async_database_url(settings.database_url)
    engine = create_async_engine(
        async_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        raise RuntimeError("Database session is not configured. Set DATABASE_URL.")
    async with SessionLocal() as session:
        yield session
