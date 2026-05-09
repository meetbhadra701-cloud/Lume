PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS events (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id                 TEXT    NOT NULL,
  render_id               TEXT,                          -- links event to originating render
  text_id                 TEXT,                          -- nullable; matches frontend seed id
  text_hash               TEXT    NOT NULL,
  features_json           TEXT    NOT NULL,
  adaptation_config_json  TEXT    NOT NULL,
  arm_index               INTEGER,                       -- nullable; -1 for non-arm/user_override
  recommendation_source   TEXT    NOT NULL CHECK(
    recommendation_source IN (
      'bandit', 'model', 'demo_seed', 'mode_default',
      'mode_bionic', 'mode_lume_tuned', 'user_override'
    )
  ),
  was_user_modified       INTEGER NOT NULL DEFAULT 0,    -- bool 0/1
  word_count              INTEGER NOT NULL,              -- enforces ≥50 logging gate
  wpm                     REAL    NOT NULL,
  comprehension_score     REAL    NOT NULL,              -- 0.0–1.0
  comprehension_type      TEXT    NOT NULL CHECK(comprehension_type IN ('mc', 'self_rated')),
  reward                  REAL    NOT NULL,
  data_source             TEXT    NOT NULL CHECK(data_source IN ('synthetic', 'real_user', 'demo')),
  created_at              INTEGER NOT NULL               -- int(time.time()*1000) in Python at insert
);

CREATE INDEX IF NOT EXISTS idx_events_user    ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_render  ON events(render_id);
