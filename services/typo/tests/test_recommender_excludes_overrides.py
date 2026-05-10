"""Test that user-override rows are excluded from Ridge fit (rev. 4 fix 54)."""
import json
import sqlite3
import time
from pathlib import Path

import pytest

from app.ml.arms import ARMS
from app.ml.model import MIN_EVENTS_FOR_FIT, fit_user_model, load_events_for_user


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("LUME_DB_PATH", str(db_file))
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    conn = sqlite3.connect(str(db_file))
    conn.executescript(schema_path.read_text())
    conn.commit()
    return conn


def _insert_event(conn, was_user_modified: int, arm_index: int = 0, reward: float = 0.7):
    now = int(time.time() * 1000)
    cfg_json = json.dumps(ARMS[arm_index])
    feats_json = json.dumps({
        "avg_word_len": 4.5, "syllable_density": 1.3,
        "freq_percentile_mean": 0.5, "sentence_count": 5, "flesch_kincaid": 8.0,
    })
    conn.execute(
        """INSERT INTO events
           (user_id, render_id, text_id, text_hash, features_json, adaptation_config_json,
            arm_index, recommendation_source, was_user_modified, word_count,
            wpm, comprehension_score, comprehension_type, self_rating, mcq_correct,
            reward, data_source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("u1", None, None, "hash123", feats_json, cfg_json, arm_index,
         "bandit", was_user_modified, 60, 180.0, reward, "self_rated", None, None, reward, "demo", now),
    )


def test_override_rows_excluded_from_load(temp_db):
    """was_user_modified=1 rows must not appear in load_events_for_user."""
    conn = temp_db
    for _ in range(35):
        _insert_event(conn, was_user_modified=0)
    for _ in range(5):
        _insert_event(conn, was_user_modified=1)
    conn.commit()

    events = load_events_for_user(conn, "u1", exclude_user_modified=True)
    assert len(events) == 35, f"Expected 35, got {len(events)}"


def test_model_trained_without_overrides(temp_db):
    """fit_user_model should succeed on 35 non-override events."""
    conn = temp_db
    for _ in range(35):
        _insert_event(conn, was_user_modified=0)
    # Add override rows that must not count toward the minimum
    for _ in range(20):
        _insert_event(conn, was_user_modified=1)
    conn.commit()

    events = load_events_for_user(conn, "u1", exclude_user_modified=True)
    model = fit_user_model("u1", events)
    assert model is not None, "Model should fit on 35 non-override events"
    assert model.n_events == 35


def test_model_returns_none_below_threshold(temp_db):
    """Fewer than MIN_EVENTS_FOR_FIT non-override rows → model returns None."""
    conn = temp_db
    for _ in range(MIN_EVENTS_FOR_FIT - 1):
        _insert_event(conn, was_user_modified=0)
    conn.commit()

    events = load_events_for_user(conn, "u1", exclude_user_modified=True)
    model = fit_user_model("u1", events)
    assert model is None
