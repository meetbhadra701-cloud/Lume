"""Reward formula — single source of truth (rev. 4 §A.6).

Self-rated comprehension: (rating - 1) / 4 converts 1-5 slider → 0..1.
This should be done by the caller before passing comprehension to compute_reward.
"""

WPM_FLOOR = 50.0
WPM_CEIL = 300.0


def normalize_wpm(wpm: float) -> float:
    return min(max((wpm - WPM_FLOOR) / (WPM_CEIL - WPM_FLOOR), 0.0), 1.0)


def normalize_comprehension(score: float) -> float:  # already 0..1
    return min(max(score, 0.0), 1.0)


def compute_reward(wpm: float, comprehension: float) -> float:
    """Hackathon simplification: single formula, equal-weight mix of WPM + comprehension.

    A production version would calibrate per-user baselines.
    """
    return min(
        max(
            0.7 * normalize_wpm(wpm) + 0.3 * normalize_comprehension(comprehension),
            0.0,
        ),
        1.0,
    )
