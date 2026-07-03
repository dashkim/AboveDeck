"""Database access layer (Neon Postgres + PostGIS).

When Neon is wired up:
  1. Add sqlalchemy[asyncio] and asyncpg to requirements.txt
  2. Create an async engine from DATABASE_URL
  3. Implement get_session() for route handlers
  4. PostGIS bbox queries for peaks live here (see planning/OVERARCHING_PLAN.md)
"""

from collections.abc import AsyncIterator
from typing import Any


async def get_session() -> AsyncIterator[Any]:
    """Yield a database session once Neon is configured."""
    raise NotImplementedError("Database session is not implemented yet.")
    yield  # pragma: no cover
