CREATE TABLE IF NOT EXISTS observations (
  id                  SERIAL PRIMARY KEY,
  peak_id             INTEGER NOT NULL REFERENCES peaks(id) ON DELETE CASCADE,
  station_id          TEXT,
  observed_at         TIMESTAMPTZ NOT NULL,
  cloud_base_m        REAL,
  visibility_m        REAL,
  temp_c              REAL,
  rh                  REAL,
  wind_ms             REAL,
  above_cloud         BOOLEAN,
  inversion_present   BOOLEAN,
  strength            TEXT,
  stability_index     REAL,
  margin_m            REAL,
  source              TEXT NOT NULL,
  definition_version  TEXT NOT NULL DEFAULT 'inv-def-v1',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (peak_id, observed_at, source)
);

CREATE INDEX IF NOT EXISTS observations_peak_observed_idx ON observations (peak_id, observed_at);
CREATE INDEX IF NOT EXISTS observations_station_observed_idx ON observations (station_id, observed_at);
