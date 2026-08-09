from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text

from config import Settings, get_settings
from db import SessionLocal

router = APIRouter(tags=["health"])

KEEPALIVE_STALE_AFTER = timedelta(minutes=15)

_last_keepalive_at: datetime | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["connected", "not_configured", "error"]
    keepalive_last_ping_at: str | None
    keepalive_status: Literal["ok", "stale", "unknown"]


def _keepalive_fields(record: bool) -> tuple[str | None, Literal["ok", "stale", "unknown"]]:
    global _last_keepalive_at
    now = datetime.now(timezone.utc)
    if record:
        _last_keepalive_at = now

    if _last_keepalive_at is None:
        return None, "unknown"

    last = _last_keepalive_at
    age = now - last
    status: Literal["ok", "stale", "unknown"] = "ok" if age <= KEEPALIVE_STALE_AFTER else "stale"
    return last.isoformat().replace("+00:00", "Z"), status


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    source: str | None = Query(default=None),
) -> HealthResponse:
    last_ping_at, keepalive_status = _keepalive_fields(record=source == "keepalive")

    if not settings.database_configured or SessionLocal is None:
        return HealthResponse(
            status="ok",
            database="not_configured",
            keepalive_last_ping_at=last_ping_at,
            keepalive_status=keepalive_status,
        )

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return HealthResponse(
            status="ok",
            database="connected",
            keepalive_last_ping_at=last_ping_at,
            keepalive_status=keepalive_status,
        )
    except Exception:
        return HealthResponse(
            status="degraded",
            database="error",
            keepalive_last_ping_at=last_ping_at,
            keepalive_status=keepalive_status,
        )
