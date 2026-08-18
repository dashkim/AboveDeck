#!/usr/bin/env python3
"""Backfill historical weather and METAR for training."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.clients.iem_metar import IemMetarClient
from ml.clients.open_meteo import OpenMeteoClient
from ml.config import PNW_METAR_STATIONS
from ml.db import fetch_all, upsert_weather_peak


def load_peaks(limit: int | None = None) -> list[dict]:
    query = """
        SELECT id, name, ST_Y(geom) AS lat, ST_X(geom) AS lon, elevation_m, state
        FROM peaks
        WHERE elevation_m IS NOT NULL
        ORDER BY elevation_m DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return fetch_all(query)


def backfill_weather(
    peaks: list[dict],
    start_date: str,
    end_date: str,
) -> int:
    client = OpenMeteoClient()
    fetched_at = datetime.now(timezone.utc)
    total = 0
    for peak in tqdm(peaks, desc="Backfill weather"):
        snapshots = client.fetch_historical(peak["lat"], peak["lon"], start_date, end_date)
        rows = [OpenMeteoClient.snapshot_to_db_row(peak["id"], s, fetched_at) for s in snapshots]
        if rows:
            total += upsert_weather_peak(rows)
    return total


def backfill_metar(start: datetime, end: datetime) -> list:
    client = IemMetarClient()
    stations = list(PNW_METAR_STATIONS.keys())
    return client.fetch_observations(stations, start, end)


def run(
    *,
    months: int = 6,
    limit: int | None = None,
    weather: bool = True,
    metar: bool = True,
) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30 * months)
    start_date = start.strftime("%Y-%m-%d")
    end_date = end.strftime("%Y-%m-%d")

    peaks = load_peaks(limit=limit)
    print(f"Backfilling {len(peaks)} peaks from {start_date} to {end_date}")

    if weather:
        count = backfill_weather(peaks, start_date, end_date)
        print(f"Weather rows upserted: {count}")

    if metar:
        obs = backfill_metar(start, end)
        print(f"Fetched {len(obs)} METAR observations (run label.py to persist)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical weather data")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--weather-only", action="store_true")
    parser.add_argument("--metar-only", action="store_true")
    args = parser.parse_args()
    run(
        months=args.months,
        limit=args.limit,
        weather=not args.metar_only,
        metar=not args.weather_only,
    )


if __name__ == "__main__":
    main()
