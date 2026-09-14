"""Cloud base estimation from METAR and weather variables."""

from __future__ import annotations

_SUMMIT_ELEV_TOLERANCE_M = 25.0
_DEFAULT_VALLEY_DROP_M = 600.0


def lifting_condensation_level_m(temp_c: float, dewpoint_c: float, elevation_m: float = 0.0) -> float:
    """Estimate LCL height above ground (m), then return AMSL."""
    spread = max(temp_c - dewpoint_c, 0.1)
    lcl_agl_m = 125.0 * spread
    return elevation_m + lcl_agl_m


def surface_elevation_for_lcl(
    peak_elevation_m: float,
    *,
    forecast_elevation_m: float | None = None,
    prominence_m: float | None = None,
    summit_tolerance_m: float = _SUMMIT_ELEV_TOLERANCE_M,
    default_drop_m: float = _DEFAULT_VALLEY_DROP_M,
) -> float:
    """Pick the ground elevation for LCL — never the summit itself.

    Temp/dewpoint apply at the model/station surface. Anchoring LCL at the peak
    made cloud_base = peak + LCL_AGL and capped probabilities near 48%.
    """
    peak = float(peak_elevation_m)

    if forecast_elevation_m is not None and float(forecast_elevation_m) < peak - summit_tolerance_m:
        return max(0.0, float(forecast_elevation_m))

    if prominence_m is not None and prominence_m > 0:
        valley = peak - float(prominence_m)
        if valley < peak - summit_tolerance_m:
            return max(0.0, valley)

    return max(0.0, peak - default_drop_m)


def estimate_cloud_base_m(
    *,
    temp_c: float | None,
    dewpoint_c: float | None,
    elevation_m: float,
    observed_ceiling_m: float | None = None,
    cloud_cover_low: float | None = None,
) -> float | None:
    """Prefer observed ceiling; fall back to LCL at surface elevation."""
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
