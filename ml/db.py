"""Sync Postgres helpers for ML pipeline scripts."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

from ml.config import get_settings


@contextmanager
def get_connection() -> Iterator[Any]:
    settings = get_settings()
    if not settings.database_configured:
        raise RuntimeError("DATABASE_URL is not configured")
    conn = psycopg2.connect(settings.sync_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query: str, params: tuple | dict | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params: tuple | dict | None = None) -> dict | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute(query: str, params: tuple | dict | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)


def execute_many(query: str, rows: list[tuple]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, rows)


def upsert_weather_peak(rows: list[tuple]) -> int:
    if not rows:
        return 0
    query = """
        INSERT INTO weather_peak (
            peak_id, valid_at, fetched_at, lead_hours,
            temp_c, dewpoint_c, rh, wind_ms, wind_dir,
            cloud_cover, cloud_cover_low, cloud_cover_mid,
            pressure_hpa, source_model, raw_jsonb
        ) VALUES %s
        ON CONFLICT (peak_id, valid_at, fetched_at) DO UPDATE SET
            lead_hours = EXCLUDED.lead_hours,
            temp_c = EXCLUDED.temp_c,
            dewpoint_c = EXCLUDED.dewpoint_c,
            rh = EXCLUDED.rh,
            wind_ms = EXCLUDED.wind_ms,
            wind_dir = EXCLUDED.wind_dir,
            cloud_cover = EXCLUDED.cloud_cover,
            cloud_cover_low = EXCLUDED.cloud_cover_low,
            cloud_cover_mid = EXCLUDED.cloud_cover_mid,
            pressure_hpa = EXCLUDED.pressure_hpa,
            source_model = EXCLUDED.source_model,
            raw_jsonb = EXCLUDED.raw_jsonb
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, rows)
            return len(rows)


def upsert_observations(rows: list[tuple]) -> int:
    if not rows:
        return 0
    query = """
        INSERT INTO observations (
            peak_id, station_id, observed_at, cloud_base_m, visibility_m,
            temp_c, rh, wind_ms, above_cloud, inversion_present,
            strength, stability_index, margin_m, source, definition_version
        ) VALUES %s
        ON CONFLICT (peak_id, observed_at, source)
        DO UPDATE SET
            cloud_base_m = EXCLUDED.cloud_base_m,
            visibility_m = EXCLUDED.visibility_m,
            temp_c = EXCLUDED.temp_c,
            rh = EXCLUDED.rh,
            wind_ms = EXCLUDED.wind_ms,
            above_cloud = EXCLUDED.above_cloud,
            inversion_present = EXCLUDED.inversion_present,
            strength = EXCLUDED.strength,
            stability_index = EXCLUDED.stability_index,
            margin_m = EXCLUDED.margin_m,
            definition_version = EXCLUDED.definition_version
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, rows)
            return len(rows)


def upsert_predictions(rows: list[tuple]) -> int:
    if not rows:
        return 0
    query = """
        INSERT INTO predictions (
            peak_id, valid_at, lead_hours, above_cloud_prob,
            inversion_strength, estimated_cloud_base_m, confidence, model_version
        ) VALUES %s
        ON CONFLICT (peak_id, valid_at, model_version) DO UPDATE SET
            lead_hours = EXCLUDED.lead_hours,
            above_cloud_prob = EXCLUDED.above_cloud_prob,
            inversion_strength = EXCLUDED.inversion_strength,
            estimated_cloud_base_m = EXCLUDED.estimated_cloud_base_m,
            confidence = EXCLUDED.confidence
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, rows)
            return len(rows)
