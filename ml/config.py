"""Shared configuration for ML pipeline scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


HOURLY_VARIABLES = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
]

PNW_METAR_STATIONS: dict[str, tuple[float, float]] = {
    "KPDX": (45.58872, -122.59750),
    "KSEA": (47.44989, -122.31178),
    "KBFI": (47.53000, -122.30194),
    "KEUG": (44.12458, -123.21197),
    "KMFR": (42.37423, -122.87350),
    "KRDM": (44.25407, -121.14964),
    "KBOI": (43.56444, -116.22278),
    "KGEG": (47.61986, -117.53364),
    "KPSC": (46.26468, -119.11903),
    "KYKM": (46.56817, -120.54406),
    "KOLM": (46.96972, -122.90278),
    "KUIL": (47.23861, -124.00694),
    "KBLI": (48.79275, -122.53753),
    "KMWH": (47.20771, -119.32019),
    "KALW": (46.09389, -118.28583),
}

DEFINITION_VERSION = "inv-def-v1"
DEFAULT_MODEL_VERSION = "rules-v0"
ML_MODEL_VERSION = "inv-clf-v1"


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_historical_url: str = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    open_meteo_single_run_url: str = "https://single-runs-api.open-meteo.com/v1/forecast"
    iem_asos_url: str = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    models_dir: str = field(
        default_factory=lambda: os.path.join(os.path.dirname(__file__), "models", "artifacts")
    )

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)

    def sync_database_url(self) -> str:
        return normalize_psycopg2_url(self.database_url)


def normalize_psycopg2_url(url: str) -> str:
    """Normalize DATABASE_URL for psycopg2 (Neon uses ssl=require)."""
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql://" + url.split("://", 1)[1]
            break
    # Neon and some providers use ?ssl=require; psycopg2 expects sslmode=require
    url = url.replace("ssl=require", "sslmode=require")
    url = url.replace("?sslmode=require&", "?sslmode=require&")
    if url.endswith("?ssl"):
        url = url[:-4] + "?sslmode=require"
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
