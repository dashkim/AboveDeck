"""Tests for rule-based forecast helpers."""

from datetime import date, datetime, timezone

from services.cloud_base import estimate_cloud_base_m, surface_elevation_for_lcl
from services.scoring import above_cloud_probability, inversion_strength_from_prob
from services.weather_forecast import PeakLocation, _forecast_days_for, _score_hour


def test_forecast_days_covers_target_date():
    today = date(2026, 9, 13)
    assert _forecast_days_for(date(2026, 9, 13), today) == 1
    assert _forecast_days_for(date(2026, 9, 15), today) == 3
    assert _forecast_days_for(date(2026, 9, 20), today) == 7


def test_cloud_base_none_when_clear():
    assert (
        estimate_cloud_base_m(
            temp_c=10.0,
            dewpoint_c=2.0,
            elevation_m=1500,
            cloud_cover_low=5,
        )
        is None
    )


def test_high_peak_above_low_deck():
    base = estimate_cloud_base_m(
        temp_c=5.0,
        dewpoint_c=4.0,
        elevation_m=1000,
        cloud_cover_low=80,
    )
    assert base is not None
    prob = above_cloud_probability(3000, base)
    assert prob > 0.8
    assert inversion_strength_from_prob(prob) in {"strong", "excellent"}


def test_surface_elevation_prefers_forecast_grid_below_peak():
    surface = surface_elevation_for_lcl(3000, forecast_elevation_m=1200)
    assert surface == 1200


def test_surface_elevation_uses_near_summit_forecast_grid():
    # Mt Hood-like: model DEM only ~100 m below summit — still use it.
    surface = surface_elevation_for_lcl(3424, forecast_elevation_m=3319)
    assert surface == 3319


def test_surface_elevation_falls_back_when_forecast_at_summit():
    surface = surface_elevation_for_lcl(
        3000,
        forecast_elevation_m=3000,
        prominence_m=800,
    )
    assert surface == 2200


def test_surface_elevation_default_valley_drop():
    surface = surface_elevation_for_lcl(2000, forecast_elevation_m=2000)
    assert surface == 1400


def test_score_hour_not_capped_near_half_when_peak_above_deck():
    """Regression: summit-anchored LCL used to cap every humid peak at ~48%."""
    peak = PeakLocation(id=1, lat=46.85, lon=-121.76, elevation_m=3000, prominence_m=900)
    hour = {
        "valid_at": datetime(2026, 9, 14, 14, tzinfo=timezone.utc),
        "lead_hours": 6.0,
        "temp_c": 5.0,
        "dewpoint_c": 4.0,
        "rh": 90.0,
        "cloud_cover_low": 80.0,
        "forecast_elevation_m": 1100.0,
    }
    scored = _score_hour(peak, hour)
    assert scored["above_cloud_prob"] > 0.85
    assert scored["inversion_strength"] in {"strong", "excellent"}
    assert scored["model_version"] == "rules-v1"


def test_score_hour_uses_prominence_when_forecast_elev_missing():
    peak = PeakLocation(id=2, lat=46.0, lon=-121.0, elevation_m=2500, prominence_m=700)
    hour = {
        "valid_at": datetime(2026, 9, 14, 8, tzinfo=timezone.utc),
        "lead_hours": 2.0,
        "temp_c": 6.0,
        "dewpoint_c": 5.5,
        "rh": 95.0,
        "cloud_cover_low": 70.0,
        "forecast_elevation_m": None,
    }
    scored = _score_hour(peak, hour)
    # Valley at 1800, LCL ~62.5 AGL → base ~1862; peak 2500 → high prob
    assert scored["above_cloud_prob"] > 0.85
