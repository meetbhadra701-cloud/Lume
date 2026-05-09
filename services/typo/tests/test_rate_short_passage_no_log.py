"""Test that /rate rejects passages with word_count < 50 (rev. 4 fix 9)."""
import sqlite3
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

SHORT_TEXT = "This is a very short passage. It has fewer than fifty words."
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


DEFAULT_CONFIG = {
    "letter_spacing_em": 0.0, "word_spacing_em": 0.0,
    "hyphenation_on": False, "emphasis_on": False,
    "color_overlay_on": False, "chunked_on": False, "opendyslexic_on": False,
}


@pytest.mark.asyncio
async def test_short_passage_render_succeeds_but_rate_does_not_log(temp_db, monkeypatch):
    """Short text (< 50 words) renders OK but /rate returns ok=False and logs nothing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Render succeeds even for short text
        render_resp = await client.post(
            "/render",
            json={"text": SHORT_TEXT, "user_id": "demo", "mode": "default"},
        )
        assert render_resp.status_code == 200, render_resp.text
        render_data = render_resp.json()
        render_id = render_data["render_id"]
        arm_index = render_data["arm_index"]
        rec_source = render_data["recommendation_source"]
        word_count = render_data["word_count"]

        assert word_count < 50, f"Fixture isn't actually short ({word_count} words)"

        # Rate should NOT log (ok=False)
        rate_resp = await client.post(
            "/rate",
            json={
                "render_id": render_id,
                "user_id": "demo",
                "adaptation_config": DEFAULT_CONFIG,
                "arm_index": arm_index,
                "recommendation_source": rec_source,
                "was_user_modified": False,
                "wpm": 150.0,
                "comprehension_score": 0.6,
                "comprehension_type": "self_rated",
            },
        )
        # Either 200 with ok=False or 4xx
        if rate_resp.status_code == 200:
            assert rate_resp.json().get("ok") is False
        else:
            assert rate_resp.status_code in (400, 422)

        # Events table must be empty
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
        assert count == 0, f"Expected 0 events for short passage, got {count}"


@pytest.mark.asyncio
async def test_render_rejects_empty_text(temp_db, monkeypatch):
    """Empty text must be rejected by /render with 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/render",
            json={"text": "", "user_id": "demo", "mode": "default"},
        )
        assert resp.status_code == 422
