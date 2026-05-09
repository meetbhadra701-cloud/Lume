"""Knuth-Plass-inspired DP for optimal hyphenation break selection.

We use dynamic programming to choose which break points to realise as
soft hyphens, minimising a cost function that penalises very short
syllable segments.  pyphen provides the legal candidate positions;
the DP picks the optimal subset.

Complexity
----------
- _knuth_plass_breaks(): O(B²) where B = number of candidate break
  positions, with per-word memoisation for repeated words.
- apply_hyphenation():   O(W · B²) where W = tokens in text.

References
----------
Knuth & Plass (1981). "Breaking paragraphs into lines."
We apply the badness metric at the word level only (not the paragraph
level) and therefore call the algorithm "Knuth-Plass-inspired."
"""

from __future__ import annotations

import functools
from typing import Optional

from app.adaptations.syllables import syllable_positions

# Unicode soft hyphen
_SHY = "­"

# Minimum segment length (chars) before/after a chosen break
_MIN_SEGMENT = 2

# Badness penalty for segments shorter than _MIN_SEGMENT
_SHORT_PENALTY = 1_000


# ------------------------------------------------------------------
# DP core
# ------------------------------------------------------------------

@functools.lru_cache(maxsize=4096)
def _knuth_plass_breaks(word: str) -> tuple[int, ...]:
    """Return the optimal set of break positions for *word*.

    Uses DP: dp[i] = minimum cost of hyphenating word[:positions[i]].
    The last position implicitly ends at the word boundary.

    Complexity: O(B²) where B = |positions|, memoised per word.

    Returns a (possibly empty) tuple of 0-based character offsets.
    """
    positions = syllable_positions(word)
    if not positions:
        return ()

    n = len(positions)
    # sentinel: end of word
    full = list(positions) + [len(word)]

    # dp[i] = (min_cost, best_prev_index)
    INF = float("inf")
    dp_cost: list[float] = [INF] * (n + 1)
    dp_prev: list[int] = [-1] * (n + 1)
    dp_cost[0] = 0.0

    for i in range(1, n + 1):
        seg_end = full[i - 1]          # character index of this break
        for j in range(i):
            seg_start = full[j - 1] if j > 0 else 0
            seg_len = seg_end - seg_start
            # Badness: penalise short segments
            cost = _SHORT_PENALTY if seg_len < _MIN_SEGMENT else 0.0
            candidate = dp_cost[j] + cost
            if candidate < dp_cost[i]:
                dp_cost[i] = candidate
                dp_prev[i] = j

    # Back-track from position n
    chosen: list[int] = []
    cur = n
    while cur > 0:
        prev = dp_prev[cur]
        if prev < cur - 1 or cur == n:
            # Include break at full[cur - 1] unless it's the word end
            if cur < n:
                chosen.append(full[cur - 1])
        cur = prev
        if cur == 0:
            break

    return tuple(sorted(chosen))


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def hyphenate_word(word: str) -> str:
    """Insert soft hyphens at DP-selected positions in *word*.

    The display is identical to the original — soft hyphens are invisible
    until the browser decides to wrap.

    Parameters
    ----------
    word:
        A single token (may contain punctuation; stripped internally).
    """
    breaks = _knuth_plass_breaks(word)
    if not breaks:
        return word
    parts: list[str] = []
    prev = 0
    for pos in breaks:
        parts.append(word[prev:pos])
        parts.append(_SHY)
        prev = pos
    parts.append(word[prev:])
    return "".join(parts)


def apply_hyphenation(tokens: list[str]) -> list[str]:
    """Apply hyphenation to a list of token strings.  O(W · B²).

    Returns a new list with soft hyphens inserted.  Tokens that are
    already single characters or are punctuation-only are left unchanged.
    """
    return [hyphenate_word(t) if len(t) >= 4 else t for t in tokens]
