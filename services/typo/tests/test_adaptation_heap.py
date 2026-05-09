"""Tests for AdaptationHeap min-heap (Phase 1.5)."""
import pytest

from app.data_structures.adaptation_heap import AdaptationHeap


def test_empty_heap():
    h = AdaptationHeap(k=3)
    assert len(h) == 0
    assert h.peek_min() is None
    assert h.top_k() == []


def test_push_within_capacity():
    h = AdaptationHeap(k=3)
    h.push(0, 0.5)
    h.push(1, 0.7)
    assert len(h) == 2


def test_top_k_sorted_descending():
    h = AdaptationHeap(k=5)
    scores = [0.3, 0.9, 0.5, 0.1, 0.7]
    for i, s in enumerate(scores):
        h.push(i, s)
    top = h.top_k()
    assert len(top) == 5
    # Sorted descending
    for a, b in zip(top, top[1:]):
        assert a.score >= b.score


def test_eviction_keeps_top_k():
    h = AdaptationHeap(k=3)
    h.push(0, 0.1)
    h.push(1, 0.5)
    h.push(2, 0.9)
    h.push(3, 0.3)   # should evict 0.1
    assert len(h) == 3
    scores = {e.score for e in h.top_k()}
    assert 0.1 not in scores
    assert 0.9 in scores


def test_k_equals_one():
    h = AdaptationHeap(k=1)
    h.push(0, 0.3)
    h.push(1, 0.8)
    h.push(2, 0.6)
    top = h.top_k()
    assert len(top) == 1
    assert top[0].score == pytest.approx(0.8)


def test_arm_index_preserved():
    h = AdaptationHeap(k=2)
    h.push(arm_index=5, score=0.7)
    h.push(arm_index=12, score=0.9)
    top = h.top_k()
    assert top[0].arm_index == 12
    assert top[1].arm_index == 5


def test_invalid_k_raises():
    with pytest.raises(ValueError):
        AdaptationHeap(k=0)
