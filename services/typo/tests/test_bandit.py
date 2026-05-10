"""Tests for Thompson-sampling bandit (Phase 2.2)."""
import numpy as np
import pytest

from app.ml.bandit import LumeBandit


def test_sample_returns_valid_arm():
    b = LumeBandit(n_arms=4)
    arm = b.sample("user1")
    assert 0 <= arm < 4


def test_update_changes_posteriors():
    b = LumeBandit(n_arms=4)
    b.update("user1", 2, 0.8)
    # alpha for arm 2 should increase
    assert b.alpha["user1"][2] > 1.0    # started at 1.0
    assert b.beta_["user1"][2] > 1.0    # 1.0 + (1-0.8) = 1.2


def test_update_continuous_beta():
    b = LumeBandit(n_arms=4)
    b.update("u", 0, 0.75)
    assert b.alpha["u"][0] == pytest.approx(1.75)
    assert b.beta_["u"][0] == pytest.approx(1.25)


def test_seed_demo_user_reproducible(monkeypatch):
    monkeypatch.setenv("DEMO_USER_ID", "demo")
    b = LumeBandit(n_arms=16)
    b.seed_demo_user(42)
    s1 = b.sample("demo")
    # Reseed and sample again — should get same first draw
    b.seed_demo_user(42)
    s2 = b.sample("demo")
    assert s1 == s2


def test_convergence_4arms():
    """After 200 pulls on 4 arms with means [0.3, 0.5, 0.7, 0.9],
    arm-3 posterior mean should exceed 0.85 (§A.7)."""
    rng = np.random.default_rng(42)
    arm_means = [0.3, 0.5, 0.7, 0.9]
    b = LumeBandit(n_arms=4)
    b._rngs["test"] = np.random.default_rng(123)

    for _ in range(200):
        arm = b.sample("test")
        # Bernoulli reward
        reward = float(rng.random() < arm_means[arm])
        b.update("test", arm, reward)

    means = b.posterior_mean("test")
    assert means[3] > 0.85, f"arm-3 posterior mean {means[3]:.3f} should be > 0.85"


def test_rebuild_from_events(tmp_path, monkeypatch):
    """rebuild_from_events replays DB rows to restore posteriors."""
    import sqlite3
    from pathlib import Path
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    db_file = tmp_path / "test_rebuild.db"
    monkeypatch.setenv("LUME_DB_PATH", str(db_file))

    conn = sqlite3.connect(str(db_file))
    conn.executescript(schema_path.read_text())
    conn.commit()

    # Insert 3 events: arm 0 with rewards 0.8, 0.6; arm 2 with reward 0.3
    import json
    import time
    now = int(time.time() * 1000)
    from app.ml.arms import ARMS
    cfg_json = json.dumps(ARMS[0])
    feats_json = json.dumps({"avg_word_len": 4.5, "syllable_density": 1.3,
                              "freq_percentile_mean": 0.5, "sentence_count": 5, "flesch_kincaid": 8.0})
    rows = [
        ("u1", None, None, "abc", feats_json, cfg_json, 0, "bandit", 0, 55, 200.0, 0.8, "self_rated", None, None, 0.8, "demo", now),
        ("u1", None, None, "abc", feats_json, cfg_json, 0, "bandit", 0, 55, 190.0, 0.6, "self_rated", None, None, 0.6, "demo", now+1),
        ("u1", None, None, "abc", feats_json, json.dumps(ARMS[2]), 2, "bandit", 0, 55, 100.0, 0.3, "self_rated", None, None, 0.3, "demo", now+2),
    ]
    conn.executemany(
        """INSERT INTO events
           (user_id, render_id, text_id, text_hash, features_json, adaptation_config_json,
            arm_index, recommendation_source, was_user_modified, word_count,
            wpm, comprehension_score, comprehension_type, self_rating, mcq_correct,
            reward, data_source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()

    b = LumeBandit(n_arms=16)
    b.rebuild_from_events(conn)
    conn.close()

    # arm 0: alpha = 1 + 0.8 + 0.6 = 2.4; beta = 1 + 0.2 + 0.4 = 1.6
    assert b.alpha["u1"][0] == pytest.approx(2.4)
    assert b.beta_["u1"][0] == pytest.approx(1.6)
    # arm 2: alpha = 1 + 0.3 = 1.3
    assert b.alpha["u1"][2] == pytest.approx(1.3)
