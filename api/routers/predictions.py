from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import functions as gf
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from dependencies import require_db
from models.peaks import Peak
from schemas.predictions import GridResponse
from services.weather_forecast import MODEL_VERSION, PeakLocation, refresh_peak_forecasts

router = APIRouter(prefix="/predictions", tags=["predictions"])


class RefreshResponse(BaseModel):
    refreshed_rows: int = Field(ge=0)
    peak_count: int = Field(ge=0)
    date: date
    model_version: str = MODEL_VERSION


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = [float(value.strip()) for value in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=422, detail="bbox must be west,south,east,north")
    west, south, east, north = parts
    if west >= east or south >= north:
        raise HTTPException(status_code=422, detail="bbox bounds are invalid")
    return west, south, east, north


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_predictions(
    bbox: str = Query(..., description="west,south,east,north"),
    date: date = Query(..., description="ISO date for predictions"),
    limit: int = Query(80, ge=1, le=200, description="Max peaks to refresh"),
    _settings=Depends(require_db),
    session: AsyncSession = Depends(get_session),
) -> RefreshResponse:
    """Pull Open-Meteo for peaks in view and upsert live rule scores."""
    west, south, east, north = parse_bbox(bbox)
    envelope = gf.ST_MakeEnvelope(west, south, east, north, 4326)
    stmt = (
        select(
            Peak.id,
            func.ST_Y(Peak.geom).label("lat"),
            func.ST_X(Peak.geom).label("lon"),
            Peak.elevation_m,
            Peak.prominence_m,
        )
        .where(Peak.geom.ST_Intersects(envelope), Peak.elevation_m.is_not(None))
        .order_by(Peak.elevation_m.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    locations = [
        PeakLocation(
            id=row.id,
            lat=float(row.lat),
            lon=float(row.lon),
            elevation_m=float(row.elevation_m),
            prominence_m=float(row.prominence_m) if row.prominence_m is not None else None,
        )
        for row in result.all()
    ]
    try:
        refreshed = await refresh_peak_forecasts(
            session, locations, date, max_peaks=limit
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {exc}") from exc

    return RefreshResponse(
        refreshed_rows=refreshed,
        peak_count=len(locations),
        date=date,
        model_version=MODEL_VERSION,
    )


@router.get("/grid", response_model=GridResponse)
def get_prediction_grid(
    bbox: str = Query(..., description="west,south,east,north"),
    date: date = Query(..., description="ISO date for predictions"),
    _settings=Depends(require_db),
) -> GridResponse:
    raise NotImplementedError("Prediction grid not implemented yet.")
