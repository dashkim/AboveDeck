#!/usr/bin/env python3
"""Nightly Open-Meteo ingest for all peaks."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.clients.open_meteo import OpenMeteoClient
from ml.db import fetch_all, upsert_weather_peak

API_BATCH_SIZE = 50
DB_BATCH_SIZE = 500


def load_peaks(limit: int | None = None, *, skip_ingested: bool = False) -> list[dict]:
    query = """
        SELECT id, ST_Y(geom) AS lat, ST_X(geom) AS lon, elevation_m
        FROM peaks
        WHERE elevation_m IS NOT NULL
    """
    if skip_ingested:
        query += """
          AND NOT EXISTS (
              SELECT 1 FROM weather_peak wp
              WHERE wp.peak_id = peaks.id
                AND wp.fetched_at > now() - interval '18 hours'
          )
        """
    query += " ORDER BY elevation_m DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    return fetch_all(query)


def run(
    *,
    forecast_days: int = 7,
    limit: int | None = None,
    api_batch_size: int = API_BATCH_SIZE,
    skip_ingested: bool = True,
) -> int:
    peaks = load_peaks(limit=limit, skip_ingested=skip_ingested)
    if not peaks:
        print("No peaks left to ingest.")
        return 0
    print(f"Ingesting {len(peaks)} peaks (skip_ingested={skip_ingested}).")

    client = OpenMeteoClient()
    fetched_at = datetime.now(timezone.utc)
    total_rows = 0

    for start in tqdm(range(0, len(peaks), api_batch_size), desc="Ingesting weather"):
        batch = peaks[start : start + api_batch_size]
        locations = [(p["lat"], p["lon"]) for p in batch]
        snapshot_groups = client.fetch_forecast_batch(
            locations,
            forecast_days=forecast_days,
            fetched_at=fetched_at,
        )
        rows: list[tuple] = []
        for peak, snapshots in zip(batch, snapshot_groups):
            rows.extend(
                OpenMeteoClient.snapshot_to_db_row(peak["id"], snap, fetched_at)
                for snap in snapshots
            )
        for i in range(0, len(rows), DB_BATCH_SIZE):
            total_rows += upsert_weather_peak(rows[i : i + DB_BATCH_SIZE])

    print(f"Upserted {total_rows} weather_peak rows for {len(peaks)} peaks.")
    return total_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Open-Meteo forecasts per peak")
    parser.add_argument("--forecast-days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=None, help="Limit peaks (for testing)")
    parser.add_argument("--api-batch-size", type=int, default=API_BATCH_SIZE)
    parser.add_argument(
        "--reingest-all",
        action="store_true",
        help="Fetch every peak even if weather was ingested in the last 18 hours",
    )
    args = parser.parse_args()
    run(
        forecast_days=args.forecast_days,
        limit=args.limit,
        api_batch_size=args.api_batch_size,
        skip_ingested=not args.reingest_all,
    )


if __name__ == "__main__":
    main()
