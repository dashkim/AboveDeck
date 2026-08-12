# AboveDeck

Cloud inversion forecast for hikers and photographers in the **Pacific Northwest**.

Not another weather app. AboveDeck answers a different question:

> **Where should I hike to be above the clouds?**

The goal is an interactive map that predicts mountain cloud inversions (“sea of clouds”) so you can plan sunrise hikes when ridges sit above the deck.

## Geographic scope

**Now:** Oregon and Washington

**Later:** Northern California, Idaho, British Columbia, then the broader western US

## Status

### Done (UI / geo shell)

- MapLibre map of OR/WA with wilderness overlays
- Peak search and bbox-based peak listing from Neon Postgres + PostGIS
- FastAPI backend on Render, static frontend, system status page
- GitHub Actions keepalive (avoids free-tier API cold starts)

### Not done yet

- Real weather ingest
- Real above-cloud / inversion scores (API still returns placeholders)
- Hourly forecast curves and morning viewing windows
- Spatial prediction heatmap
- ML labels and trained models

The map UI is in place. The next work is the **prediction pipeline**.

## Where to go next

Build order — ship peak-level forecasts before fancy map layers or ML:

1. **Nightly weather ingest** — Fetch forecasts per peak (Open-Meteo for MVP; NOAA HRRR later). Persist or pass into scoring.
2. **Wire the rule-based scorer** — [`api/services/scoring.py`](api/services/scoring.py) already maps peak elevation vs estimated cloud base → `above_cloud_prob` and strength buckets (`none` / `possible` / `strong` / `excellent`). Plug it into peak list/detail routes and stop returning zeros.
3. **Hourly morning curves** — High-confidence UI for ~0–48 h; softer “pattern favorable” badges for days 3–7 (inversions are boundary-layer phenomena; timing confidence decays fast).
4. **Labels for ML** — GOES low-cloud/fog imagery plus a few mountain webcams → train LightGBM (or similar) once rules work.
5. **Spatial prediction grid** — Heatmap overlay once peak-level forecasts are trustworthy.

Full architecture, DB design, and free-tier constraints live in [planning/OVERARCHING_PLAN.md](planning/OVERARCHING_PLAN.md).

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
| Jobs | GitHub Actions (keepalive now; nightly weather pipeline next) |
| Scoring (next) | Rule-based elevation vs cloud base, then LightGBM |

## Product north star

Create the go-to planning tool for PNW sunrise hikes and cloud-sea photography:

> **"Where should I hike this weekend to get above the clouds?"**
