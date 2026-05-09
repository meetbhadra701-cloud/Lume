"""Tests for reward.py (Phase 2.0)."""
import pytest

from app.ml.reward import WPM_CEIL, WPM_FLOOR, compute_reward, normalize_wpm


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
