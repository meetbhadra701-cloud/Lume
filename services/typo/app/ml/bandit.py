"""Thompson-sampling bandit over 16 arms (stub — full implementation in Phase 2.2).

Continuous Beta(alpha, beta) posteriors.
Update: alpha += reward; beta += 1.0 - reward.
"""
from __future__ import annotations

import math
import sqlite3
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

# Singleton instance
_bandit_instance: "LumeBandit | None" = None


def get_bandit() -> "LumeBandit":
    global _bandit_instance
    if _bandit_instance is None:
        _bandit_instance = LumeBandit(n_arms=16)
    return _bandit_instance


class LumeBandit:
    """Thompson-sampling bandit with continuous Beta update.

    Demo RNG seeded once per process via seed_demo_user(42).
    Per-user np.random.Generator instances stored in self._rngs[user_id].
    Posteriors rebuilt from events table on startup (not persisted).
    """

    def __init__(self, n_arms: int = 16) -> None:
        self.n_arms = n_arms
        # Beta posteriors: alpha, beta start at 1 (uniform prior)
        self.alpha: dict[str, np.ndarray] = {}
        self.beta_: dict[str, np.ndarray] = {}
        self._rngs: dict[str, np.random.Generator] = {}

    def _ensure_user(self, user_id: str) -> None:
        if user_id not in self.alpha:
            self.alpha[user_id] = np.ones(self.n_arms, dtype=float)
            self.beta_[user_id] = np.ones(self.n_arms, dtype=float)
            self._rngs[user_id] = np.random.default_rng()

    def seed_demo_user(self, seed: int = 42) -> None:
        """Seed the DEMO_USER_ID RNG once per process (rev. 4 fix 18)."""
        import os
        demo_user = os.environ.get("DEMO_USER_ID", "demo")
        self._ensure_user(demo_user)
        self._rngs[demo_user] = np.random.default_rng(seed)

    def sample(self, user_id: str) -> int:
        """Thompson sample: return arm with highest sampled reward."""
        self._ensure_user(user_id)
        rng = self._rngs[user_id]
        samples = rng.beta(self.alpha[user_id], self.beta_[user_id])
        return int(np.argmax(samples))

    def update(self, user_id: str, arm: int, reward: float) -> None:
        """Continuous Beta update (rev. 4 §A.7).

        Discards non-finite rewards silently to prevent NaN from corrupting posteriors.
        Clamps reward to [0, 1] to keep Beta parameters valid.
        """
        if not math.isfinite(reward):
            return
        reward = max(0.0, min(1.0, reward))
        self._ensure_user(user_id)
        self.alpha[user_id][arm] += reward
        self.beta_[user_id][arm] += 1.0 - reward

    def rebuild_from_events(self, conn: sqlite3.Connection) -> None:
        """Replay events table to restore posteriors after server restart.

        Per user_id, in created_at order, re-applies update() for each row
        with arm_index >= 0 (rev. 4 fix 19).
        """
        rows = conn.execute(
            """
            SELECT user_id, arm_index, reward
            FROM events
            WHERE arm_index >= 0
            ORDER BY created_at ASC
            """
        ).fetchall()
        for row in rows:
            user_id, arm_index, reward = row[0], row[1], row[2]
            self.update(user_id, arm_index, float(reward))

    def posterior_mean(self, user_id: str) -> np.ndarray:
        """Return posterior mean for each arm."""
        self._ensure_user(user_id)
        return self.alpha[user_id] / (self.alpha[user_id] + self.beta_[user_id])
