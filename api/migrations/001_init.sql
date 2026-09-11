-- BoviScan companion schema (SQLite)

CREATE TABLE IF NOT EXISTS weight_events (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  track_id TEXT NOT NULL,
  session_id TEXT,
  timestamp TEXT NOT NULL,
  species TEXT NOT NULL,
  estimated_weight_kg REAL,
  confidence REAL NOT NULL,
  proxy_metrics TEXT NOT NULL DEFAULT '{}',
  calibration_id TEXT,
  synced_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS weighing_sessions (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  event_count INTEGER NOT NULL DEFAULT 0,
  notes TEXT,
  sync_state TEXT NOT NULL DEFAULT 'pending',
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS device_status (
  device_id TEXT PRIMARY KEY,
  online INTEGER NOT NULL DEFAULT 1,
  camera_ok INTEGER NOT NULL DEFAULT 1,
  inference_backend TEXT,
  pipeline_state TEXT,
  cpu_temp_c REAL,
  disk_free_gb REAL,
  last_heartbeat TEXT NOT NULL,
  version TEXT,
  synced_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_outbox (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON weight_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_session ON weight_events(session_id);
CREATE INDEX IF NOT EXISTS idx_outbox_type ON sync_outbox(entity_type);
