CREATE TABLE IF NOT EXISTS weather_peak (
  id                SERIAL PRIMARY KEY,
  peak_id           INTEGER NOT NULL REFERENCES peaks(id) ON DELETE CASCADE,
  valid_at          TIMESTAMPTZ NOT NULL,
  fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  lead_hours        REAL,
  temp_c            REAL,
  dewpoint_c        REAL,
  rh                REAL,
  wind_ms           REAL,
  wind_dir          REAL,
  cloud_cover       REAL,
  cloud_cover_low   REAL,
  cloud_cover_mid   REAL,
  pressure_hpa      REAL,
  source_model      TEXT NOT NULL DEFAULT 'best_match',
  raw_jsonb         JSONB,
  UNIQUE (peak_id, valid_at, fetched_at)
);

CREATE INDEX IF NOT EXISTS weather_peak_peak_valid_idx ON weather_peak (peak_id, valid_at);
CREATE INDEX IF NOT EXISTS weather_peak_fetched_idx ON weather_peak (fetched_at);
