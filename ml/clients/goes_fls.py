"""GOES-18 Fog/Low Stratus label helpers (phase 1b)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GoesFlsSample:
    lat: float
    lon: float
    observed_at: datetime
    low_cloud_present: bool | None
    visibility_prob: float | None
    source: str = "goes18_fls"


class GoesFlsClient:
    """Minimal GOES-18 FLS client.

    Full NetCDF ingest from s3://noaa-goes18/ requires xarray/netCDF4 and is
    intentionally deferred. This client provides the interface and a no-op fetch
    so label.py can call it when AWS dependencies are added later.
    """

    BUCKET = "noaa-goes18"
    PRODUCT_PREFIX = "ABI-L2-FLF"

    def sample_point(
        self,
        lat: float,
        lon: float,
        observed_at: datetime,
    ) -> GoesFlsSample | None:
        _ = (lat, lon, observed_at)
        return None

    @staticmethod
    def observation_to_label(sample: GoesFlsSample, elevation_m: float) -> bool | None:
        if sample.low_cloud_present is None:
            return None
        if sample.low_cloud_present and elevation_m > 500:
            return True
        if not sample.low_cloud_present:
            return False
        return None
