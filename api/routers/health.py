from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from config import Settings, get_settings
from db import SessionLocal

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["connected", "not_configured", "error"]


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    if not settings.database_configured or SessionLocal is None:
        return HealthResponse(status="ok", database="not_configured")

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return HealthResponse(status="ok", database="connected")
    except Exception:
        return HealthResponse(status="degraded", database="error")
