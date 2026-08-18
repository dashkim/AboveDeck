"""Query helpers for peak predictions."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.predictions import Prediction
from schemas.peaks import HourlyPrediction, PeakSummary


async def _latest_model_version(
    session: AsyncSession,
    peak_ids: list[int],
    day_start: datetime,
    day_end: datetime,
) -> str | None:
    stmt = (
        select(Prediction.model_version)
        .where(
            Prediction.peak_id.in_(peak_ids),
            Prediction.valid_at >= day_start,
            Prediction.valid_at <= day_end,
        )
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def fetch_peak_predictions_for_date(
    session: AsyncSession,
    peak_ids: list[int],
    target_date: date,
    hour: int | None = None,
) -> dict[int, Prediction]:
    if not peak_ids:
        return {}

    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    model_version = await _latest_model_version(session, peak_ids, day_start, day_end)
    if model_version is None:
        return {}

    base_filters = [
        Prediction.peak_id.in_(peak_ids),
        Prediction.model_version == model_version,
        Prediction.valid_at >= day_start,
        Prediction.valid_at <= day_end,
    ]

    if hour is not None:
        target_valid = datetime.combine(target_date, time(hour=hour), tzinfo=timezone.utc)
        stmt = select(Prediction).where(*base_filters, Prediction.valid_at == target_valid)
        result = await session.execute(stmt)
        return {row.peak_id: row for row in result.scalars().all()}

    stmt = (
        select(Prediction)
        .where(*base_filters)
        .distinct(Prediction.peak_id)
        .order_by(Prediction.peak_id, Prediction.above_cloud_prob.desc())
    )
    result = await session.execute(stmt)
    return {row.peak_id: row for row in result.scalars().all()}


async def fetch_hourly_predictions(
    session: AsyncSession,
    peak_id: int,
    target_date: date,
) -> list[HourlyPrediction]:
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    model_version = await _latest_model_version(session, [peak_id], day_start, day_end)
    if model_version is None:
        return []

    stmt = (
        select(Prediction)
        .where(
            Prediction.peak_id == peak_id,
            Prediction.model_version == model_version,
            Prediction.valid_at >= day_start,
            Prediction.valid_at <= day_end,
        )
        .order_by(Prediction.valid_at)
    )
    result = await session.execute(stmt)
    return [
        HourlyPrediction(
            valid_at=row.valid_at,
            above_cloud_prob=row.above_cloud_prob,
            inversion_strength=row.inversion_strength,  # type: ignore[arg-type]
            estimated_cloud_base_m=row.estimated_cloud_base_m,
            confidence=row.confidence,  # type: ignore[arg-type]
        )
        for row in result.scalars().all()
    ]


def prediction_to_summary(
    peak_id: int,
    name: str,
    lat: float,
    lon: float,
    elevation_m: int | None,
    state: str,
    prediction: Prediction | None,
) -> PeakSummary:
    if prediction is None:
        return PeakSummary(
            id=peak_id,
            name=name,
            lat=lat,
            lon=lon,
            elevation_m=elevation_m or 0,
            prominence_m=None,
            state=state,
            above_cloud_prob=0.0,
            inversion_strength="none",
            confidence="low",
            best_window_start=None,
            best_window_end=None,
        )
    return PeakSummary(
        id=peak_id,
        name=name,
        lat=lat,
        lon=lon,
        elevation_m=elevation_m or 0,
        prominence_m=None,
        state=state,
        above_cloud_prob=prediction.above_cloud_prob,
        inversion_strength=prediction.inversion_strength,  # type: ignore[arg-type]
        confidence=prediction.confidence,  # type: ignore[arg-type]
        best_window_start=None,
        best_window_end=None,
    )
