CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS peaks (
  id              SERIAL PRIMARY KEY,
  source_id       INTEGER NOT NULL,
  name            TEXT NOT NULL,
  geom            geometry(Point, 4326) NOT NULL,
  elevation_m     INTEGER,
  prominence_m    INTEGER,
  state           CHAR(2) NOT NULL,
  feature_class   TEXT NOT NULL DEFAULT 'Summit',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, state)
);

CREATE INDEX IF NOT EXISTS peaks_geom_idx ON peaks USING GIST (geom);
CREATE INDEX IF NOT EXISTS peaks_name_trgm_idx ON peaks USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS peaks_elevation_idx ON peaks (elevation_m);
