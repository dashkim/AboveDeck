"""Derive above-cloud probability from peak elevation vs estimated cloud base."""

from __future__ import annotations

import math


def above_cloud_probability(
    elevation_m: float,
    cloud_base_m: float,
    *,
    uncertainty_m: float = 150.0,
) -> float:
    """Sigmoid over elevation margin above cloud base (meters)."""
    margin = elevation_m - cloud_base_m
    return 1.0 / (1.0 + math.exp(-margin / max(uncertainty_m, 1.0)))


def inversion_strength_from_prob(prob: float) -> str:
    if prob >= 0.85:
        return "excellent"
    if prob >= 0.65:
        return "strong"
    if prob >= 0.35:
        return "possible"
    return "none"


def confidence_from_lead_hours(lead_hours: float | None, cloud_base_m: float | None) -> str:
    if cloud_base_m is None:
        return "low"
    if lead_hours is None:
        return "medium"
    if lead_hours <= 24:
        return "medium"
    if lead_hours <= 48:
        return "low"
    return "low"
