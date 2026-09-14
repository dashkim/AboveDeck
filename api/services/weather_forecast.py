"""Fetch Open-Meteo forecasts and write rule-based peak predictions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Sequence

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.predictions import Prediction
from services.cloud_base import estimate_cloud_base_m, surface_elevation_for_lcl
from services.scoring import (
    above_cloud_probability,
    confidence_from_lead_hours,
    inversion_strength_from_prob,
)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARIABLES = (
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
)
# rules-v1: LCL anchored at forecast/valley surface elevation, not the summit.
MODEL_VERSION = "rules-v1"
API_BATCH_SIZE = 20
DEFAULT_REFRESH_CAP = 80
_FETCH_MAX_ATTEMPTS = 5
_FETCH_RETRY_BASE_SECONDS = 1.5
_BATCH_PAUSE_SECONDS = 0.75


@dataclass(frozen=True)
class PeakLocation:
    id: int
    lat: float
    lon: float
    elevation_m: float
    prominence_m: float | None = None


def _forecast_days_for(target_date: date, today: date | None = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    ahead = (target_date - today).days
    if ahead < 0:
        return 1
    return max(1, min(7, ahead + 1))


def _parse_hourly_payload(
    payload: dict[str, Any],
    *,
    fetched_at: datetime,
    target_date: date,
) -> list[dict[str, Any]]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    forecast_elevation_m = payload.get("elevation")
    if forecast_elevation_m is not None:
        forecast_elevation_m = float(forecast_elevation_m)
    rows: list[dict[str, Any]] = []
    for idx, time_str in enumerate(times):
        valid_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if valid_at.tzinfo is None:
            valid_at = valid_at.replace(tzinfo=timezone.utc)
        if valid_at.date() != target_date:
            continue
        lead_hours = (valid_at - fetched_at).total_seconds() / 3600.0
        rows.append(
            {
                "valid_at": valid_at,
                "lead_hours": lead_hours if lead_hours >= 0 else None,
                "temp_c": _at(hourly, "temperature_2m", idx),
                "dewpoint_c": _at(hourly, "dewpoint_2m", idx),
                "rh": _at(hourly, "relative_humidity_2m", idx),
                "cloud_cover_low": _at(hourly, "cloud_cover_low", idx),
                "forecast_elevation_m": forecast_elevation_m,
            }
        )
    return rows


def _at(hourly: dict[str, Any], key: str, idx: int) -> float | None:
    values = hourly.get(key) or []
    if idx >= len(values):
        return None
    value = values[idx]
    return float(value) if value is not None else None


async def _fetch_batch(
    client: httpx.AsyncClient,
    peaks: Sequence[PeakLocation],
    *,
    forecast_days: int,
    fetched_at: datetime,
    target_date: date,
) -> list[list[dict[str, Any]]]:
    params = {
        "latitude": ",".join(str(p.lat) for p in peaks),
        "longitude": ",".join(str(p.lon) for p in peaks),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
        "models": "best_match",
        "forecast_days": forecast_days,
    }
    last_error: Exception | None = None
    for attempt in range(_FETCH_MAX_ATTEMPTS):
        try:
            response = await client.get(OPEN_METEO_URL, params=params, timeout=60.0)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else (
                    _FETCH_RETRY_BASE_SECONDS * (2**attempt)
                )
                await asyncio.sleep(delay)
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                return [
                    _parse_hourly_payload(item, fetched_at=fetched_at, target_date=target_date)
                    for item in payload
                ]
            return [_parse_hourly_payload(payload, fetched_at=fetched_at, target_date=target_date)]
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response is not None and exc.response.status_code == 429:
                await asyncio.sleep(_FETCH_RETRY_BASE_SECONDS * (2**attempt))
                continue
            raise
        except httpx.TransportError as exc:
            last_error = exc
            await asyncio.sleep(_FETCH_RETRY_BASE_SECONDS * (2**attempt))
    if last_error is not None:
        raise last_error
    raise httpx.HTTPError("Open-Meteo rate limited after retries")


def _score_hour(peak: PeakLocation, hour: dict[str, Any]) -> dict[str, Any]:
    surface_m = surface_elevation_for_lcl(
        peak.elevation_m,
        forecast_elevation_m=hour.get("forecast_elevation_m"),
        prominence_m=peak.prominence_m,
    )
    cloud_base_m = estimate_cloud_base_m(
        temp_c=hour["temp_c"],
        dewpoint_c=hour["dewpoint_c"],
        elevation_m=surface_m,
        cloud_cover_low=hour["cloud_cover_low"],
    )
    prob = (
        above_cloud_probability(peak.elevation_m, cloud_base_m)
        if cloud_base_m is not None
        else 0.0
    )
    return {
        "peak_id": peak.id,
        "valid_at": hour["valid_at"],
        "lead_hours": hour["lead_hours"],
        "above_cloud_prob": prob,
        "inversion_strength": inversion_strength_from_prob(prob),
        "estimated_cloud_base_m": cloud_base_m,
        "confidence": confidence_from_lead_hours(hour["lead_hours"], cloud_base_m),
        "model_version": MODEL_VERSION,
    }


async def upsert_prediction_rows(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(Prediction).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["peak_id", "valid_at", "model_version"],
        set_={
            "lead_hours": stmt.excluded.lead_hours,
            "above_cloud_prob": stmt.excluded.above_cloud_prob,
            "inversion_strength": stmt.excluded.inversion_strength,
            "estimated_cloud_base_m": stmt.excluded.estimated_cloud_base_m,
            "confidence": stmt.excluded.confidence,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def refresh_peak_forecasts(
    session: AsyncSession,
    peaks: Sequence[PeakLocation],
    target_date: date,
    *,
    max_peaks: int = DEFAULT_REFRESH_CAP,
) -> int:
    """Pull Open-Meteo for peaks and upsert rules-v1 predictions for target_date."""
    if not peaks:
        return 0

    ordered = sorted(peaks, key=lambda p: p.elevation_m, reverse=True)[:max_peaks]
    fetched_at = datetime.now(timezone.utc)
    forecast_days = _forecast_days_for(target_date, fetched_at.date())
    scored: list[dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        for start in range(0, len(ordered), API_BATCH_SIZE):
            if start > 0:
                await asyncio.sleep(_BATCH_PAUSE_SECONDS)
            batch = ordered[start : start + API_BATCH_SIZE]
            hour_groups = await _fetch_batch(
                client,
                batch,
                forecast_days=forecast_days,
                fetched_at=fetched_at,
                target_date=target_date,
            )
            for peak, hours in zip(batch, hour_groups):
                scored.extend(_score_hour(peak, hour) for hour in hours)

    return await upsert_prediction_rows(session, scored)


def day_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    return start, end
