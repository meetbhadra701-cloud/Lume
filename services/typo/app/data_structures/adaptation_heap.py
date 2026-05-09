"""Min-heap wrapper for top-k arm selection.

Wraps Python's `heapq` module so that callers don't need to reason about
heap invariants.  Used by the inline post-reading panel to surface the
top-k best-performing adaptation arms for a user.

Complexity
----------
- push()  : O(log k) where k = max heap size
- top_k() : O(k log k)  [returns sorted list]
- __len__ : O(1)
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(order=True)
class _HeapEntry:
    """Heap entry ordered by (score, insertion_index) for stability."""
    score: float
    index: int = field(compare=True)
    arm_index: int = field(compare=False)
    config: Any = field(compare=False, default=None)


class AdaptationHeap:
    """Fixed-capacity min-heap returning the top-k highest-scoring arms.

    Parameters
    ----------
    k:
        Maximum number of arms to retain.  The heap always keeps only
        the top-*k* entries by score (min-heap over the *lowest* of
        the top-k, so we can efficiently evict).
    """

    def __init__(self, k: int) -> None:
        if k < 1:
            raise ValueError("k must be ≥ 1")
        self._k = k
        self._heap: list[_HeapEntry] = []
        self._counter = 0             # tie-breaker for stable ordering

    def push(self, arm_index: int, score: float, config: Any = None) -> None:
        """Push an arm-score pair, evicting the lowest if capacity exceeded.

        O(log k)
        """
        entry = _HeapEntry(score=score, index=self._counter, arm_index=arm_index, config=config)
        self._counter += 1

        if len(self._heap) < self._k:
            heapq.heappush(self._heap, entry)
        elif score > self._heap[0].score:
            # Current minimum is worse than the new entry — replace it
            heapq.heapreplace(self._heap, entry)

    def top_k(self) -> list[_HeapEntry]:
        """Return the top-k entries sorted by descending score.

        O(k log k)
        """
        return sorted(self._heap, key=lambda e: e.score, reverse=True)

    def peek_min(self) -> Optional[_HeapEntry]:
        """Return the current minimum entry without removing it.  O(1)."""
        return self._heap[0] if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)

    def __repr__(self) -> str:
        top = self.top_k()
        entries = ", ".join(f"arm={e.arm_index}:{e.score:.3f}" for e in top)
        return f"AdaptationHeap(k={self._k}, [{entries}])"
