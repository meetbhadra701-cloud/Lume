"""Reading-emphasis: frequency-aware word highlighting.

Wires together the Trie (O(L) lookup) and FreqIndex (O(log V) rank) to
decide which tokens are "infrequent" and should receive the emphasis flag.

An *infrequent* word (one below `EMPHASIS_PERCENTILE_THRESHOLD`) gets
`Token.is_emphasized = True` and gains the "lume-emphasis" CSS class hint.
Common stop-words are excluded from emphasis to avoid visual noise.

The two-tier design is intentional:
  1. Trie provides O(L) lookup for exact-match words already indexed.
  2. FreqIndex provides O(log V) fallback for words present in wordfreq
     but not yet in the Trie, or for adjustable percentile thresholds.

Complexity
----------
- build_freq_resources(): O(V log V) once at startup
- is_emphasis_word():     O(L) Trie lookup or O(log V) FreqIndex fallback
- emphasize_tokens():     O(W · L) where W = number of tokens

Public API
----------
- build_freq_resources(vocab_size) → tuple[Trie, FreqIndex]
- is_emphasis_word(word, trie, freq_index) → bool
- emphasize_tokens(tokens, trie, freq_index) → list[bool]
"""

from __future__ import annotations

import re
from typing import Optional

from app.data_structures.freq_index import FreqIndex
from app.data_structures.trie import Trie

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------

# Tokens below this frequency percentile are candidates for emphasis.
# 0.5 → bottom 50% by frequency (i.e. the less-common half).
EMPHASIS_PERCENTILE_THRESHOLD = 0.5

# Words shorter than this are never emphasised (articles, preps, etc.)
MIN_WORD_LEN_FOR_EMPHASIS = 4

# Lazy-loaded shared resources (built once per process)
_SHARED_TRIE: Optional[Trie] = None
_SHARED_FREQ_INDEX: Optional[FreqIndex] = None

# Only load at most this many words from wordfreq (top by frequency)
_MAX_VOCAB = 50_000


def _strip_punct(word: str) -> str:
    """Remove leading/trailing punctuation for lookup."""
    return re.sub(r"^[^\w]+|[^\w]+$", "", word)


# ---------------------------------------------------------------
# Resource builders
# ---------------------------------------------------------------

def build_freq_resources(vocab_size: int = _MAX_VOCAB) -> tuple[Trie, FreqIndex]:
    """Build (Trie, FreqIndex) from wordfreq.  O(V log V).

    Called once at startup.  Results are cached in module-level singletons.

    Parameters
    ----------
    vocab_size:
        Maximum number of words to load from wordfreq.
    """
    global _SHARED_TRIE, _SHARED_FREQ_INDEX

    try:
        from wordfreq import top_n_list  # type: ignore[import]
        words = top_n_list("en", vocab_size)
    except Exception:
        words = []   # graceful degrade: no frequency data

    pairs: list[tuple[str, float]] = [(w, vocab_size - i) for i, w in enumerate(words)]

    trie = Trie()
    for rank_one, (word, _) in enumerate(pairs, start=1):
        trie.insert(word, rank_one)

    freq_index = FreqIndex(pairs, sort=False)  # already rank-ordered

    _SHARED_TRIE = trie
    _SHARED_FREQ_INDEX = freq_index
    return trie, freq_index


def _get_shared() -> tuple[Trie, FreqIndex]:
    """Return module-level resources, building them if not yet ready."""
    global _SHARED_TRIE, _SHARED_FREQ_INDEX
    if _SHARED_TRIE is None or _SHARED_FREQ_INDEX is None:
        build_freq_resources()
    return _SHARED_TRIE, _SHARED_FREQ_INDEX  # type: ignore[return-value]


# ---------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------

def is_emphasis_word(
    word: str,
    trie: Optional[Trie] = None,
    freq_index: Optional[FreqIndex] = None,
) -> bool:
    """Return True if *word* should be emphasised.

    Uses trie (O(L)) first; falls back to freq_index (O(log V)) if the
    trie has no result.

    Parameters
    ----------
    word:
        Raw token string (may contain punctuation).
    trie, freq_index:
        Pre-built resources.  If None, uses the module-level singletons.
    """
    if trie is None or freq_index is None:
        trie, freq_index = _get_shared()

    clean = _strip_punct(word)
    if len(clean) < MIN_WORD_LEN_FOR_EMPHASIS:
        return False

    # Trie: O(L)
    rank = trie.freq_rank(clean)
    if rank is not None:
        percentile = 1.0 - (rank - 1) / max(len(trie), 1)
        return percentile < EMPHASIS_PERCENTILE_THRESHOLD

    # FreqIndex fallback: O(log V)
    return freq_index.is_rare(clean, threshold_percentile=EMPHASIS_PERCENTILE_THRESHOLD)


def emphasize_tokens(
    tokens: list[str],
    trie: Optional[Trie] = None,
    freq_index: Optional[FreqIndex] = None,
    *,
    cap: int = 1000,
) -> list[bool]:
    """Return a bool mask: True where the token should be emphasised.

    Parameters
    ----------
    tokens:
        The token strings to classify.
    trie, freq_index:
        Pre-built resources; None → module singletons.
    cap:
        Only perform frequency analysis on the first *cap* tokens;
        tokens beyond this index are never emphasised (perf guard).

    Complexity: O(W · L) where W = min(len(tokens), cap).
    """
    if trie is None or freq_index is None:
        trie, freq_index = _get_shared()

    result: list[bool] = []
    for i, tok in enumerate(tokens):
        if i >= cap:
            result.append(False)
        else:
            result.append(is_emphasis_word(tok, trie, freq_index))
    return result
