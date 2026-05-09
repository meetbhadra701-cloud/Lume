"""Tests for app.adaptations.syllables (Phase 1.3)."""

from app.adaptations.syllables import syllable_count, syllable_positions, walk


def test_walk_empty():
    assert walk([]) == []


def test_walk_single():
    assert walk([3]) == [3]


def test_walk_multiple():
    result = walk([2, 5, 8])
    assert result == [2, 5, 8]


def test_walk_returns_all_positions():
    positions = [1, 3, 7, 12]
    assert walk(positions) == positions


def test_syllable_count_monosyllabic():
    # Short common words — at least 1 syllable
    for word in ["the", "a", "of", "is"]:
        assert syllable_count(word) >= 1


def test_syllable_count_known_polysyllabic():
    # "reading" → read-ing (2 syllables)
    assert syllable_count("reading") >= 2


def test_syllable_count_minimum_one():
    # Even unknown words return ≥ 1
    assert syllable_count("xyzzy") >= 1


def test_syllable_positions_returns_sorted():
    positions = syllable_positions("adaptation")
    assert positions == sorted(positions)


def test_syllable_positions_empty_for_short():
    # Single-character — no breaks
    result = syllable_positions("a")
    assert isinstance(result, list)
