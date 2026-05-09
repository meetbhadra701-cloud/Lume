"""Tests for app.data_structures.trie (Phase 1.1)."""

from app.data_structures.trie import Trie


def test_insert_and_lookup():
    t = Trie()
    t.insert("hello", 5)
    assert t.lookup("hello")
    assert "hello" in t
    assert not t.lookup("world")


def test_freq_rank_exact():
    t = Trie()
    t.insert("the", 1)
    t.insert("dyslexia", 9999)
    assert t.freq_rank("the") == 1
    assert t.freq_rank("dyslexia") == 9999


def test_freq_rank_missing():
    t = Trie()
    t.insert("hello", 1)
    assert t.freq_rank("missing") is None


def test_case_insensitive():
    t = Trie()
    t.insert("HELLO", 42)
    assert t.lookup("hello")
    assert t.freq_rank("Hello") == 42


def test_len():
    t = Trie()
    assert len(t) == 0
    t.insert("a", 1)
    t.insert("b", 2)
    t.insert("a", 3)   # re-insert same word
    assert len(t) == 2


def test_large_vocab():
    t = Trie()
    words = [f"word{i}" for i in range(1000)]
    for i, w in enumerate(words):
        t.insert(w, i + 1)
    assert len(t) == 1000
    for i, w in enumerate(words):
        assert t.freq_rank(w) == i + 1
