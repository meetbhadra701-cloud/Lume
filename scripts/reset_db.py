#!/usr/bin/env python3
"""Reset the Lume SQLite database.

Drops and recreates from schema.sql, then seeds with demo_seed_events.jsonl.
Stdlib-only — no third-party imports.

Usage (from any directory):
    python scripts/reset_db.py
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

# Compute repo root from this script's location
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "services" / "typo" / "schema.sql"
SEED_PATH = REPO_ROOT / "services" / "typo" / "app" / "eda" / "demo_seed_events.jsonl"

# DB path: env override or default
DB_PATH = Path(os.environ.get("LUME_DB_PATH") or (REPO_ROOT / "services" / "typo" / "seed.db"))


def reset(db_path: Path, schema_path: Path, seed_path: Path) -> None:
    if not schema_path.exists():
        print(f"ERROR: schema not found at {schema_path}", file=sys.stderr)
        sys.exit(1)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        # Drop tables
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS events")
        conn.execute("DROP TABLE IF EXISTS meta")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

        # Recreate from schema
        schema_sql = schema_path.read_text()
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Schema applied from {schema_path}")

        # Seed demo events if file exists
        if seed_path.exists():
            rows_inserted = 0
            with open(seed_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    conn.execute(
                        """
                        INSERT INTO events (
                            user_id, render_id, text_id, text_hash, features_json,
                            adaptation_config_json, arm_index, recommendation_source,
                            was_user_modified, word_count, wpm, comprehension_score,
                            comprehension_type, reward, data_source, created_at
                        ) VALUES (
                            :user_id, :render_id, :text_id, :text_hash, :features_json,
                            :adaptation_config_json, :arm_index, :recommendation_source,
                            :was_user_modified, :word_count, :wpm, :comprehension_score,
                            :comprehension_type, :reward, :data_source, :created_at
                        )
                        """,
                        row,
                    )
                    rows_inserted += 1
            conn.commit()
            print(f"Seeded {rows_inserted} demo events from {seed_path}")
        else:
            print(f"No seed file at {seed_path} — starting with empty events table")

        # Verify
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        print(f"DB ready at {db_path} ({count} events)")
    finally:
        conn.close()


if __name__ == "__main__":
    reset(DB_PATH, SCHEMA_PATH, SEED_PATH)
