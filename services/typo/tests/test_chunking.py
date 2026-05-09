"""Tests for recursive text chunker (Phase 1.6)."""
import pytest

from app.adaptations.chunking import chunk_text


def test_empty_input():
    assert chunk_text([]) == []


def test_small_input_single_chunk():
    tokens = ["word"] * 10
    chunks = chunk_text(tokens, chunk_size=80)
    assert len(chunks) == 1
    assert chunks[0] == list(range(10))


def test_exact_chunk_size():
    tokens = ["w"] * 80
    chunks = chunk_text(tokens, chunk_size=80)
    assert len(chunks) == 1


def test_split_into_multiple_chunks():
    tokens = ["w"] * 200
    chunks = chunk_text(tokens, chunk_size=80)
    assert all(len(c) <= 80 for c in chunks)
    assert sum(len(c) for c in chunks) == 200


def test_covers_all_tokens():
    tokens = ["w"] * 157
    chunks = chunk_text(tokens, chunk_size=80)
    all_indices = sorted(idx for chunk in chunks for idx in chunk)
    assert all_indices == list(range(157))


def test_no_duplicates():
    tokens = ["w"] * 200
    chunks = chunk_text(tokens, chunk_size=80)
    flat = [idx for chunk in chunks for idx in chunk]
    assert len(flat) == len(set(flat))


def test_custom_chunk_size():
    tokens = ["w"] * 50
    chunks = chunk_text(tokens, chunk_size=10)
    assert all(len(c) <= 10 for c in chunks)
    assert sum(len(c) for c in chunks) == 50
