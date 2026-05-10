"""Test that /rate inserts exactly one event with the correct reward (rev. 4 fix 53)."""
import sqlite3
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ml.reward import blend_comprehension, compute_reward

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


DEFAULT_ADAPTATION_CONFIG = {
    "letter_spacing_em": 0.0,
    "word_spacing_em": 0.0,
    "hyphenation_on": False,
    "emphasis_on": False,
    "color_overlay_on": False,
    "chunked_on": False,
    "opendyslexic_on": False,
}


@pytest.mark.asyncio
async def test_rate_inserts_one_event_with_correct_reward(temp_db, monkeypatch):
    """POST /rate must insert exactly one row with reward matching compute_reward."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First render to get render_id
        render_resp = await client.post(
            "/render",
            json={"text": VALID_TEXT, "user_id": "demo", "mode": "default"},
        )
        assert render_resp.status_code == 200
        render_data = render_resp.json()
        render_id = render_data["render_id"]
        word_count = render_data["word_count"]
        arm_index = render_data["arm_index"]
        rec_source = render_data["recommendation_source"]

        assert word_count >= 50, "Fixture passage must be ≥50 words"

        # Rate it — use both signals (comprehension_type="both")
        wpm = 180.0
        self_rating = 4
        mcq_correct = True
        expected_comprehension = blend_comprehension(self_rating, mcq_correct)
        expected_reward = compute_reward(wpm, expected_comprehension)

        rate_resp = await client.post(
            "/rate",
            json={
                "render_id": render_id,
                "user_id": "demo",
                "adaptation_config": DEFAULT_ADAPTATION_CONFIG,
                "arm_index": arm_index,
                "recommendation_source": rec_source,
                "was_user_modified": False,
                "wpm": wpm,
                "self_rating": self_rating,
                "mcq_correct": mcq_correct,
                "comprehension_type": "both",
            },
        )
        assert rate_resp.status_code == 200
        rate_data = rate_resp.json()
        assert rate_data["ok"] is True

        returned_reward = rate_data["reward"]
        assert abs(returned_reward - expected_reward) < 0.001, (
            f"reward mismatch: got {returned_reward}, expected {expected_reward}"
        )

        # Verify exactly one row and that both raw values are persisted
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute("SELECT * FROM events").fetchall()
        assert len(rows) == 1, f"Expected 1 event, got {len(rows)}"
        row = conn.execute(
            "SELECT self_rating, mcq_correct, comprehension_score, comprehension_type FROM events LIMIT 1"
        ).fetchone()
        conn.close()

        assert row[0] == self_rating, f"self_rating mismatch: {row[0]}"
        assert row[1] == 1, f"mcq_correct should be 1, got {row[1]}"
        assert abs(row[2] - expected_comprehension) < 0.001
        assert row[3] == "both"


@pytest.mark.asyncio
async def test_rate_was_user_modified_roundtrip(temp_db, monkeypatch):
    """was_user_modified bool must be stored as int 0/1 and returned correctly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        render_resp = await client.post(
            "/render",
            json={"text": VALID_TEXT, "user_id": "demo", "mode": "default"},
        )
        assert render_resp.status_code == 200
        render_data = render_resp.json()
        render_id = render_data["render_id"]

        rate_resp = await client.post(
            "/rate",
            json={
                "render_id": render_id,
                "user_id": "demo",
                "adaptation_config": DEFAULT_ADAPTATION_CONFIG,
                "arm_index": -1,
                "recommendation_source": "mode_default",
                "was_user_modified": True,  # True here
                "wpm": 150.0,
                "self_rating": 3,
                "mcq_correct": False,
                "comprehension_type": "both",
            },
        )
        assert rate_resp.status_code == 200

        # Check DB value
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT was_user_modified FROM events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        assert row[0] == 1, f"was_user_modified should be 1, got {row[0]}"
