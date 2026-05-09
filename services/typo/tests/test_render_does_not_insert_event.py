"""Test that /render is read-only — does not insert rows into the events table (rev. 4 fix 52)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Create a temp SQLite DB."""
    import sqlite3
    from pathlib import Path


    db_file = tmp_path / "test.db"
    monkeypatch.setenv("LUME_DB_PATH", str(db_file))
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    conn = sqlite3.connect(str(db_file))
    conn.executescript(schema_path.read_text())
    conn.commit()
    conn.close()
    return db_file


VALID_TEXT = (
    "The ability to read quickly and accurately is a cornerstone of learning. "
    "For adults with dyslexia, standard typographic choices can create unnecessary friction. "
    "Research-informed adaptations such as increased letter spacing and frequency-aware emphasis "
    "can meaningfully improve the reading experience for many readers across diverse backgrounds."
)


@pytest.mark.asyncio
async def test_render_does_not_insert_event(temp_db, monkeypatch):
    """POST /render must not write any rows to the events table."""
    import sqlite3

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Count events before
        conn = sqlite3.connect(str(temp_db))
        count_before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()

        resp = await client.post(
            "/render",
            json={"text": VALID_TEXT, "user_id": "demo", "mode": "default"},
        )
        assert resp.status_code == 200, resp.text

        # Count events after — must be unchanged
        conn = sqlite3.connect(str(temp_db))
        count_after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()

        assert count_after == count_before, (
            f"/render inserted {count_after - count_before} event(s) — must be 0"
        )
