CREATE TABLE IF NOT EXISTS predictions (
  id                      SERIAL PRIMARY KEY,
  peak_id                 INTEGER NOT NULL REFERENCES peaks(id) ON DELETE CASCADE,
  valid_at                TIMESTAMPTZ NOT NULL,
  lead_hours              REAL,
  above_cloud_prob        REAL NOT NULL CHECK (above_cloud_prob >= 0 AND above_cloud_prob <= 1),
  inversion_strength      TEXT NOT NULL,
  estimated_cloud_base_m  REAL,
  confidence              TEXT NOT NULL,
  model_version           TEXT NOT NULL DEFAULT 'rules-v0',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (peak_id, valid_at, model_version)
);

CREATE INDEX IF NOT EXISTS predictions_peak_valid_idx ON predictions (peak_id, valid_at);
