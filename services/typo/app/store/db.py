"""SQLite connection and helper utilities for Lume."""
import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from app.store.paths import db_path, repo_root


@contextmanager
def get_conn():
    """Context-manager yielding a SQLite connection with FK enforcement."""
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply schema.sql to the given connection (idempotent CREATE IF NOT EXISTS)."""
    schema_path = repo_root() / "services" / "typo" / "schema.sql"
    schema_sql = schema_path.read_text()
    conn.executescript(schema_sql)


def insert_event(conn: sqlite3.Connection, event: dict[str, Any]) -> int:
    """Insert one event row; returns the new row id.

    bool_to_int converts was_user_modified bool → INTEGER 0/1.
    created_at is always computed here in Python (millisecond precision).
    """
    row = dict(event)
    # Bool → int
    row["was_user_modified"] = int(bool(row.get("was_user_modified", False)))
    # Millisecond timestamp
    row["created_at"] = int(time.time() * 1000)
    # JSON-encode dicts if passed as Python objects
    if isinstance(row.get("features_json"), dict):
        row["features_json"] = json.dumps(row["features_json"])
    if isinstance(row.get("adaptation_config_json"), dict):
        row["adaptation_config_json"] = json.dumps(row["adaptation_config_json"])

    cursor = conn.execute(
        """
        INSERT INTO events (
            user_id, render_id, text_id, text_hash,
            features_json, adaptation_config_json,
            arm_index, recommendation_source,
            was_user_modified, word_count,
            wpm, comprehension_score, comprehension_type,
            reward, data_source, created_at
        ) VALUES (
            :user_id, :render_id, :text_id, :text_hash,
            :features_json, :adaptation_config_json,
            :arm_index, :recommendation_source,
            :was_user_modified, :word_count,
            :wpm, :comprehension_score, :comprehension_type,
            :reward, :data_source, :created_at
        )
        """,
        row,
    )
    return cursor.lastrowid  # type: ignore[return-value]


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict; parse JSON fields."""
    d = dict(row)
    d["was_user_modified"] = bool(d.get("was_user_modified", 0))
    for key in ("features_json", "adaptation_config_json"):
        if isinstance(d.get(key), str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d
