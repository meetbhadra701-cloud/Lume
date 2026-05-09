"""Tests for SQLite schema and db.py helper functions.

Uses a temp DB via LUME_DB_PATH env override — never touches seed.db.
"""
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Create a temp SQLite DB and point LUME_DB_PATH at it."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("LUME_DB_PATH", str(db_file))
    # Apply schema
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    conn = sqlite3.connect(str(db_file))
    conn.executescript(schema_path.read_text())
    conn.commit()
    conn.close()
    return db_file


def _sample_event(**overrides) -> dict:
    base = dict(
        user_id="demo",
        render_id="render-001",
        text_id=None,
        text_hash="abc123",
        features_json={"avg_word_len": 5.2, "syllable_density": 1.8},
        adaptation_config_json={"letter_spacing_em": 0.04, "emphasis_on": True},
        arm_index=3,
        recommendation_source="bandit",
        was_user_modified=False,
        word_count=75,
        wpm=180.5,
        comprehension_score=0.8,
        comprehension_type="self_rated",
        reward=0.72,
        data_source="demo",
    )
    base.update(overrides)
    return base


class TestSchemaEnums:
    def test_valid_recommendation_sources(self, temp_db, monkeypatch):
        """All valid recommendation_source values should insert cleanly."""
        from app.store.db import get_conn, insert_event

        valid = [
            "bandit", "model", "demo_seed", "mode_default",
            "mode_bionic", "mode_lume_tuned", "user_override",
        ]
        with get_conn() as conn:
            for rs in valid:
                insert_event(conn, _sample_event(recommendation_source=rs))

        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert count == len(valid)

    def test_invalid_recommendation_source_rejected(self, temp_db, monkeypatch):
        """Invalid recommendation_source should raise IntegrityError."""
        from app.store.db import get_conn, insert_event

        with pytest.raises(sqlite3.IntegrityError):
            with get_conn() as conn:
                insert_event(conn, _sample_event(recommendation_source="invalid_source"))

    def test_valid_data_sources(self, temp_db, monkeypatch):
        """All valid data_source values should insert."""
        from app.store.db import get_conn, insert_event

        valid = ["synthetic", "real_user", "demo"]
        with get_conn() as conn:
            for ds in valid:
                insert_event(conn, _sample_event(data_source=ds))

        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert count == 3

    def test_invalid_data_source_rejected(self, temp_db, monkeypatch):
        from app.store.db import get_conn, insert_event

        with pytest.raises(sqlite3.IntegrityError):
            with get_conn() as conn:
                insert_event(conn, _sample_event(data_source="unknown"))


class TestBoolRoundTrip:
    def test_was_user_modified_true_roundtrip(self, temp_db, monkeypatch):
        from app.store.db import get_conn, insert_event, row_to_dict

        with get_conn() as conn:
            insert_event(conn, _sample_event(was_user_modified=True))
            row = conn.execute("SELECT * FROM events LIMIT 1").fetchone()
            d = row_to_dict(row)

        assert d["was_user_modified"] is True

    def test_was_user_modified_false_roundtrip(self, temp_db, monkeypatch):
        from app.store.db import get_conn, insert_event, row_to_dict

        with get_conn() as conn:
            insert_event(conn, _sample_event(was_user_modified=False))
            row = conn.execute("SELECT * FROM events LIMIT 1").fetchone()
            d = row_to_dict(row)

        assert d["was_user_modified"] is False


class TestCreatedAtPrecision:
    def test_created_at_is_milliseconds(self, temp_db, monkeypatch):
        """created_at should be epoch milliseconds (≥ 13 digits for current time)."""
        from app.store.db import get_conn, insert_event

        before = int(time.time() * 1000)
        with get_conn() as conn:
            insert_event(conn, _sample_event())
        after = int(time.time() * 1000)

        with get_conn() as conn:
            row = conn.execute("SELECT created_at FROM events LIMIT 1").fetchone()
        created_at = row[0]

        assert before <= created_at <= after, (
            f"created_at={created_at} outside [{before}, {after}]"
        )
        # Sanity: epoch ms for 2020+ is 13 digits
        assert len(str(created_at)) >= 13


class TestJsonFields:
    def test_json_dict_encoded(self, temp_db, monkeypatch):
        """insert_event should encode dict features_json to JSON string."""
        from app.store.db import get_conn, insert_event, row_to_dict

        feats = {"avg_word_len": 5.2, "sentence_count": 3}
        with get_conn() as conn:
            insert_event(conn, _sample_event(features_json=feats))
            # Raw column should be a JSON string
            raw = conn.execute("SELECT features_json FROM events LIMIT 1").fetchone()[0]
            assert isinstance(raw, str)
            assert json.loads(raw) == feats
            # row_to_dict should parse it back
            row = conn.execute("SELECT * FROM events LIMIT 1").fetchone()
            d = row_to_dict(row)
        assert d["features_json"] == feats
