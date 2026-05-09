"""Recursive text chunker (~80-word chunks).

Splits a token list into chunks of at most *chunk_size* tokens using a
recursive divide-and-conquer approach.  The recursion depth is bounded by
⌈log₂(n/chunk_size)⌉, making it O(n log n) overall with depth ≤ log L.

The chunk boundaries returned are used by the frontend to paginate the
passage one chunk at a time.

Complexity
----------
- chunk_text(): O(n log n) with recursion depth ≤ log L

Public API
----------
- chunk_text(tokens, chunk_size) → list[list[int]]
  Each inner list is a sequence of *token indices* that belong to one chunk.
"""

from __future__ import annotations

_DEFAULT_CHUNK_SIZE = 80   # words per chunk


def _chunk_indices(
    indices: list[int],
    chunk_size: int,
) -> list[list[int]]:
    """Recursively split *indices* into groups of ≤ *chunk_size*.

    Recursion depth ≤ log₂(len(indices) / chunk_size).
    """
    if len(indices) <= chunk_size:
        return [indices]

    mid = len(indices) // 2
    left = _chunk_indices(indices[:mid], chunk_size)
    right = _chunk_indices(indices[mid:], chunk_size)
    return left + right


def chunk_text(
    tokens: list[str],
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> list[list[int]]:
    """Split *tokens* into chunks of ≤ *chunk_size* tokens.

    Returns a list of chunks, where each chunk is a list of token indices
    (0-based offsets into *tokens*).  The union of all chunks covers every
    token exactly once.

    Parameters
    ----------
    tokens:
        The flat list of token strings returned by the tokeniser.
    chunk_size:
        Maximum tokens per chunk.  Defaults to 80.

    Examples
    --------
    >>> chunks = chunk_text(["word"] * 200)
    >>> assert all(len(c) <= 80 for c in chunks)
    >>> assert sum(len(c) for c in chunks) == 200
    """
    if not tokens:
        return []
    indices = list(range(len(tokens)))
    return _chunk_indices(indices, chunk_size)
