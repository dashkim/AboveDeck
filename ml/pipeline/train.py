#!/usr/bin/env python3
"""Train LightGBM inversion classifier with calibration."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.config import ML_MODEL_VERSION, get_settings
from ml.db import fetch_all
from ml.features import FEATURE_COLUMNS, build_features


def load_training_data() -> pd.DataFrame:
    rows = fetch_all(
        """
        SELECT
            o.peak_id,
            o.observed_at AS valid_at,
            o.above_cloud,
            o.cloud_base_m,
            o.temp_c,
            o.rh,
            o.wind_ms,
            p.elevation_m,
            p.prominence_m,
            ST_Y(p.geom) AS lat,
            ST_X(p.geom) AS lon,
            w.dewpoint_c,
            w.cloud_cover,
            w.cloud_cover_low,
            w.cloud_cover_mid,
            w.wind_dir,
            w.pressure_hpa,
            w.lead_hours
        FROM observations o
        JOIN peaks p ON p.id = o.peak_id
        LEFT JOIN LATERAL (
            SELECT *
            FROM weather_peak wp
            WHERE wp.peak_id = o.peak_id
              AND wp.valid_at <= o.observed_at + interval '1 hour'
              AND wp.valid_at >= o.observed_at - interval '3 hours'
            ORDER BY abs(extract(epoch from (wp.valid_at - o.observed_at)))
            LIMIT 1
        ) w ON true
        WHERE o.above_cloud IS NOT NULL
        """
    )
    if not rows:
        return pd.DataFrame()

    feature_rows = []
    labels = []
    for row in rows:
        features = build_features(
            peak_id=row["peak_id"],
            lat=row["lat"],
            lon=row["lon"],
            elevation_m=float(row["elevation_m"]),
            prominence_m=row["prominence_m"],
            valid_at=row["valid_at"],
            temp_c=row["temp_c"],
            dewpoint_c=row.get("dewpoint_c"),
            rh=row["rh"],
            wind_ms=row["wind_ms"],
            wind_dir=row.get("wind_dir"),
            cloud_cover=row.get("cloud_cover"),
            cloud_cover_low=row.get("cloud_cover_low"),
            cloud_cover_mid=row.get("cloud_cover_mid"),
            pressure_hpa=row.get("pressure_hpa"),
            valley_temp_c=row["temp_c"],
            lead_hours=row.get("lead_hours"),
            observed_ceiling_m=row["cloud_base_m"],
            has_observation=True,
        )
        feature_rows.append({col: features.get(col) for col in FEATURE_COLUMNS})
        labels.append(int(row["above_cloud"]))

    df = pd.DataFrame(feature_rows)
    df["above_cloud"] = labels
    return df


def run(*, min_samples: int = 50) -> str | None:
    settings = get_settings()
    df = load_training_data()
    if df.empty or len(df) < min_samples:
        print(f"Insufficient training data ({len(df)} rows, need {min_samples}). Skipping train.")
        return None

    X = df[FEATURE_COLUMNS].astype(float)
    y = df["above_cloud"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    base = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        random_state=42,
        verbose=-1,
    )
    model = CalibratedClassifierCV(base, method="isotonic", cv=3)
    model.fit(X_train, y_train)

    prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        "model_version": ML_MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(df),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "brier_score": float(brier_score_loss(y_test, prob)),
    }
    if y_test.nunique() > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_test, prob))

    artifacts_dir = Path(settings.models_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifacts_dir / f"{ML_MODEL_VERSION}.joblib"
    metrics_path = artifacts_dir / f"{ML_MODEL_VERSION}_metrics.json"

    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "version": ML_MODEL_VERSION}, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2))

    print(f"Saved model to {model_path}")
    print(json.dumps(metrics, indent=2))
    return str(model_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train inversion classifier")
    parser.add_argument("--min-samples", type=int, default=50)
    args = parser.parse_args()
    run(min_samples=args.min_samples)


if __name__ == "__main__":
    main()
