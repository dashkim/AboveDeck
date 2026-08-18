#!/usr/bin/env python3
"""Score peaks using ML model or rule-based fallback."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.config import DEFAULT_MODEL_VERSION, ML_MODEL_VERSION, get_settings
from ml.db import fetch_all, upsert_predictions
from ml.features import FEATURE_COLUMNS, build_features
from ml.inversion.scoring import inversion_strength_from_prob

DB_BATCH_SIZE = 5000


def load_model():
    settings = get_settings()
    model_path = Path(settings.models_dir) / f"{ML_MODEL_VERSION}.joblib"
    if not model_path.exists():
        return None, DEFAULT_MODEL_VERSION
    artifact = joblib.load(model_path)
    return artifact["model"], artifact.get("version", ML_MODEL_VERSION)


def load_peaks_with_weather(limit: int | None = None) -> list[dict]:
    query = """
        SELECT p.id, ST_Y(p.geom) AS lat, ST_X(p.geom) AS lon,
               p.elevation_m, p.prominence_m
        FROM peaks p
        WHERE p.elevation_m IS NOT NULL
          AND EXISTS (SELECT 1 FROM weather_peak wp WHERE wp.peak_id = p.id)
        ORDER BY p.elevation_m DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return fetch_all(query)


def load_latest_weather_bulk() -> dict[int, list[dict]]:
    rows = fetch_all(
        """
        SELECT wp.*
        FROM weather_peak wp
        JOIN (
            SELECT peak_id, max(fetched_at) AS fetched_at
            FROM weather_peak
            GROUP BY peak_id
        ) latest ON latest.peak_id = wp.peak_id AND latest.fetched_at = wp.fetched_at
        ORDER BY wp.peak_id, wp.valid_at
        """
    )
    by_peak: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_peak[row["peak_id"]].append(row)
    return by_peak


def run(*, limit: int | None = None) -> int:
    model, model_version = load_model()
    peaks = load_peaks_with_weather(limit=limit)
    if not peaks:
        print("No peaks with weather data found.")
        return 0

    weather_by_peak = load_latest_weather_bulk()
    feature_rows: list[dict] = []
    meta_rows: list[tuple] = []

    for peak in peaks:
        for w in weather_by_peak.get(peak["id"], []):
            features = build_features(
                peak_id=peak["id"],
                lat=peak["lat"],
                lon=peak["lon"],
                elevation_m=float(peak["elevation_m"]),
                prominence_m=peak.get("prominence_m"),
                valid_at=w["valid_at"],
                temp_c=w["temp_c"],
                dewpoint_c=w["dewpoint_c"],
                rh=w["rh"],
                wind_ms=w["wind_ms"],
                wind_dir=w["wind_dir"],
                cloud_cover=w["cloud_cover"],
                cloud_cover_low=w["cloud_cover_low"],
                cloud_cover_mid=w["cloud_cover_mid"],
                pressure_hpa=w["pressure_hpa"],
                lead_hours=w["lead_hours"],
                has_observation=False,
            )
            feature_rows.append({col: features.get(col) for col in FEATURE_COLUMNS})
            meta_rows.append(
                (
                    peak["id"],
                    w["valid_at"],
                    w["lead_hours"],
                    features["estimated_cloud_base_m"],
                    features["confidence_rules"],
                    float(features["above_cloud_prob_rules"]),
                )
            )

    if not feature_rows:
        print("No weather rows to score.")
        return 0

    X = pd.DataFrame(feature_rows).astype(float)
    if model is not None:
        probs = model.predict_proba(X)[:, 1]
        version = model_version
    else:
        probs = X.get("above_cloud_prob_rules", pd.Series([0.0] * len(X)))
        if model is None:
            probs = pd.Series([m[5] for m in meta_rows])
        version = DEFAULT_MODEL_VERSION

    all_rows: list[tuple] = []
    for prob, meta in zip(probs, meta_rows):
        peak_id, valid_at, lead_hours, cloud_base, confidence, _rules_prob = meta
        prob_f = float(prob)
        all_rows.append(
            (
                peak_id,
                valid_at,
                lead_hours,
                prob_f,
                inversion_strength_from_prob(prob_f),
                cloud_base,
                confidence,
                version,
            )
        )

    count = 0
    for i in range(0, len(all_rows), DB_BATCH_SIZE):
        count += upsert_predictions(all_rows[i : i + DB_BATCH_SIZE])

    print(f"Scored {len(peaks)} peaks, upserted {count} predictions (model_version={version}).")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Score peaks from latest weather")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(limit=args.limit)


if __name__ == "__main__":
    main()
