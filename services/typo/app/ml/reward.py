"""Reward formula — single source of truth (rev. 4 §A.6).

When both self_rating and mcq_correct are captured per session, call
blend_comprehension() first to produce a single 0..1 score, then pass
that to compute_reward().  compute_reward() signature is unchanged so that
existing test fixtures and the synthetic seed-event generator continue to
work without modification.
"""
from __future__ import annotations

import math

WPM_FLOOR = 50.0
WPM_CEIL = 300.0


def blend_comprehension(
    self_rating: int | None,
    mcq_correct: bool | None,
) -> float:
    """Blend a 1-5 self-rating and/or a binary MCQ result into a single 0..1 score.

    Each present signal is normalised to [0, 1] and averaged with equal weight:
      - self_rating: (rating - 1) / 4   → 1→0.0, 5→1.0
      - mcq_correct: 1.0 if True else 0.0
    Returns 0.0 if both are None (safe fallback; no signal at all).
    """
    parts: list[float] = []
    if self_rating is not None:
        parts.append((self_rating - 1) / 4.0)
    if mcq_correct is not None:
        parts.append(1.0 if mcq_correct else 0.0)
    return sum(parts) / len(parts) if parts else 0.0


def normalize_wpm(wpm: float) -> float:
    return min(max((wpm - WPM_FLOOR) / (WPM_CEIL - WPM_FLOOR), 0.0), 1.0)


def normalize_comprehension(score: float) -> float:  # already 0..1
    return min(max(score, 0.0), 1.0)


def compute_reward(wpm: float, comprehension: float) -> float:
    """Hackathon simplification: single formula, equal-weight mix of WPM + comprehension.

    A production version would calibrate per-user baselines.
    Returns 0.0 for non-finite inputs to prevent NaN propagation into the bandit.
    """
    if not math.isfinite(wpm) or not math.isfinite(comprehension):
        return 0.0
    return min(
        max(
            0.7 * normalize_wpm(wpm) + 0.3 * normalize_comprehension(comprehension),
            0.0,
        ),
        1.0,
    )
