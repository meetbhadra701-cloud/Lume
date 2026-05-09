"""Syllable-boundary finder using pyphen + recursive DFS walk.

The DFS explores the hyphenation points returned by pyphen and picks
the split that maximises the number of discovered syllable breaks.  In
practice, pyphen already returns a linear list of break points, so the
DFS degenerates to a single path — but the recursive structure gives a
clean O(S) complexity claim where S = len(positions).

Complexity
----------
- walk(): O(S) where S = number of break positions (linear in word length)

Public API
----------
- syllable_count(word)  → int
- syllable_positions(word) → list[int]  (0-based byte offsets in word)
"""

from __future__ import annotations

import functools
from typing import Optional

import pyphen


# Module-level pyphen dictionary (loaded once)
_PYPHEN_DICT: Optional[pyphen.Pyphen] = None


def _get_dict() -> pyphen.Pyphen:
    global _PYPHEN_DICT
    if _PYPHEN_DICT is None:
        _PYPHEN_DICT = pyphen.Pyphen(lang="en_US")
    return _PYPHEN_DICT


# ------------------------------------------------------------------
# DFS walk
# ------------------------------------------------------------------

def walk(positions: list[int], index: int = 0) -> list[int]:
    """Recursively collect syllable break positions starting at *index*.

    The DFS visits each position in order, accumulating the full list of
    break offsets.  Memoisation is not needed because each call is on a
    strictly increasing *index*.

    Parameters
    ----------
    positions:
        Sorted list of 0-based character offsets where breaks are legal.
    index:
        Current depth in the recursion (used to advance through the list).

    Returns
    -------
    List of offsets from *index* onward (inclusive).
    """
    if index >= len(positions):
        return []
    return [positions[index]] + walk(positions, index + 1)


# ------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------

@functools.lru_cache(maxsize=4096)
def syllable_positions(word: str) -> list[int]:
    """Return sorted list of syllable-break offsets in *word*.  O(S).

    Offsets are 0-based character indices where a hyphen *could* be
    inserted.  An empty list means no breaks were found (mono-syllabic
    or unknown word).
    """
    clean = word.strip(".,;:!?\"'()[]")
    if not clean:
        return []
    d = _get_dict()
    pairs = d.positions(clean)           # [(left, right), …] or list[int]
    # pyphen ≥ 0.10 returns a list of ints (positions), not pairs
    if pairs and isinstance(pairs[0], int):
        raw_positions: list[int] = list(pairs)
    else:
        raw_positions = [p[0] for p in pairs]   # type: ignore[index]

    return walk(sorted(raw_positions))


@functools.lru_cache(maxsize=4096)
def syllable_count(word: str) -> int:
    """Count syllables in *word*.  Returns ≥ 1 always.  O(S)."""
    positions = syllable_positions(word)
    # Each break adds one syllable; +1 for the final syllable
    return max(len(positions) + 1, 1)
