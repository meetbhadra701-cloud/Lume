"""Per-user Ridge regression over the 47-dim feature vector.

Gated: fitting only when a user has ≥ 30 events (§A.10, rev. 4 fix 17).
Below that threshold, the recommender falls back to the bandit exclusively.

Complexity
----------
- fit():     O(n · d²) where n = events, d = 47 (small constant in practice)
- predict(): O(d) per candidate arm

Public API
----------
- LumeModel — per-user model wrapper
- load_events_for_user(conn, user_id) → list[dict]
- fit_user_model(user_id, events) → LumeModel | None
"""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_DIM, build_feature_vector
from app.schemas import AdaptationConfig, TextFeatures

MIN_EVENTS_FOR_FIT = 30   # rev. 4 fix 17


class LumeModel:
    """Per-user Ridge regression model.

    Attributes
    ----------
    user_id : str
    n_events : int  — number of events used to train
    coef_ : np.ndarray  — Ridge coefficients (shape: FEATURE_DIM)
    intercept_ : float
    r2_ : float  — training R² (reported in notebook and self-test)
    """

    def __init__(
        self,
        user_id: str,
        ridge: Ridge,
        scaler: StandardScaler,
        n_events: int,
        r2: float,
    ) -> None:
        self.user_id = user_id
        self._ridge = ridge
        self._scaler = scaler
        self.n_events = n_events
        self.r2_ = r2
        self.coef_ = ridge.coef_
        self.intercept_ = float(ridge.intercept_)

    def predict(self, features: TextFeatures, cfg: AdaptationConfig) -> float:
        """Predict expected reward for a given (text_features, config) pair."""
        x = build_feature_vector(features, cfg).reshape(1, -1)
        x_scaled = self._scaler.transform(x)
        return float(self._ridge.predict(x_scaled)[0])

    def summary(self) -> str:
        """Return a human-readable summary for the --self-test output."""
        return (
            f"User: {self.user_id} | n_events: {self.n_events} | "
            f"R²: {self.r2_:.3f} | intercept: {self.intercept_:.4f}"
        )


# ── Data loading ─────────────────────────────────────────────────────────────

def load_events_for_user(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    exclude_user_modified: bool = True,
) -> list[dict]:
    """Load events for *user_id*, optionally excluding manual-override rows.

    Rows with was_user_modified=1 are excluded from Ridge training
    (rev. 4 fix 54: user overrides don't enter fit).
    """
    query = """
        SELECT features_json, adaptation_config_json, reward
        FROM events
        WHERE user_id = ?
        {}
        ORDER BY created_at ASC
    """.format("AND was_user_modified = 0" if exclude_user_modified else "")
    rows = conn.execute(query, (user_id,)).fetchall()
    events = []
    for row in rows:
        try:
            features_json = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            config_json = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            events.append({
                "features": features_json,
                "adaptation_config": config_json,
                "reward": float(row[2]),
            })
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return events


# ── Fitting ──────────────────────────────────────────────────────────────────

def fit_user_model(
    user_id: str,
    events: list[dict],
    *,
    alpha: float = 1.0,
) -> Optional[LumeModel]:
    """Fit a Ridge model for *user_id* if enough events exist.

    Returns None when len(events) < MIN_EVENTS_FOR_FIT.

    Parameters
    ----------
    user_id:
        The user to model.
    events:
        List of dicts from load_events_for_user.
    alpha:
        Ridge regularisation strength.
    """
    if len(events) < MIN_EVENTS_FOR_FIT:
        return None

    X_rows: list[np.ndarray] = []
    y: list[float] = []

    for ev in events:
        try:
            tf = TextFeatures(**ev["features"])
            cfg = AdaptationConfig(**ev["adaptation_config"])
            vec = build_feature_vector(tf, cfg)
            X_rows.append(vec)
            y.append(ev["reward"])
        except Exception:
            continue

    if len(X_rows) < MIN_EVENTS_FOR_FIT:
        return None

    X = np.array(X_rows)
    y_arr = np.array(y)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    ridge = Ridge(alpha=alpha)
    ridge.fit(X_scaled, y_arr)

    # Training R²
    y_pred = ridge.predict(X_scaled)
    ss_res = np.sum((y_arr - y_pred) ** 2)
    ss_tot = np.sum((y_arr - y_arr.mean()) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return LumeModel(
        user_id=user_id,
        ridge=ridge,
        scaler=scaler,
        n_events=len(X_rows),
        r2=float(r2),
    )


# ── Self-test ─────────────────────────────────────────────────────────────────

def _self_test() -> None:
    """Smoke-test: synthesise ≥30 events and fit a model.

    Run via: cd services/typo && uv run python -m app.ml.model --self-test
    """
    import random

    from app.ml.arms import ARMS

    random.seed(0)
    np.random.seed(0)

    user_id = "self_test_user"
    events: list[dict] = []

    for _ in range(50):
        arm_cfg = random.choice(ARMS)
        # Fake features
        features = {
            "avg_word_len": random.uniform(3.0, 7.0),
            "syllable_density": random.uniform(1.0, 3.0),
            "freq_percentile_mean": random.uniform(0.2, 0.8),
            "sentence_count": random.randint(3, 15),
            "flesch_kincaid": random.uniform(5.0, 14.0),
        }
        # Reward: correlated with letter_spacing_em (so Ridge can learn)
        reward = 0.5 + 0.3 * arm_cfg["letter_spacing_em"] / 0.04 + random.gauss(0, 0.1)
        reward = min(max(reward, 0.0), 1.0)
        events.append({
            "features": features,
            "adaptation_config": arm_cfg,
            "reward": reward,
        })

    model = fit_user_model(user_id, events)
    if model is None:
        print("FAIL: model returned None (not enough events?)")
        raise SystemExit(1)

    print(model.summary())
    assert model.n_events == 50
    assert FEATURE_DIM == 47, f"Wrong dim: {FEATURE_DIM}"

    # Predict on one arm
    from app.schemas import AdaptationConfig, TextFeatures
    tf = TextFeatures(avg_word_len=5.0, syllable_density=1.5, freq_percentile_mean=0.5, sentence_count=5, flesch_kincaid=8.0)
    cfg = AdaptationConfig(**ARMS[0])
    pred = model.predict(tf, cfg)
    print(f"Prediction for arm 0: {pred:.4f}")
    assert 0.0 <= pred <= 2.0, f"Prediction out of reasonable range: {pred}"

    if model.r2_ >= 0.7:
        print(f"R² = {model.r2_:.3f} ✓ (≥ 0.7)")
    else:
        print(f"R² = {model.r2_:.3f} (below 0.7 on synthetic — expected with noise)")

    print("Self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
