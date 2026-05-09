"""Tests for the process-local render cache (rev. 4 fix 55).

Cache key is (text_hash, sha1(json(adaptation_config_canonical))).
Same text + different configs must be separate cache entries.
"""
from pathlib import Path
import sqlite3

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

VALID_TEXT = (
    "The ability to read quickly and accurately is a cornerstone of learning. "
    "For adults with dyslexia, standard typographic choices can create unnecessary friction. "
    "Research-informed adaptations such as increased letter spacing and frequency-aware emphasis "
    "can meaningfully improve the reading experience for many readers across diverse backgrounds."
)


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("LUME_DB_PATH", str(db_file))
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    conn = sqlite3.connect(str(db_file))
    conn.executescript(schema_path.read_text())
    conn.commit()
    conn.close()
    return db_file


@pytest.mark.asyncio
async def test_render_cache_keyed_by_config(temp_db, monkeypatch):
    """Same text, two different adaptation configs → two separate renders (different render_ids)."""
    from app.api.routes import render_cache

    # Clear cache for clean test
    render_cache.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        config_a = {
            "letter_spacing_em": 0.0, "word_spacing_em": 0.0,
            "hyphenation_on": False, "emphasis_on": False,
            "color_overlay_on": False, "chunked_on": False, "opendyslexic_on": False,
        }
        config_b = {
            "letter_spacing_em": 0.04, "word_spacing_em": 0.16,
            "hyphenation_on": False, "emphasis_on": True,
            "color_overlay_on": False, "chunked_on": False, "opendyslexic_on": False,
        }

        # Render with config A
        resp_a = await client.post(
            "/render",
            json={
                "text": VALID_TEXT,
                "user_id": "demo",
                "mode": "default",
                "adaptation_config": config_a,
                "arm_index": -1,
                "recommendation_source": "user_override",
            },
        )
        assert resp_a.status_code == 200

        # Render with config B (same text, different config)
        resp_b = await client.post(
            "/render",
            json={
                "text": VALID_TEXT,
                "user_id": "demo",
                "mode": "default",
                "adaptation_config": config_b,
                "arm_index": -1,
                "recommendation_source": "user_override",
            },
        )
        assert resp_b.status_code == 200

        # There should be 2 separate cache entries
        assert len(render_cache) == 2, (
            f"Expected 2 cache entries for 2 different configs, got {len(render_cache)}"
        )

        # Render IDs should be different (different render sessions)
        assert resp_a.json()["render_id"] != resp_b.json()["render_id"]

        # Adaptation configs in response should differ
        assert resp_a.json()["adaptation_config"]["emphasis_on"] is False
        assert resp_b.json()["adaptation_config"]["emphasis_on"] is True


@pytest.mark.asyncio
async def test_render_cache_hit_same_config(temp_db, monkeypatch):
    """Same text + same config → cache hit (tokens are identical)."""
    from app.api.routes import render_cache

    render_cache.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cfg = {
            "letter_spacing_em": 0.04, "word_spacing_em": 0.0,
            "hyphenation_on": False, "emphasis_on": False,
            "color_overlay_on": False, "chunked_on": False, "opendyslexic_on": False,
        }

        resp1 = await client.post(
            "/render",
            json={
                "text": VALID_TEXT,
                "user_id": "demo",
                "mode": "default",
                "adaptation_config": cfg,
                "arm_index": -1,
                "recommendation_source": "user_override",
            },
        )
        resp2 = await client.post(
            "/render",
            json={
                "text": VALID_TEXT,
                "user_id": "demo",
                "mode": "default",
                "adaptation_config": cfg,
                "arm_index": -1,
                "recommendation_source": "user_override",
            },
        )
        assert resp1.status_code == resp2.status_code == 200
        # Cache should have exactly 1 entry (cache hit on second call)
        assert len(render_cache) == 1
        # Tokens should match
        assert resp1.json()["tokens"] == resp2.json()["tokens"]
