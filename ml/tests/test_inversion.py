"""Tests for inversion definition."""

from ml.inversion.cloud_base import estimate_cloud_base_m, lifting_condensation_level_m
from ml.inversion.definition import assess_inversion
from ml.inversion.scoring import above_cloud_probability, inversion_strength_from_prob


def test_lcl_increases_with_spread():
    low = lifting_condensation_level_m(10.0, 9.0, elevation_m=1000.0)
    high = lifting_condensation_level_m(10.0, 0.0, elevation_m=1000.0)
    assert high > low


def test_above_cloud_probability_sigmoid():
    assert above_cloud_probability(2000, 1500) > 0.9
    assert above_cloud_probability(1500, 2000) < 0.1


def test_inversion_strength_buckets():
    assert inversion_strength_from_prob(0.9) == "excellent"
    assert inversion_strength_from_prob(0.7) == "strong"
    assert inversion_strength_from_prob(0.4) == "possible"
    assert inversion_strength_from_prob(0.1) == "none"


def test_assess_inversion_with_observed_ceiling():
    result = assess_inversion(
        elevation_m=2000.0,
        temp_c=5.0,
        dewpoint_c=4.0,
        valley_temp_c=2.0,
        rh=90.0,
        wind_ms=2.0,
        cloud_cover_low=80.0,
        observed_ceiling_m=1200.0,
        has_observation=True,
    )
    assert result.above_cloud is True
    assert result.inversion_present is True
    assert result.margin_m == 800.0


def test_estimate_cloud_base_prefers_observation():
    obs = estimate_cloud_base_m(
        temp_c=10.0,
        dewpoint_c=8.0,
        elevation_m=1500.0,
        observed_ceiling_m=900.0,
    )
    assert obs == 900.0
