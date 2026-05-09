"""Tests for app.data_structures.freq_index (Phase 1.2)."""
import pytest

from app.data_structures.freq_index import FreqIndex


PAIRS = [
    ("the", 0.9),
    ("of", 0.8),
    ("and", 0.75),
    ("dyslexia", 0.001),
    ("typographic", 0.002),
]


def test_rank_common_word():
    fi = FreqIndex(PAIRS)
    assert fi.rank("the") == 1      # highest frequency → rank 1


def test_rank_rare_word():
    fi = FreqIndex(PAIRS)
    assert fi.rank("dyslexia") is not None


def test_rank_missing():
    fi = FreqIndex(PAIRS)
    assert fi.rank("xyzzy_unknown") is None


def test_percentile_order():
    fi = FreqIndex(PAIRS)
    p_common = fi.percentile("the")
    p_rare = fi.percentile("dyslexia")
    assert p_common is not None and p_rare is not None
    assert p_common > p_rare


def test_is_rare_common():
    fi = FreqIndex(PAIRS)
    assert not fi.is_rare("the", threshold_percentile=0.5)


def test_is_rare_rare():
    fi = FreqIndex(PAIRS)
    assert fi.is_rare("dyslexia", threshold_percentile=0.5)


def test_binary_search_correctness():
    """Rank lookup uses binary search — verify it's correct for all words."""
    fi = FreqIndex(PAIRS)
    for word, _ in PAIRS:
        rank = fi.rank(word)
        assert rank is not None, f"{word!r} not found"
        assert 1 <= rank <= len(PAIRS)


def test_case_insensitive():
    fi = FreqIndex([("Hello", 0.5)])
    assert fi.rank("hello") is not None
    assert fi.rank("HELLO") is not None
