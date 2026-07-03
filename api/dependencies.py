from fastapi import Depends, HTTPException

from config import Settings, get_settings


def require_db(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.database_configured:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL to enable this endpoint.",
        )
    return settings
