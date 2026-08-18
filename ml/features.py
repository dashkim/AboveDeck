"""Shared feature builder for training and inference."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ml.inversion.cloud_base import dewpoint_depression, estimate_cloud_base_m
from ml.inversion.definition import assess_inversion


def build_features(
    *,
    peak_id: int,
    lat: float,
    lon: float,
    elevation_m: float,
    prominence_m: float | None,
    valid_at: datetime,
    temp_c: float | None = None,
    dewpoint_c: float | None = None,
    rh: float | None = None,
    wind_ms: float | None = None,
    wind_dir: float | None = None,
    cloud_cover: float | None = None,
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    pressure_hpa: float | None = None,
    valley_temp_c: float | None = None,
    lead_hours: float | None = None,
    observed_ceiling_m: float | None = None,
    has_observation: bool = False,
) -> dict[str, Any]:
    if valid_at.tzinfo is None:
        valid_at = valid_at.replace(tzinfo=timezone.utc)

    cloud_base_m = estimate_cloud_base_m(
        temp_c=temp_c,
        dewpoint_c=dewpoint_c,
        elevation_m=elevation_m,
        observed_ceiling_m=observed_ceiling_m,
        cloud_cover_low=cloud_cover_low,
    )
    assessment = assess_inversion(
        elevation_m=elevation_m,
        temp_c=temp_c,
        dewpoint_c=dewpoint_c,
        valley_temp_c=valley_temp_c,
        rh=rh,
        wind_ms=wind_ms,
        cloud_cover_low=cloud_cover_low,
        observed_ceiling_m=observed_ceiling_m,
        lead_hours=lead_hours,
        has_observation=has_observation,
    )

    valley_delta = None
    if valley_temp_c is not None and temp_c is not None:
        valley_delta = temp_c - valley_temp_c

    return {
        "peak_id": peak_id,
        "lat": lat,
        "lon": lon,
        "valid_at": valid_at.isoformat(),
        "temp_c": temp_c,
        "dewpoint_c": dewpoint_c,
        "rh": rh,
        "wind_ms": wind_ms,
        "wind_dir": wind_dir,
        "cloud_cover": cloud_cover,
        "cloud_cover_low": cloud_cover_low,
        "cloud_cover_mid": cloud_cover_mid,
        "pressure_hpa": pressure_hpa,
        "elevation_m": elevation_m,
        "prominence_m": prominence_m,
        "hour_utc": valid_at.hour,
        "day_of_year": valid_at.timetuple().tm_yday,
        "lead_hours": lead_hours,
        "dewpoint_depression": dewpoint_depression(temp_c, dewpoint_c),
        "valley_temp_delta": valley_delta,
        "estimated_cloud_base_m": cloud_base_m,
        "margin_m": assessment.margin_m,
        "stability_index": assessment.stability_index,
        "above_cloud_prob_rules": assessment.above_cloud_prob,
        "strength_rules": assessment.strength,
        "confidence_rules": assessment.confidence,
        "above_cloud_label": int(assessment.above_cloud),
    }


FEATURE_COLUMNS = [
    "temp_c",
    "dewpoint_c",
    "rh",
    "wind_ms",
    "wind_dir",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "pressure_hpa",
    "elevation_m",
    "prominence_m",
    "hour_utc",
    "day_of_year",
    "lead_hours",
    "dewpoint_depression",
    "valley_temp_delta",
    "estimated_cloud_base_m",
    "margin_m",
    "stability_index",
    "lat",
    "lon",
]
