"""Tests for reward.py (Phase 2.0)."""
import math

import pytest

from app.ml.reward import WPM_CEIL, WPM_FLOOR, blend_comprehension, compute_reward, normalize_wpm


def test_normalize_wpm_at_floor():
    assert normalize_wpm(WPM_FLOOR) == pytest.approx(0.0)


def test_normalize_wpm_at_ceil():
    assert normalize_wpm(WPM_CEIL) == pytest.approx(1.0)


def test_normalize_wpm_below_floor():
    assert normalize_wpm(WPM_FLOOR - 10) == pytest.approx(0.0)


def test_normalize_wpm_above_ceil():
    assert normalize_wpm(WPM_CEIL + 50) == pytest.approx(1.0)


def test_reward_perfect():
    r = compute_reward(WPM_CEIL, 1.0)
    assert r == pytest.approx(1.0)


def test_reward_zero():
    r = compute_reward(WPM_FLOOR - 1, 0.0)
    assert r == pytest.approx(0.0)


def test_reward_formula():
    wpm = 175.0  # normalize_wpm = (175-50)/(300-50) = 125/250 = 0.5
    comp = 0.8
    expected = min(max(0.7 * 0.5 + 0.3 * 0.8, 0.0), 1.0)
    assert compute_reward(wpm, comp) == pytest.approx(expected, abs=0.001)


def test_self_rated_comprehension_conversion():
    """(rating - 1) / 4 maps 1→0.0 and 5→1.0."""
    assert (1 - 1) / 4 == 0.0
    assert (5 - 1) / 4 == 1.0
    assert (3 - 1) / 4 == pytest.approx(0.5)


def test_reward_clipped_to_unit_interval():
    r = compute_reward(1000.0, 2.0)  # both out of range
    assert 0.0 <= r <= 1.0


# ── blend_comprehension tests ─────────────────────────────────────────────────

def test_blend_both_signals():
    """MCQ correct + rating 5 → perfect blend."""
    assert blend_comprehension(5, True) == pytest.approx(1.0)


def test_blend_mcq_only_correct():
    assert blend_comprehension(None, True) == pytest.approx(1.0)


def test_blend_mcq_only_wrong():
    assert blend_comprehension(None, False) == pytest.approx(0.0)


def test_blend_rating_only_min():
    assert blend_comprehension(1, None) == pytest.approx(0.0)


def test_blend_rating_only_max():
    assert blend_comprehension(5, None) == pytest.approx(1.0)


def test_blend_rating_only_mid():
    # rating 3 → (3-1)/4 = 0.5
    assert blend_comprehension(3, None) == pytest.approx(0.5)


def test_blend_neither_returns_zero():
    """Safe fallback when no signal is provided."""
    assert blend_comprehension(None, None) == pytest.approx(0.0)


def test_blend_mixed_signals():
    """rating 3 (→0.5) + mcq wrong (→0.0) → average 0.25."""
    assert blend_comprehension(3, False) == pytest.approx(0.25)


def test_blend_output_in_unit_interval():
    for rating in range(1, 6):
        for correct in (True, False, None):
            score = blend_comprehension(rating, correct)
            assert 0.0 <= score <= 1.0, f"Out of range for rating={rating}, correct={correct}"


# ── NaN / non-finite guard tests ─────────────────────────────────────────────

def test_compute_reward_nan_wpm_returns_zero():
    """Non-finite WPM must not propagate NaN into the bandit."""
    assert compute_reward(float("nan"), 0.5) == pytest.approx(0.0)


def test_compute_reward_inf_wpm_returns_zero():
    assert compute_reward(float("inf"), 0.5) == pytest.approx(0.0)


def test_compute_reward_neg_inf_wpm_returns_zero():
    assert compute_reward(float("-inf"), 0.5) == pytest.approx(0.0)


def test_compute_reward_nan_comprehension_returns_zero():
    assert compute_reward(175.0, float("nan")) == pytest.approx(0.0)


def test_compute_reward_both_nan_returns_zero():
    assert compute_reward(float("nan"), float("nan")) == pytest.approx(0.0)


def test_compute_reward_output_always_finite():
    """Smoke test: any finite inputs must produce a finite output in [0, 1]."""
    for wpm in (0.0, 50.0, 175.0, 300.0, 500.0):
        for comp in (0.0, 0.25, 0.5, 0.75, 1.0):
            r = compute_reward(wpm, comp)
            assert math.isfinite(r), f"Non-finite output for wpm={wpm}, comp={comp}"
            assert 0.0 <= r <= 1.0
