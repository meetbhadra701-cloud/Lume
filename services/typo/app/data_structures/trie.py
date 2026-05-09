"""Trie data structure for O(L) word lookup and frequency ranking.

Each node stores child pointers and, for terminal nodes, the word's
frequency rank (lower = more common).  Used by highlight.py to drive
the reading-emphasis feature.

Complexity
----------
- Insert  : O(L) where L = word length
- Lookup  : O(L)
- freq_rank: O(L)
"""

from __future__ import annotations

from typing import Optional


class _TrieNode:
    """Single node in the trie."""

    __slots__ = ("children", "freq_rank", "is_terminal")

    def __init__(self) -> None:
        self.children: dict[str, "_TrieNode"] = {}
        self.freq_rank: Optional[int] = None   # set only at terminal nodes
        self.is_terminal: bool = False


class Trie:
    """Character-level trie seeded with (word, freq_rank) pairs.

    Rank convention: 1 = most frequent word, higher = rarer.
    Unknown words return rank None (treated as rare by callers).
    """

    def __init__(self) -> None:
        self._root = _TrieNode()
        self._size: int = 0

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def insert(self, word: str, freq_rank: int) -> None:
        """Insert *word* with *freq_rank*.  O(L)."""
        node = self._root
        for ch in word.lower():
            if ch not in node.children:
                node.children[ch] = _TrieNode()
            node = node.children[ch]
        if not node.is_terminal:
            self._size += 1
        node.is_terminal = True
        node.freq_rank = freq_rank

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def lookup(self, word: str) -> bool:
        """Return True if *word* is in the trie.  O(L)."""
        return self.freq_rank(word) is not None

    def freq_rank(self, word: str) -> Optional[int]:
        """Return the frequency rank of *word*, or None if not found.  O(L).

        A lower rank means the word is more common (1 = most common).
        """
        node = self._root
        for ch in word.lower():
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node.freq_rank if node.is_terminal else None

    def __len__(self) -> int:
        return self._size

    def __contains__(self, word: str) -> bool:
        return self.lookup(word)
