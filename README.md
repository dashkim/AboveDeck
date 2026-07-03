# Cloud Inversion Forecast for Hikers (Oregon & Washington)

## Repository layout

```
AboveDeck/
├── index.html      # Live app (Render static site entry point)
├── assets/         # Favicons and static media
├── data/           # GeoJSON and other data files
├── templates/      # System status page
├── api/            # FastAPI backend (Render web service)
├── planning/       # Design docs and roadmap
├── README.md
└── LICENSE
```

**Deploy:** Render static site publishes from repo root (`.`), with `index.html` as the entry point. The API lives in `api/` with Root Directory set to `api`.

---

## Project Vision

Build a web application that predicts **mountain cloud inversions** across Oregon and Washington, allowing hikers and photographers to easily determine when and where they are likely to experience a "sea of clouds."

The goal is not to create another weather app. Existing weather apps already provide forecasts for temperature, wind, and precipitation. This application should answer a different question:

> **Where should I hike to be above the clouds?**

The application should combine weather forecasts, terrain analysis, and machine learning into a single interactive map that predicts inversion conditions up to seven days into the future.

---

# MVP Goals

Users should be able to:

- View an interactive map of Oregon and Washington.
- Move an hourly timeline slider to see inversion forecasts over the next seven days.
- Click anywhere on the map to view inversion information.
- Search for hikes or viewpoints.
- See the probability of being above the cloud layer.
- See recommended sunrise viewing windows.
- View confidence in each prediction.

The interface should prioritize simplicity and beautiful visualization over meteorological complexity.

---

# Example User Experience

A user wants to hike McNeil Point on Saturday.

They open the website.

The map displays colored overlays:

- 🟢 No inversion
- 🟡 Possible inversion
- 🟠 Strong inversion
- 🔴 Excellent chance of a cloud sea

They click **McNeil Point** and see:

| Time | Prediction |
|------|------------|
| 5:00 AM | Strong inversion |
| 6:00 AM | Excellent |
| 7:00 AM | Peak cloud sea |
| 8:00 AM | Excellent |
| 9:00 AM | Beginning to burn off |
| 10:00 AM | Mostly clear |

The user immediately knows the ideal hiking window.

---

# Geographic Scope

Initial release:

- Oregon
- Washington

Future expansion:

- Northern California
- Idaho
- British Columbia
- Entire western United States

---

# Data Sources

## Weather Forecast Models

Potential sources:

- NOAA HRRR
- NOAA GFS
- NAM
- ECMWF (future)

Forecast variables:

- Temperature
- Dew point
- Relative humidity
- Wind speed
- Wind direction
- Pressure
- Cloud cover
- Solar radiation
- Precipitation
- Boundary layer height (if available)

Forecast data should automatically refresh multiple times per day.

---

## Terrain Data

Use a Digital Elevation Model (DEM).

Potential sources:

- USGS 3DEP
- Copernicus DEM
- SRTM

Generate derived terrain layers:

- Elevation
- Slope
- Aspect
- Curvature
- Terrain Ruggedness Index
- Topographic Position Index
- Valley depth
- Ridge distance
- Valley distance
- Relative elevation
- Cold-air pooling index
- Sky-view factor

Terrain processing is performed once and stored.

---

## Historical Labels

Train using historical observations.

Potential sources:

### GOES Satellite Imagery

Detect:

- Low cloud
- Fog
- Cloud extent

---

### Mountain Webcams

Examples:

- Timberline Lodge
- Mt. Hood Meadows
- ODOT cameras
- WSDOT cameras
- Ski resorts

Useful for validating predictions.

---

### Weather Stations

Examples:

- SNOTEL
- RAWS
- NOAA
- Mesonet stations

Variables:

- Temperature
- Humidity
- Wind
- Pressure

---

### Radiosondes

Useful for:

- Inversion height
- Temperature profiles
- Atmospheric stability

---

# Machine Learning Pipeline

## Phase 1

Use Gradient Boosted Trees.

Recommended models:

- XGBoost
- LightGBM

Inputs:

- Forecast weather
- Terrain features
- Time of day
- Day of year
- Geographic location

Outputs:

- Inversion probability
- Above-cloud probability
- Estimated inversion strength

---

## Phase 2

Move toward spatial deep learning.

Possible models:

- CNNs
- U-Net
- Graph Neural Networks
- Physics-informed neural networks

Goal:

Generate continuous inversion probability maps over the entire Pacific Northwest.

---

# Primary Prediction

Instead of simply predicting:

- Inversion: Yes / No

Predict something meaningful to hikers:

> **Probability that this location will be above the cloud layer.**

Example:

| Time | Above Cloud Probability |
|------|-------------------------|
| 5 AM | 96% |
| 6 AM | 99% |
| 7 AM | 99% |
| 8 AM | 97% |
| 9 AM | 84% |

This is the core value of the application.

---

# Interactive Map

The map should be the centerpiece of the application.

Desired features:

- Smooth pan and zoom
- Hourly timeline animation
- Forecast playback
- Hover predictions
- Click for detailed forecast
- Search by hike
- Favorite hikes
- Mobile friendly

Potential overlays:

- Inversion probability
- Cloud cover
- Fog
- Wind
- Temperature
- Humidity
- Terrain
- Satellite imagery
- Sunrise and sunset
- Trailheads
- Hiking trails

---

# Popular Hiking Locations

Examples to support on launch:

## Oregon

- McNeil Point
- Tom Dick and Harry Mountain
- Larch Mountain
- Saddle Mountain
- Dog Mountain
- Mary's Peak
- Mount Pisgah

## Washington

- Mount Ellinor
- High Rock Lookout
- Tolmie Peak
- Skyline Trail
- Fremont Lookout
- Burroughs Mountain
- Table Mountain

Each location should have:

- Hourly forecast
- Best viewing window
- Prediction confidence
- Weather summary

---

# Validation

Compare predictions against:

- GOES satellite imagery
- Mountain webcams
- Weather stations
- User reports

Metrics:

- Accuracy
- Precision
- Recall
- ROC-AUC
- F1 Score
- Calibration
- Spatial accuracy

---

# Future Features

- User-submitted trip reports
- User-uploaded photos
- AI verification of inversion conditions
- Personalized recommendations
- Push notifications
- Favorite hikes
- Historical inversion archive
- Seasonal statistics
- Public API
- Social sharing

---

# Tech Stack

## Frontend

- React
- TypeScript
- Tailwind CSS
- MapLibre GL JS

## Backend

- FastAPI
- PostgreSQL
- PostGIS
- Redis

## Machine Learning

- PyTorch
- XGBoost
- LightGBM
- scikit-learn

## Geospatial

- Rasterio
- GDAL
- Xarray
- GeoPandas
- Dask

## Data Formats

- NetCDF
- GRIB2
- GeoTIFF
- Zarr

---

# Long-Term Vision

Create the definitive forecasting platform for hikers and photographers in the Pacific Northwest.

Instead of asking:

> "What's the weather?"

Users should ask:

> **"Where should I hike this weekend to get above the clouds?"**

The application should become the go-to planning tool for sunrise hikes, photography trips, and mountain adventures by combining machine learning, weather forecasting, terrain analysis, and an intuitive map-based interface.

---

# UI/Wireframe Goals (Initial Cursor Prompt)

Design a modern, clean, map-first interface inspired by products like Google Maps, Gaia GPS, Windy, and AllTrails.

The homepage should immediately answer the question:

> **"Where will the best cloud inversions be?"**

### Primary layout

- Large interactive map occupying most of the screen
- Timeline slider across the bottom (hour-by-hour forecast)
- Search bar at the top
- Layer selector
- Forecast legend
- Collapsible side panel

### Clicking a location opens a side panel showing:

- Above-cloud probability
- Inversion strength
- Forecast graph
- Weather summary
- Sunrise and sunset
- Best viewing window
- Confidence score
- Nearby hikes

### Color palette

- Blues and whites for cloud layers
- Greens for terrain
- Warm sunrise oranges
- Minimal, modern design
- Smooth animations
- Emphasis on beautiful visualization over dense meteorological data