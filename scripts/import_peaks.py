#!/usr/bin/env python3
"""Extract GNIS Summits from WA/OR gazetteer GPKGs, enrich via USGS EPQS, upsert to Neon."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import execute_values
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
GPKG_ZIPS = [
    (DATA_DIR / "Gazetteer_WA_GPKG.zip", "WA", "Gazetteer_WA_GPKG.gpkg"),
    (DATA_DIR / "Gazetteer_OR_GPKG.zip", "OR", "Gazetteer_OR_GPKG.gpkg"),
]
EPQS_URL = "https://epqs.nationalmap.gov/v1/json"
SUMMIT_QUERY = """
SELECT f.feature_id, n.feature_name, f.prim_lat_dec, f.prim_long_dec
FROM Gaz_Features f
JOIN Gaz_Names n ON f.feature_id = n.feature_id
WHERE f.feature_class = 'Summit'
  AND n.feature_name_official = 1
  AND f.prim_lat_dec IS NOT NULL
  AND f.prim_long_dec IS NOT NULL
"""


@dataclass
class Summit:
    source_id: int
    name: str
    lat: float
    lon: float
    state: str


def sync_database_url(url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql://" + url.split("://", 1)[1]
    return url


def extract_summits(gpkg_path: Path, state: str) -> list[Summit]:
    conn = sqlite3.connect(gpkg_path)
    try:
        rows = conn.execute(SUMMIT_QUERY).fetchall()
    finally:
        conn.close()
    return [
        Summit(
            source_id=row[0],
            name=row[1].strip(),
            lat=row[2],
            lon=row[3],
            state=state,
        )
        for row in rows
        if row[1] and row[1].strip()
    ]


def fetch_elevation_m(lon: float, lat: float, session: requests.Session) -> int | None:
    response = session.get(
        EPQS_URL,
        params={"x": lon, "y": lat, "units": "Meters"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    value = payload.get("value")
    if value is None:
        return None
    return int(round(float(value)))


def load_summits(skip_epqs: bool = False) -> list[Summit]:
    summits: list[Summit] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for zip_path, state, gpkg_name in GPKG_ZIPS:
            if not zip_path.exists():
                raise FileNotFoundError(f"Missing dataset: {zip_path}")
            with zipfile.ZipFile(zip_path) as archive:
                archive.extract(gpkg_name, tmp_path)
            summits.extend(extract_summits(tmp_path / gpkg_name, state))
    return summits


def enrich_elevations(
    summits: list[Summit],
    *,
    min_elevation_m: int,
    delay_s: float,
    skip_epqs: bool,
) -> list[tuple[Summit, int | None]]:
    enriched: list[tuple[Summit, int | None]] = []
    session = requests.Session()
    iterator = tqdm(summits, desc="EPQS elevation lookup")
    for summit in iterator:
        elevation_m: int | None = None
        if not skip_epqs:
            try:
                elevation_m = fetch_elevation_m(summit.lon, summit.lat, session)
            except requests.RequestException as exc:
                tqdm.write(f"EPQS failed for {summit.name} ({summit.state}): {exc}")
            time.sleep(delay_s)
        enriched.append((summit, elevation_m))

    if min_elevation_m > 0:
        enriched = [
            item for item in enriched
            if item[1] is None or item[1] >= min_elevation_m
        ]
    return enriched


def upsert_peaks(conn, rows: list[tuple[Summit, int | None]]) -> int:
    values = [
        (
            summit.source_id,
            summit.name,
            summit.lon,
            summit.lat,
            elevation_m,
            summit.state,
            "Summit",
        )
        for summit, elevation_m in rows
    ]
    sql = """
        INSERT INTO peaks (source_id, name, geom, elevation_m, state, feature_class)
        VALUES %s
        ON CONFLICT (source_id, state) DO UPDATE SET
            name = EXCLUDED.name,
            geom = EXCLUDED.geom,
            elevation_m = COALESCE(EXCLUDED.elevation_m, peaks.elevation_m),
            feature_class = EXCLUDED.feature_class
    """
    template = "(%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)"
    with conn.cursor() as cur:
        execute_values(cur, sql, values, template=template, page_size=500)
    conn.commit()
    return len(values)


def run_migration(database_url: str) -> None:
    migration_path = REPO_ROOT / "api" / "migrations" / "001_peaks.sql"
    sql = migration_path.read_text()
    conn = psycopg2.connect(sync_database_url(database_url))
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import GNIS summits into Neon Postgres")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--min-elevation-m", type=int, default=1200)
    parser.add_argument("--delay-s", type=float, default=1.0, help="Delay between EPQS requests")
    parser.add_argument("--skip-epqs", action="store_true", help="Load coords only, skip elevation lookup")
    parser.add_argument("--skip-migration", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.database_url:
        print("DATABASE_URL is required (env var or --database-url)", file=sys.stderr)
        return 1

    summits = load_summits()
    print(f"Found {len(summits)} summits across WA and OR")

    if args.dry_run:
        for summit in summits[:5]:
            print(f"  {summit.state} {summit.name} ({summit.lat}, {summit.lon})")
        return 0

    if not args.skip_migration:
        print("Running migration...")
        run_migration(args.database_url)

    enriched = enrich_elevations(
        summits,
        min_elevation_m=args.min_elevation_m,
        delay_s=args.delay_s,
        skip_epqs=args.skip_epqs,
    )
    print(f"Importing {len(enriched)} summits (min elevation {args.min_elevation_m} m)...")

    conn = psycopg2.connect(sync_database_url(args.database_url))
    try:
        count = upsert_peaks(conn, enriched)
    finally:
        conn.close()

    print(f"Done. Upserted {count} peaks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
