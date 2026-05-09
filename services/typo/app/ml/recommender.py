"""Recommendation routing: bandit vs. Ridge model.

Rules (§A.10, rev. 4 fix 17, §A.29):
  1. If LUME_COLLECT_MODE == 'real_user':
       → uniform-random from 5-arm balanced subset (real_user_arms.py)
  2. Else if n_user_events < 30 OR random() < 0.2:
       → Thompson bandit sample
  3. Else:
       → per-user Ridge model; recommend arm with highest predicted reward
         across all 16 arms.

Manual overrides (was_user_modified rows) are excluded from Ridge training
(test_recommender_excludes_overrides.py; rev. 4 fix 54).

Public API
----------
- recommend(user_id, features, conn) → tuple[AdaptationConfig, int, str]
  Returns (config, arm_index, recommendation_source).
"""

from __future__ import annotations

import os
import random
import sqlite3
from typing import Optional

from app.ml.arms import ARMS
from app.ml.bandit import get_bandit
from app.ml.model import fit_user_model, load_events_for_user
from app.ml.real_user_arms import REAL_USER_ARM_INDICES
from app.schemas import AdaptationConfig, TextFeatures

# Exploration fraction: 20% of the time use bandit even when model is ready
_EXPLORATION_FRACTION = 0.2


def _count_events_for_user(conn: sqlite3.Connection, user_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM events WHERE user_id = ? AND was_user_modified = 0",
        (user_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def recommend(
    user_id: str,
    features: TextFeatures,
    conn: Optional[sqlite3.Connection] = None,
) -> tuple[AdaptationConfig, int, str]:
    """Return the recommended (config, arm_index, recommendation_source).

    Parameters
    ----------
    user_id:
        User to personalise for.
    features:
        TextFeatures extracted from the current passage.
    conn:
        SQLite connection to read event history.  If None, falls back to
        bandit only (no event count check).
    """
    # ── Real-user collection mode: forced uniform-random over 5-arm subset ──
    lume_collect_mode = os.environ.get("LUME_COLLECT_MODE", "")
    if lume_collect_mode == "real_user":
        arm_idx = random.choice(REAL_USER_ARM_INDICES)
        cfg = AdaptationConfig(**ARMS[arm_idx])
        return cfg, arm_idx, "bandit"

    bandit = get_bandit()

    # ── Check event count to gate Ridge fit ─────────────────────────────────
    n_events = 0
    if conn is not None:
        n_events = _count_events_for_user(conn, user_id)

    use_bandit = (n_events < 30) or (random.random() < _EXPLORATION_FRACTION)

    if use_bandit:
        arm_idx = bandit.sample(user_id)
        cfg = AdaptationConfig(**ARMS[arm_idx])
        source = "bandit"
        return cfg, arm_idx, source

    # ── Ridge model path ─────────────────────────────────────────────────────
    if conn is None:
        arm_idx = bandit.sample(user_id)
        cfg = AdaptationConfig(**ARMS[arm_idx])
        return cfg, arm_idx, "bandit"

    events = load_events_for_user(conn, user_id, exclude_user_modified=True)
    model = fit_user_model(user_id, events)

    if model is None:
        # Fit failed (shouldn't happen given n_events ≥ 30, but guard it)
        arm_idx = bandit.sample(user_id)
        cfg = AdaptationConfig(**ARMS[arm_idx])
        return cfg, arm_idx, "bandit"

    # Predict reward for each arm; pick argmax
    best_arm = 0
    best_reward = -float("inf")
    for i, arm_cfg in enumerate(ARMS):
        cfg_candidate = AdaptationConfig(**arm_cfg)
        pred = model.predict(features, cfg_candidate)
        if pred > best_reward:
            best_reward = pred
            best_arm = i

    cfg = AdaptationConfig(**ARMS[best_arm])
    return cfg, best_arm, "model"
