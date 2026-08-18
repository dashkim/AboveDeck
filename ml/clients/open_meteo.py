"""Open-Meteo forecast and archive client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import requests

from ml.config import HOURLY_VARIABLES, get_settings

EndpointKind = Literal["forecast", "historical", "single_run"]


@dataclass
class WeatherSnapshot:
    valid_at: datetime
    temp_c: float | None
    dewpoint_c: float | None
    rh: float | None
    wind_ms: float | None
    wind_dir: float | None
    cloud_cover: float | None
    cloud_cover_low: float | None
    cloud_cover_mid: float | None
    pressure_hpa: float | None
    source_model: str
    lead_hours: float | None = None
    raw: dict[str, Any] | None = None


class OpenMeteoClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.settings = get_settings()

    def _base_url(self, kind: EndpointKind) -> str:
        if kind == "forecast":
            return self.settings.open_meteo_forecast_url
        if kind == "historical":
            return self.settings.open_meteo_historical_url
        return self.settings.open_meteo_single_run_url

    def fetch_hourly(
        self,
        lat: float,
        lon: float,
        *,
        kind: EndpointKind = "forecast",
        start_date: str | None = None,
        end_date: str | None = None,
        forecast_days: int | None = 7,
        run: str | None = None,
        models: str = "best_match",
        fetched_at: datetime | None = None,
    ) -> list[WeatherSnapshot]:
        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
            "models": models,
        }
        if start_date and end_date:
            params["start_date"] = start_date
            params["end_date"] = end_date
        elif forecast_days is not None:
            params["forecast_days"] = forecast_days
        if run:
            params["run"] = run

        url = self._base_url(kind)
        response = self.session.get(url, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        return self._parse_hourly(payload, models=models, fetched_at=fetched_at)

    def _parse_hourly(
        self,
        payload: dict[str, Any],
        *,
        models: str,
        fetched_at: datetime | None,
    ) -> list[WeatherSnapshot]:
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            return []

        fetched = fetched_at or datetime.now(timezone.utc)
        snapshots: list[WeatherSnapshot] = []

        for idx, time_str in enumerate(times):
            valid_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            if valid_at.tzinfo is None:
                valid_at = valid_at.replace(tzinfo=timezone.utc)
            lead_hours = (valid_at - fetched).total_seconds() / 3600.0

            row_slice = {key: (values[idx] if idx < len(values) else None) for key, values in hourly.items() if key != "time"}
            snapshots.append(
                WeatherSnapshot(
                    valid_at=valid_at,
                    temp_c=hourly.get("temperature_2m", [None] * len(times))[idx],
                    dewpoint_c=hourly.get("dewpoint_2m", [None] * len(times))[idx],
                    rh=hourly.get("relative_humidity_2m", [None] * len(times))[idx],
                    wind_ms=hourly.get("wind_speed_10m", [None] * len(times))[idx],
                    wind_dir=hourly.get("wind_direction_10m", [None] * len(times))[idx],
                    cloud_cover=hourly.get("cloud_cover", [None] * len(times))[idx],
                    cloud_cover_low=hourly.get("cloud_cover_low", [None] * len(times))[idx],
                    cloud_cover_mid=hourly.get("cloud_cover_mid", [None] * len(times))[idx],
                    pressure_hpa=hourly.get("surface_pressure", [None] * len(times))[idx],
                    source_model=models,
                    lead_hours=lead_hours if lead_hours >= 0 else None,
                    raw={"time": time_str, **{k: v for k, v in row_slice.items()}},
                )
            )
        return snapshots

    def fetch_forecast_batch(
        self,
        locations: list[tuple[float, float]],
        *,
        forecast_days: int = 7,
        fetched_at: datetime | None = None,
        models: str = "best_match",
    ) -> list[list[WeatherSnapshot]]:
        if not locations:
            return []
        if len(locations) == 1:
            return [self.fetch_forecast(locations[0][0], locations[0][1], forecast_days=forecast_days)]

        fetched = fetched_at or datetime.now(timezone.utc)
        params: dict[str, Any] = {
            "latitude": ",".join(str(lat) for lat, _ in locations),
            "longitude": ",".join(str(lon) for _, lon in locations),
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
            "models": models,
            "forecast_days": forecast_days,
        }
        response = self.session.get(self._base_url("forecast"), params=params, timeout=120)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return [self._parse_hourly(item, models=models, fetched_at=fetched) for item in payload]
        return [self._parse_hourly(payload, models=models, fetched_at=fetched)]

    def fetch_forecast(self, lat: float, lon: float, *, forecast_days: int = 7) -> list[WeatherSnapshot]:
        fetched_at = datetime.now(timezone.utc)
        return self.fetch_hourly(
            lat,
            lon,
            kind="forecast",
            forecast_days=forecast_days,
            fetched_at=fetched_at,
        )

    def fetch_historical(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
    ) -> list[WeatherSnapshot]:
        return self.fetch_hourly(
            lat,
            lon,
            kind="historical",
            start_date=start_date,
            end_date=end_date,
            forecast_days=None,
            fetched_at=datetime.fromisoformat(f"{start_date}T00:00:00+00:00"),
        )

    def fetch_single_run(
        self,
        lat: float,
        lon: float,
        run: str,
        *,
        models: str = "best_match",
    ) -> list[WeatherSnapshot]:
        run_dt = datetime.fromisoformat(run.replace("Z", "+00:00"))
        if run_dt.tzinfo is None:
            run_dt = run_dt.replace(tzinfo=timezone.utc)
        return self.fetch_hourly(
            lat,
            lon,
            kind="single_run",
            run=run,
            models=models,
            forecast_days=None,
            start_date=None,
            end_date=None,
            fetched_at=run_dt,
        )

    @staticmethod
    def snapshot_to_db_row(
        peak_id: int,
        snapshot: WeatherSnapshot,
        fetched_at: datetime,
    ) -> tuple:
        return (
            peak_id,
            snapshot.valid_at,
            fetched_at,
            snapshot.lead_hours,
            snapshot.temp_c,
            snapshot.dewpoint_c,
            snapshot.rh,
            snapshot.wind_ms,
            snapshot.wind_dir,
            snapshot.cloud_cover,
            snapshot.cloud_cover_low,
            snapshot.cloud_cover_mid,
            snapshot.pressure_hpa,
            snapshot.source_model,
            json.dumps(snapshot.raw) if snapshot.raw else None,
        )
