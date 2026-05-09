"""Test that /rate infers data_source server-side (rev. 4 fix 51).

Rules:
- 'real_user' if LUME_COLLECT_MODE == 'real_user'
- 'demo' if user_id == DEMO_USER_ID
- 'demo' otherwise (live API never writes 'synthetic')
"""
import sqlite3
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

VALID_TEXT = (
    "The ability to read quickly and accurately is a cornerstone of learning. "
    "For adults with dyslexia, standard typographic choices can create unnecessary friction. "
    "Research-informed adaptations such as increased letter spacing and frequency-aware emphasis "
    "can meaningfully improve the reading experience for many readers across diverse backgrounds. "
    "Personalized typographic settings, tailored to individual needs, may help reduce cognitive load "
    "and support sustained reading engagement over time for learners of all ages."
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
    "letter_spacing_em": 0.0,
    "word_spacing_em": 0.0,
    "hyphenation_on": False,
    "emphasis_on": False,
    "color_overlay_on": False,
    "chunked_on": False,
    "opendyslexic_on": False,
}


async def _do_render_rate(client, user_id="demo"):
    render_resp = await client.post(
        "/render",
        json={"text": VALID_TEXT, "user_id": user_id, "mode": "default"},
    )
    assert render_resp.status_code == 200
    render_data = render_resp.json()

    rate_resp = await client.post(
        "/rate",
        json={
            "render_id": render_data["render_id"],
            "user_id": user_id,
            "adaptation_config": DEFAULT_CONFIG,
            "arm_index": render_data["arm_index"],
            "recommendation_source": render_data["recommendation_source"],
            "was_user_modified": False,
            "wpm": 150.0,
            "comprehension_score": 0.6,
            "comprehension_type": "self_rated",
        },
    )
    assert rate_resp.status_code == 200
    return rate_resp.json()


@pytest.mark.asyncio
async def test_data_source_demo_for_demo_user(temp_db, monkeypatch):
    """user_id=demo → data_source='demo'."""
    monkeypatch.delenv("LUME_COLLECT_MODE", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _do_render_rate(client, user_id="demo")

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT data_source FROM events LIMIT 1").fetchone()
    conn.close()
    assert row[0] == "demo"


@pytest.mark.asyncio
async def test_data_source_real_user_when_collect_mode_set(temp_db, monkeypatch):
    """LUME_COLLECT_MODE=real_user → data_source='real_user'."""
    monkeypatch.setenv("LUME_COLLECT_MODE", "real_user")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _do_render_rate(client, user_id="demo")

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT data_source FROM events LIMIT 1").fetchone()
    conn.close()
    assert row[0] == "real_user"


@pytest.mark.asyncio
async def test_data_source_never_synthetic_from_live_api(temp_db, monkeypatch):
    """Live API must never write data_source='synthetic'."""
    monkeypatch.delenv("LUME_COLLECT_MODE", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _do_render_rate(client, user_id="test_user_x")

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT data_source FROM events LIMIT 1").fetchone()
    conn.close()
    assert row[0] != "synthetic", "Live API must never write 'synthetic'"
