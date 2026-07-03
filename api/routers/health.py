from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["configured", "not_configured"]


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        database="configured" if settings.database_configured else "not_configured",
    )
