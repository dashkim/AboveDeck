"""Tests for rule-based forecast helpers."""

from datetime import date

from services.cloud_base import estimate_cloud_base_m
from services.scoring import above_cloud_probability, inversion_strength_from_prob
from services.weather_forecast import _forecast_days_for


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
