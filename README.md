# AboveDeck

Cloud inversion forecast for hikers and photographers in the **Pacific Northwest**.

Not another weather app. AboveDeck answers a different question:

> **Where should I hike to be above the clouds?**

The goal is an interactive map that predicts mountain cloud inversions (“sea of clouds”) so you can plan sunrise hikes when ridges sit above the deck.

## Geographic scope

**Now:** Oregon and Washington

**Later:** Northern California, Idaho, British Columbia, then the broader western US

## Status

### Done

- MapLibre map of OR/WA with wilderness overlays
- Peak search and bbox peak listing from Neon Postgres + PostGIS
- FastAPI on Render + static frontend
- **Live rule-based forecasts** — `GET /peaks` pulls Open-Meteo when scores are missing, scores elevation vs cloud base (`rules-v0`), and stores rows in `predictions`
- `POST /predictions/refresh` for explicit bbox refresh
- Nightly GHA pipeline (top 600 peaks, 3-day horizon, rules scoring, prune)

### Not done yet

- Hourly morning curves / best viewing windows in the UI
- Spatial prediction heatmap (`GET /predictions/grid`)
- Trustworthy LightGBM model (checked-in `inv-clf-v1` is disabled; use `--use-ml` only after retraining)

## Forecast data flow

```
Open-Meteo (per peak lat/lon)
  → rules-v0 scorer (LCL cloud base vs elevation)
  → predictions table
  → GET /peaks
```

Nightly job: `ml/pipeline/ingest.py` → `ml/pipeline/score.py` → `ml/pipeline/prune.py`.  
On-demand: API refresh when the map requests a date with no usable `rules-v0` rows.

## Where to go next

1. **UI hourly curves** — use `/peaks/{id}` hourly payload for 0–48 h windows
2. **Labels + retrain** — METAR/GOES labels, then promote a real ML artifact with `--use-ml`
3. **Prediction grid heatmap** — implement `GET /predictions/grid`
4. **Broader ingest** — raise the nightly peak cap once Neon storage allows

Full architecture notes live in [planning/OVERARCHING_PLAN.md](planning/OVERARCHING_PLAN.md).

## Repository layout

```
AboveDeck/
├── index.html      # Live app (Render static site entry point)
├── assets/         # Favicons, config, static media
├── data/           # GeoJSON and gazetteer data
├── templates/      # System status page
├── api/            # FastAPI backend (Render web service)
├── planning/       # Design docs and roadmap
├── scripts/        # Peak import and related tooling
├── README.md
└── LICENSE
```

**Deploy:** Render static site from repo root (`.` / `index.html`). API Root Directory is `api/`.

**Keepalive:** GitHub Actions cron hits `/health?source=keepalive` so the free-tier API stays warm. Status is on the system status page.

## Tech stack

| Layer | Choice |
|-------|--------|
| Frontend | Static HTML/JS, MapLibre GL JS, Tailwind (CDN) |
| Backend | FastAPI on Render |
| Database | Neon Postgres + PostGIS |
| Jobs | GitHub Actions (keepalive + nightly weather/score) |
| Scoring | Rule-based elevation vs cloud base (`rules-v0`); LightGBM optional |

## Product north star

Create the go-to planning tool for PNW sunrise hikes and cloud-sea photography:

> **"Where should I hike this weekend to get above the clouds?"**
