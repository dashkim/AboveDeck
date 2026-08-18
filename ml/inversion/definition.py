"""Versioned inversion definition engine."""

from __future__ import annotations

from dataclasses import dataclass

from ml.config import DEFINITION_VERSION
from ml.inversion.cloud_base import estimate_cloud_base_m
from ml.inversion.scoring import above_cloud_probability, inversion_strength_from_prob


@dataclass
class InversionAssessment:
    inversion_present: bool
    above_cloud: bool
    cloud_base_m: float | None
    margin_m: float | None
    stability_index: float
    strength: str
    confidence: str
    above_cloud_prob: float
    definition_version: str = DEFINITION_VERSION


def assess_inversion(
    *,
    elevation_m: float,
    temp_c: float | None = None,
    dewpoint_c: float | None = None,
    valley_temp_c: float | None = None,
    rh: float | None = None,
    wind_ms: float | None = None,
    cloud_cover_low: float | None = None,
    observed_ceiling_m: float | None = None,
    lead_hours: float | None = None,
    has_observation: bool = False,
) -> InversionAssessment:
    cloud_base_m = estimate_cloud_base_m(
        temp_c=temp_c,
        dewpoint_c=dewpoint_c,
        elevation_m=elevation_m,
        observed_ceiling_m=observed_ceiling_m,
        cloud_cover_low=cloud_cover_low,
    )

    margin_m = (elevation_m - cloud_base_m) if cloud_base_m is not None else None
    above_cloud_prob = (
        above_cloud_probability(elevation_m, cloud_base_m) if cloud_base_m is not None else 0.0
    )
    strength = inversion_strength_from_prob(above_cloud_prob)

    deck_below = margin_m is not None and margin_m >= 100.0
    stable_layer = _stable_layer(valley_temp_c, temp_c, rh, cloud_cover_low)
    low_wind = wind_ms is None or wind_ms <= 8.0
    inversion_present = deck_below and stable_layer and low_wind
    above_cloud = deck_below and above_cloud_prob >= 0.35

    stability_index = _stability_index(valley_temp_c, temp_c, rh, cloud_cover_low, wind_ms)
    confidence = _confidence(lead_hours, has_observation, cloud_base_m)

    return InversionAssessment(
        inversion_present=inversion_present,
        above_cloud=above_cloud,
        cloud_base_m=cloud_base_m,
        margin_m=margin_m,
        stability_index=stability_index,
        strength=strength,
        confidence=confidence,
        above_cloud_prob=above_cloud_prob,
    )


def _stable_layer(
    valley_temp_c: float | None,
    ridge_temp_c: float | None,
    rh: float | None,
    cloud_cover_low: float | None,
) -> bool:
    if valley_temp_c is not None and ridge_temp_c is not None:
        if valley_temp_c <= ridge_temp_c + 1.0:
            return True
    if rh is not None and rh >= 85:
        return True
    if cloud_cover_low is not None and cloud_cover_low >= 50:
        return True
    return False


def _stability_index(
    valley_temp_c: float | None,
    ridge_temp_c: float | None,
    rh: float | None,
    cloud_cover_low: float | None,
    wind_ms: float | None,
) -> float:
    score = 0.0
    if valley_temp_c is not None and ridge_temp_c is not None and valley_temp_c <= ridge_temp_c:
        score += 0.35
    if rh is not None:
        score += min(rh / 100.0, 1.0) * 0.25
    if cloud_cover_low is not None:
        score += min(cloud_cover_low / 100.0, 1.0) * 0.25
    if wind_ms is not None:
        score += max(0.0, 1.0 - wind_ms / 12.0) * 0.15
    return min(score, 1.0)


def _confidence(
    lead_hours: float | None,
    has_observation: bool,
    cloud_base_m: float | None,
) -> str:
    if cloud_base_m is None:
        return "low"
    if has_observation:
        return "high" if (lead_hours is None or lead_hours <= 24) else "medium"
    if lead_hours is None:
        return "medium"
    if lead_hours <= 24:
        return "medium"
    if lead_hours <= 48:
        return "low"
    return "low"
