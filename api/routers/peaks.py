from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import functions as gf
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from dependencies import require_db
from models.peaks import Peak
from schemas.peaks import (
    PeakDetail,
    PeakListResponse,
    PeakSearchResponse,
    PeakSearchResult,
)
from services.predictions import (
    fetch_hourly_predictions,
    fetch_peak_predictions_for_date,
    prediction_to_summary,
)
from services.weather_forecast import PeakLocation, refresh_peak_forecasts

router = APIRouter(prefix="/peaks", tags=["peaks"])


def _needs_forecast_refresh(predictions: dict) -> bool:
    if not predictions:
        return True
    return all(
        pred.model_version != "rules-v0" and (pred.above_cloud_prob or 0) == 0.0
        for pred in predictions.values()
    )


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = [float(value.strip()) for value in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=422, detail="bbox must be west,south,east,north")
    west, south, east, north = parts
    if west >= east or south >= north:
        raise HTTPException(status_code=422, detail="bbox bounds are invalid")
    return west, south, east, north


@router.get("", response_model=PeakListResponse)
async def list_peaks(
    bbox: str = Query(..., description="west,south,east,north"),
    date: date = Query(..., description="ISO date for predictions"),
    hour: int | None = Query(None, ge=0, le=23, description="Optional hour (0-23)"),
    _settings=Depends(require_db),
    session: AsyncSession = Depends(get_session),
) -> PeakListResponse:
    west, south, east, north = parse_bbox(bbox)
    envelope = gf.ST_MakeEnvelope(west, south, east, north, 4326)
    stmt = (
        select(
            Peak.id,
            Peak.name,
            func.ST_Y(Peak.geom).label("lat"),
            func.ST_X(Peak.geom).label("lon"),
            Peak.elevation_m,
            Peak.state,
        )
        .where(Peak.geom.ST_Intersects(envelope))
        .order_by(Peak.elevation_m.desc().nulls_last(), Peak.name)
        .limit(200)
    )
    result = await session.execute(stmt)
    rows = result.all()
    peak_ids = [row.id for row in rows]
    predictions = await fetch_peak_predictions_for_date(session, peak_ids, date, hour=hour)

    if rows and _needs_forecast_refresh(predictions):
        locations = [
            PeakLocation(
                id=row.id,
                lat=float(row.lat),
                lon=float(row.lon),
                elevation_m=float(row.elevation_m or 0),
            )
            for row in rows
            if row.elevation_m is not None
        ]
        try:
            await refresh_peak_forecasts(session, locations, date)
            predictions = await fetch_peak_predictions_for_date(
                session, peak_ids, date, hour=hour
            )
        except Exception:
            # Serve peaks without live scores if Open-Meteo is unavailable.
            pass

    peaks = [
        prediction_to_summary(
            row.id,
            row.name,
            row.lat,
            row.lon,
            row.elevation_m,
            row.state,
            predictions.get(row.id),
        )
        for row in rows
    ]
    peaks.sort(key=lambda p: p.above_cloud_prob, reverse=True)
    return PeakListResponse(peaks=peaks, date=date, bbox=(west, south, east, north))


@router.get("/search", response_model=PeakSearchResponse)
async def search_peaks(
    q: str = Query(..., min_length=1, description="Peak name search query"),
    _settings=Depends(require_db),
    session: AsyncSession = Depends(get_session),
) -> PeakSearchResponse:
    stmt = (
        select(
            Peak.id,
            Peak.name,
            func.ST_Y(Peak.geom).label("lat"),
            func.ST_X(Peak.geom).label("lon"),
            Peak.state,
            Peak.elevation_m,
        )
        .where(Peak.name.ilike(f"%{q}%"))
        .order_by(func.similarity(Peak.name, q).desc(), Peak.elevation_m.desc().nulls_last())
        .limit(20)
    )
    result = await session.execute(stmt)
    results = [
        PeakSearchResult(
            id=row.id,
            name=row.name,
            lat=float(row.lat),
            lon=float(row.lon),
            state=row.state,
            elevation_m=row.elevation_m or 0,
        )
        for row in result.all()
    ]
    return PeakSearchResponse(results=results, query=q)


@router.get("/{peak_id}", response_model=PeakDetail)
async def get_peak(
    peak_id: int,
    date: date = Query(..., description="ISO date for predictions"),
    _settings=Depends(require_db),
    session: AsyncSession = Depends(get_session),
) -> PeakDetail:
    stmt = select(
        Peak.id,
        Peak.name,
        func.ST_Y(Peak.geom).label("lat"),
        func.ST_X(Peak.geom).label("lon"),
        Peak.elevation_m,
        Peak.state,
    ).where(Peak.id == peak_id)
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Peak not found")

    predictions = await fetch_peak_predictions_for_date(session, [peak_id], date)
    if _needs_forecast_refresh(predictions) and row.elevation_m is not None:
        try:
            await refresh_peak_forecasts(
                session,
                [
                    PeakLocation(
                        id=row.id,
                        lat=float(row.lat),
                        lon=float(row.lon),
                        elevation_m=float(row.elevation_m),
                    )
                ],
                date,
            )
            predictions = await fetch_peak_predictions_for_date(session, [peak_id], date)
        except Exception:
            pass

    hourly = await fetch_hourly_predictions(session, peak_id, date)
    summary = prediction_to_summary(
        row.id,
        row.name,
        row.lat,
        row.lon,
        row.elevation_m,
        row.state,
        predictions.get(peak_id),
    )
    return PeakDetail(**summary.model_dump(), hourly=hourly)
