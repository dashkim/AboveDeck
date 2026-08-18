"""Probability helpers for inversion scoring."""

from __future__ import annotations

import math


def above_cloud_probability(
    elevation_m: float,
    cloud_base_m: float,
    *,
    uncertainty_m: float = 150.0,
) -> float:
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
