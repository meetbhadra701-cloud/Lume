"""Tests for Knuth-Plass-inspired DP hyphenation (Phase 1.4)."""

from app.adaptations.hyphenation import (
    _knuth_plass_breaks,
    apply_hyphenation,
    hyphenate_word,
)

# Unicode soft hyphen
SHY = "­"


def test_hyphenate_short_word():
    # Words < 4 chars pass through unchanged via apply_hyphenation
    result = apply_hyphenation(["a", "is", "the"])
    assert result == ["a", "is", "the"]


def test_hyphenate_long_word_returns_string():
    result = hyphenate_word("adaptation")
    assert isinstance(result, str)
    # The plain text without soft hyphens should equal the original
    assert result.replace(SHY, "") == "adaptation"


def test_breaks_return_tuple():
    breaks = _knuth_plass_breaks("reading")
    assert isinstance(breaks, tuple)


def test_apply_hyphenation_length_preserved():
    tokens = ["reading", "adaptation", "dyslexia", "typography"]
    result = apply_hyphenation(tokens)
    # Number of tokens unchanged
    assert len(result) == len(tokens)
    # Plain text of each token is unchanged
    for orig, hyph in zip(tokens, result):
        assert hyph.replace(SHY, "") == orig


def test_memoisation_consistent():
    # Calling twice returns same result (memoised)
    w = "typographic"
    assert _knuth_plass_breaks(w) == _knuth_plass_breaks(w)
    assert hyphenate_word(w) == hyphenate_word(w)


def test_apply_hyphenation_mixed():
    tokens = ["Hello", "a", "world", "adaptation"]
    result = apply_hyphenation(tokens)
    # Single chars pass through
    assert result[1] == "a"
    # Others are strings
    for r in result:
        assert isinstance(r, str)
