#!/usr/bin/env python3
"""Generate inversion labels from METAR (+ optional GOES) observations."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.clients.goes_fls import GoesFlsClient
from ml.clients.iem_metar import IemMetarClient
from ml.config import DEFINITION_VERSION, PNW_METAR_STATIONS
from ml.db import fetch_all, upsert_observations
from ml.inversion.definition import assess_inversion


def load_peaks(limit: int | None = None) -> list[dict]:
    query = """
        SELECT id, ST_Y(geom) AS lat, ST_X(geom) AS lon, elevation_m
        FROM peaks
        WHERE elevation_m IS NOT NULL
        ORDER BY elevation_m DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return fetch_all(query)


def run(*, days: int = 7, limit: int | None = None) -> int:
    peaks = load_peaks(limit=limit)
    if not peaks:
        print("No peaks found.")
        return 0

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    metar_client = IemMetarClient()
    goes_client = GoesFlsClient()
    stations = list(PNW_METAR_STATIONS.keys())
    observations = metar_client.fetch_observations(stations, start, end)

    obs_by_station: dict[str, list] = {}
    for obs in observations:
        obs_by_station.setdefault(obs.station_id, []).append(obs)

    peak_station: dict[int, str] = {}
    for peak in peaks:
        station_id, _ = IemMetarClient.nearest_station(peak["lat"], peak["lon"])
        peak_station[peak["id"]] = station_id

    rows: list[tuple] = []
    for peak in tqdm(peaks, desc="Labeling peaks"):
        station_id = peak_station[peak["id"]]
        station_obs = obs_by_station.get(station_id, [])
        elevation_m = float(peak["elevation_m"])

        for obs in station_obs:
            assessment = assess_inversion(
                elevation_m=elevation_m,
                temp_c=obs.temp_c,
                dewpoint_c=obs.dewpoint_c,
                valley_temp_c=obs.temp_c,
                rh=obs.rh,
                wind_ms=obs.wind_ms,
                cloud_cover_low=80.0 if obs.cloud_base_m else 10.0,
                observed_ceiling_m=obs.cloud_base_m,
                has_observation=True,
            )

            goes_sample = goes_client.sample_point(peak["lat"], peak["lon"], obs.observed_at)
            source = "metar"
            above_cloud = assessment.above_cloud
            if goes_sample is not None:
                goes_label = goes_client.observation_to_label(goes_sample, elevation_m)
                if goes_label is not None:
                    above_cloud = goes_label
                    source = "metar+goes"

            rows.append(
                (
                    peak["id"],
                    station_id,
                    obs.observed_at,
                    obs.cloud_base_m,
                    obs.visibility_m,
                    obs.temp_c,
                    obs.rh,
                    obs.wind_ms,
                    above_cloud,
                    assessment.inversion_present,
                    assessment.strength,
                    assessment.stability_index,
                    assessment.margin_m,
                    source,
                    DEFINITION_VERSION,
                )
            )

    count = 0
    batch_size = 5000
    deduped: dict[tuple, tuple] = {}
    for row in rows:
        key = (row[0], row[2], row[13])  # peak_id, observed_at, source
        deduped[key] = row
    unique_rows = list(deduped.values())
    for i in range(0, len(unique_rows), batch_size):
        count += upsert_observations(unique_rows[i : i + batch_size])
    print(f"Upserted {count} observation labels.")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate inversion labels from METAR")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(days=args.days, limit=args.limit)


if __name__ == "__main__":
    main()
