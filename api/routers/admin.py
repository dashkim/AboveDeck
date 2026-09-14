"""Password-gated admin actions (status page overrides)."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from db import get_session
from dependencies import require_db
from models.peaks import Peak
from services.weather_forecast import MODEL_VERSION, PeakLocation, refresh_peak_forecasts

router = APIRouter(prefix="/admin", tags=["admin"])


class ForecastCacheRequest(BaseModel):
    password: str = Field(min_length=1)
    limit: int = Field(200, ge=1, le=500, description="Highest peaks to score now")
    forecast_days: int = Field(3, ge=1, le=7)
    refresh_now: bool = True
    trigger_nightly: bool = True


class ForecastCacheResponse(BaseModel):
    ok: bool
    model_version: str
    peak_count: int = 0
    refreshed_rows: int = 0
    dates: list[date] = Field(default_factory=list)
    nightly_workflow: str
    message: str


def _check_password(password: str, settings: Settings) -> None:
    expected = settings.admin_override_password or ""
    if not expected or not secrets.compare_digest(password, expected):
        raise HTTPException(status_code=401, detail="Invalid override password")


async def _dispatch_nightly_workflow(settings: Settings) -> str:
    token = (settings.github_token or "").strip()
    if not token:
        return "skipped_no_github_token"

    url = (
        f"https://api.github.com/repos/{settings.github_repo}"
        f"/actions/workflows/{settings.github_workflow_file}/dispatches"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json={"ref": settings.github_ref},
            )
        if response.status_code in (201, 204):
            return "dispatched"
        return f"failed_http_{response.status_code}: {response.text[:200]}"
    except Exception as exc:  # noqa: BLE001 — surface to operator UI
        return f"failed: {exc}"


@router.post("/run-forecast-cache", response_model=ForecastCacheResponse)
async def run_forecast_cache(
    body: ForecastCacheRequest,
    _db=Depends(require_db),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ForecastCacheResponse:
    """Status-page override: score top peaks now and/or dispatch the nightly GHA job."""
    _check_password(body.password, settings)

    nightly = "skipped"
    if body.trigger_nightly:
        nightly = await _dispatch_nightly_workflow(settings)

    refreshed_rows = 0
    peak_count = 0
    dates: list[date] = []

    if body.refresh_now:
        stmt = (
            select(
                Peak.id,
                func.ST_Y(Peak.geom).label("lat"),
                func.ST_X(Peak.geom).label("lon"),
                Peak.elevation_m,
                Peak.prominence_m,
            )
            .where(Peak.elevation_m.is_not(None))
            .order_by(Peak.elevation_m.desc())
            .limit(body.limit)
        )
        rows = (await session.execute(stmt)).all()
        locations = [
            PeakLocation(
                id=row.id,
                lat=float(row.lat),
                lon=float(row.lon),
                elevation_m=float(row.elevation_m),
                prominence_m=float(row.prominence_m) if row.prominence_m is not None else None,
            )
            for row in rows
        ]
        peak_count = len(locations)
        today = datetime.now(timezone.utc).date()
        dates = [today + timedelta(days=offset) for offset in range(body.forecast_days)]
        try:
            for target in dates:
                refreshed_rows += await refresh_peak_forecasts(
                    session,
                    locations,
                    target,
                    max_peaks=body.limit,
                )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Weather fetch failed after partial work: {exc}",
            ) from exc

    parts = []
    if body.refresh_now:
        parts.append(f"scored {peak_count} peaks → {refreshed_rows} rows ({MODEL_VERSION})")
    parts.append(f"nightly workflow: {nightly}")
    return ForecastCacheResponse(
        ok=True,
        model_version=MODEL_VERSION,
        peak_count=peak_count,
        refreshed_rows=refreshed_rows,
        dates=dates,
        nightly_workflow=nightly,
        message="; ".join(parts),
    )
