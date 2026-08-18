"""IEM ASOS/METAR observation client."""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from ml.config import PNW_METAR_STATIONS, get_settings

FEET_TO_METERS = 0.3048
KNOTS_TO_MS = 0.514444


@dataclass
class MetarObservation:
    station_id: str
    observed_at: datetime
    temp_c: float | None
    dewpoint_c: float | None
    rh: float | None
    wind_ms: float | None
    wind_dir: float | None
    visibility_m: float | None
    cloud_base_m: float | None
    cloud_cover_code: str | None
    raw_metar: str | None = None


class IemMetarClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.settings = get_settings()

    def fetch_observations(
        self,
        station_ids: list[str],
        start: datetime,
        end: datetime,
    ) -> list[MetarObservation]:
        params = {
            "station": ",".join(station_ids),
            "data": "tmpf,dwpf,relh,drct,sknt,vsby,skyc1,skyl1,metar",
            "tz": "UTC",
            "format": "onlycomma",
            "latlon": "no",
            "elev": "no",
            "missing": "M",
            "trace": "T",
            "direct": "no",
            "report_type": "3,4",
            "year1": start.year,
            "month1": start.month,
            "day1": start.day,
            "year2": end.year,
            "month2": end.month,
            "day2": end.day,
        }
        response = self.session.get(self.settings.iem_asos_url, params=params, timeout=120)
        response.raise_for_status()
        return self._parse_csv(response.text)

    def _parse_csv(self, text: str) -> list[MetarObservation]:
        reader = csv.DictReader(io.StringIO(text))
        observations: list[MetarObservation] = []
        for row in reader:
            station = (row.get("station") or "").strip()
            valid_raw = (row.get("valid") or row.get("valid(UTC)") or "").strip()
            if not station or not valid_raw:
                continue
            observed_at = datetime.strptime(valid_raw, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            observations.append(
                MetarObservation(
                    station_id=normalize_station_id(station),
                    observed_at=observed_at,
                    temp_c=_fahrenheit_to_celsius(_parse_float(row.get("tmpf"))),
                    dewpoint_c=_fahrenheit_to_celsius(_parse_float(row.get("dwpf"))),
                    rh=_parse_float(row.get("relh")),
                    wind_ms=_knots_to_ms(_parse_float(row.get("sknt"))),
                    wind_dir=_parse_float(row.get("drct")),
                    visibility_m=_miles_to_meters(_parse_float(row.get("vsby"))),
                    cloud_base_m=_feet_to_meters(_parse_float(row.get("skyl1"))),
                    cloud_cover_code=(row.get("skyc1") or "").strip() or None,
                    raw_metar=(row.get("metar") or "").strip() or None,
                )
            )
        return observations

    @staticmethod
    def nearest_station(lat: float, lon: float) -> tuple[str, float]:
        best_id = ""
        best_dist = float("inf")
        for station_id, (slat, slon) in PNW_METAR_STATIONS.items():
            dist = _haversine_km(lat, lon, slat, slon)
            if dist < best_dist:
                best_dist = dist
                best_id = station_id
        return best_id, best_dist


def normalize_station_id(station_id: str) -> str:
    station_id = station_id.strip().upper()
    if len(station_id) == 3 and not station_id.startswith("K"):
        return f"K{station_id}"
    return station_id


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"M", "T", "NA"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _fahrenheit_to_celsius(value: float | None) -> float | None:
    if value is None:
        return None
    return (value - 32.0) * 5.0 / 9.0


def _knots_to_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return value * KNOTS_TO_MS


def _feet_to_meters(value: float | None) -> float | None:
    if value is None:
        return None
    return value * FEET_TO_METERS


def _miles_to_meters(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 1609.344


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
