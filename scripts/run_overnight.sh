#!/usr/bin/env bash
# Overnight AboveDeck pipeline: ingest remaining weather, score with the trained model.
#
# Usage:
#   ./scripts/run_overnight.sh
#   nohup ./scripts/run_overnight.sh > logs/overnight.out 2>&1 &
#
# Optional env:
#   DATABASE_URL     Neon connection string (or set in api/.env)
#   FORECAST_DAYS    default 7
#   SKIP_TRAIN       set to 1 to skip retraining (default: skip; model already exists)
#   TRAIN            set to 1 to retrain after ingest

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="logs/overnight-${STAMP}.log"

if [[ -f api/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source api/.env
  set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set. Put it in api/.env or export it first." >&2
  exit 1
fi

PYTHON="${ROOT}/.venv312/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

export DATABASE_URL
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export LOKY_MAX_CPU_COUNT="${LOKY_MAX_CPU_COUNT:-1}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

FORECAST_DAYS="${FORECAST_DAYS:-7}"
SKIP_TRAIN="${SKIP_TRAIN:-1}"
if [[ "${TRAIN:-0}" == "1" ]]; then
  SKIP_TRAIN=0
fi

exec > >(tee -a "$LOG") 2>&1

echo "=============================================="
echo "AboveDeck overnight pipeline  ${STAMP}"
echo "log: ${LOG}"
echo "python: ${PYTHON}"
echo "forecast_days: ${FORECAST_DAYS}"
echo "=============================================="

step() {
  echo
  echo "---- $(date -u +%H:%M:%S)  $* ----"
}

fail() {
  echo "FAILED: $*" >&2
  echo "See ${LOG}" >&2
  exit 1
}

step "0/5  Prune Neon (drop weather/labels; keep next 7 days of predictions)"
"${PYTHON}" ml/pipeline/prune.py --horizon-days 7 || fail "prune"

step "1/5  Apply migrations"
"${PYTHON}" scripts/run_migrations.py || fail "migrations"

step "2/5  Ingest Open-Meteo (skips peaks fetched in last 18h)"
"${PYTHON}" ml/pipeline/ingest.py --forecast-days "${FORECAST_DAYS}" || fail "ingest"

if [[ "${SKIP_TRAIN}" == "0" ]]; then
  step "3/5  Retrain model"
  "${PYTHON}" ml/pipeline/train.py --min-samples 50 || fail "train"
else
  step "3/5  Skip train (model already at ml/models/artifacts/inv-clf-v1.joblib)"
fi

step "4/5  Score peaks that have weather"
"${PYTHON}" ml/pipeline/score.py || fail "score"

step "5/5  Prune Neon again (do not leave weather/labels on free-tier storage)"
"${PYTHON}" ml/pipeline/prune.py --horizon-days 7 || fail "prune"

echo
echo "=============================================="
echo "Done  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Log: ${LOG}"
echo "=============================================="
