"""Cloud base estimation for rule-based forecasts."""

from __future__ import annotations

# When forecast terrain is nearly as high as the summit, drop at least this far
# so LCL is anchored below the peak (valley / free-atmosphere reference).
_MIN_SURFACE_DROP_M = 150.0
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
    min_drop_m: float = _MIN_SURFACE_DROP_M,
    default_drop_m: float = _DEFAULT_VALLEY_DROP_M,
) -> float:
    """Pick the ground elevation for LCL — never the summit itself.

    Temp/dewpoint from Open-Meteo apply at the model grid elevation. Using the
    peak elevation as that ground made cloud_base = peak + LCL_AGL, so margin
    was always negative and scores capped near 48%.
    """
    peak = float(peak_elevation_m)
    max_surface = peak - min_drop_m

    if forecast_elevation_m is not None and forecast_elevation_m <= max_surface:
        return max(0.0, float(forecast_elevation_m))

    if prominence_m is not None and prominence_m > 0:
        valley = peak - float(prominence_m)
        if valley <= max_surface:
            return max(0.0, valley)

    return max(0.0, peak - default_drop_m)


def estimate_cloud_base_m(
    *,
    temp_c: float | None,
    dewpoint_c: float | None,
    elevation_m: float,
    cloud_cover_low: float | None = None,
) -> float | None:
    """LCL AMSL from surface elevation (not summit); None when clear / missing temps."""
    if temp_c is None or dewpoint_c is None:
        return None
    if cloud_cover_low is not None and cloud_cover_low < 20:
        return None
    return lifting_condensation_level_m(temp_c, dewpoint_c, elevation_m)
