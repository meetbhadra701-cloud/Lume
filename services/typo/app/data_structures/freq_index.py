"""Sorted frequency index with O(log V) rank lookup via binary search.

The index maps words → frequency ranks by position in a pre-sorted list
of (word, freq) tuples.  Binary search (`bisect`) finds the rank in
O(log V) where V is vocabulary size.

Used alongside the Trie: the Trie is the O(L) existence check; this
class is the fallback when we want a rank without the trie overhead (and
it also seeds the Trie).

Complexity
----------
- Build       : O(V log V) sort
- rank()      : O(log V) binary search on sorted words list
- percentile(): O(log V)
"""

from __future__ import annotations

import bisect
from typing import Optional


class FreqIndex:
    """Frequency index backed by wordfreq or a supplied word list.

    Parameters
    ----------
    word_freq_pairs:
        Iterable of ``(word, frequency_float)`` ordered by descending
        frequency (most common first).  Ranks are assigned 1-based in
        the order supplied (or, if ``sort=True``, after sorting).
    sort:
        If True, sort *word_freq_pairs* by descending frequency before
        assigning ranks.  Set False when the input is pre-sorted.
    """

    def __init__(
        self,
        word_freq_pairs: list[tuple[str, float]],
        *,
        sort: bool = True,
    ) -> None:
        if sort:
            word_freq_pairs = sorted(word_freq_pairs, key=lambda x: x[1], reverse=True)
        # Parallel arrays for binary search
        self._words: list[str] = []          # sorted alphabetically for bisect
        self._ranks: dict[str, int] = {}     # word → 1-based rank
        self._vocab_size = len(word_freq_pairs)

        for rank_zero, (word, _freq) in enumerate(word_freq_pairs):
            word_lower = word.lower()
            if word_lower not in self._ranks:
                self._ranks[word_lower] = rank_zero + 1  # 1-based

        # Build sorted word list for bisect
        self._words = sorted(self._ranks.keys())

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def rank(self, word: str) -> Optional[int]:
        """Return 1-based frequency rank, or None if word not in index.

        Uses binary search on the sorted word list — O(log V).
        """
        word_lower = word.lower()
        # bisect_left: O(log V)
        pos = bisect.bisect_left(self._words, word_lower)
        if pos < len(self._words) and self._words[pos] == word_lower:
            return self._ranks[word_lower]
        return None

    def percentile(self, word: str) -> Optional[float]:
        """Return frequency percentile in [0, 1] (1 = most common).

        Returns None if the word is unknown.
        """
        r = self.rank(word)
        if r is None or self._vocab_size == 0:
            return None
        # rank 1 → percentile 1.0; rank V → percentile ≈ 0
        return 1.0 - (r - 1) / self._vocab_size

    def is_rare(self, word: str, threshold_percentile: float = 0.5) -> bool:
        """Return True if the word is below *threshold_percentile* or unknown.

        Words at or above the threshold are considered common (not rare).
        Default: words in the top 50% of frequency are not rare.
        """
        p = self.percentile(word)
        if p is None:
            return True   # unknown → treat as rare for emphasis purposes
        return p < threshold_percentile

    @property
    def vocab_size(self) -> int:
        return self._vocab_size
