"""Cloud base estimation from METAR and weather variables."""

from __future__ import annotations

import math


def lifting_condensation_level_m(temp_c: float, dewpoint_c: float, elevation_m: float = 0.0) -> float:
    """Estimate LCL height above ground (m), then return AMSL."""
    spread = max(temp_c - dewpoint_c, 0.1)
    lcl_agl_m = 125.0 * spread
    return elevation_m + lcl_agl_m


def estimate_cloud_base_m(
    *,
    temp_c: float | None,
    dewpoint_c: float | None,
    elevation_m: float,
    observed_ceiling_m: float | None = None,
    cloud_cover_low: float | None = None,
) -> float | None:
    """Prefer observed ceiling; fall back to LCL when low clouds likely."""
    if observed_ceiling_m is not None and observed_ceiling_m > 0:
        return observed_ceiling_m
    if temp_c is None or dewpoint_c is None:
        return None
    if cloud_cover_low is not None and cloud_cover_low < 20:
        return None
    return lifting_condensation_level_m(temp_c, dewpoint_c, elevation_m)


def dewpoint_depression(temp_c: float | None, dewpoint_c: float | None) -> float | None:
    if temp_c is None or dewpoint_c is None:
        return None
    return temp_c - dewpoint_c
