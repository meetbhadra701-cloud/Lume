"""FastAPI route handlers for Lume API.

/render — read-only; returns RenderResponse + populates render_sessions
/rate   — sole event writer; reads render_sessions for context
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.adaptations.chunking import chunk_text
from app.adaptations.color import get_color_classes
from app.adaptations.highlight import emphasize_tokens
from app.adaptations.hyphenation import hyphenate_word
from app.adaptations.mcq_generator import generate_mcq
from app.adaptations.spacing import get_spacing_classes
from app.api.mode_configs import config_for_mode
from app.data_structures.adaptation_heap import AdaptationHeap
from app.ml.arms import ARMS
from app.ml.reward import blend_comprehension, compute_reward
from app.schemas import (
    AdaptationConfig,
    MCQQuestion,
    MCQRequest,
    RateRequest,
    RateResponse,
    RenderRequest,
    RenderResponse,
    TextFeatures,
    Token,
)
from app.store.db import get_conn, insert_event

router = APIRouter()

# ── Constants ────────────────────────────────────────────────────────────────

DEMO_USER_ID = os.environ.get("DEMO_USER_ID", "demo")
MIN_WORD_COUNT = 50

# ── Process-local in-memory caches ──────────────────────────────────────────
# (not durable — reset on server restart per plan §A.5)

# render_sessions[render_id] = {text_hash, features_json, word_count,
#                                arm_index, adaptation_config, text_id, created_at}
render_sessions: dict[str, dict[str, Any]] = {}

# render_cache[(text_hash, config_hash)] = cached tokenisation result
render_cache: dict[tuple[str, str], dict[str, Any]] = {}


def _config_hash(cfg: AdaptationConfig) -> str:
    """Deterministic hash of an AdaptationConfig for cache keying."""
    canonical = json.dumps(cfg.model_dump(), sort_keys=True)
    return hashlib.sha1(canonical.encode()).hexdigest()


def _text_hash(text: str) -> str:
    """SHA-1 of the normalized text (process-local identifier; not claimed non-reversible)."""
    return hashlib.sha1(text.strip().encode()).hexdigest()


# ── Stub text processing (replaced by real DSAs in Phase 1) ─────────────────

def _count_syllables_fast(word: str) -> int:
    """Fast syllable count heuristic (replaces textstat.syllable_count which is 2.5s/call)."""
    word = word.lower().strip(".,;:!?\"'")
    if not word:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # Silent e at the end
    if word.endswith("e") and len(word) > 2 and word[-2] not in vowels:
        count = max(count - 1, 1)
    return max(count, 1)


def _extract_features(text: str) -> TextFeatures:
    """Extract text features for the feature vector.

    Uses textstat for Flesch-Kincaid (warmed at startup) and the fast
    syllable heuristic for syllable density.  Frequency percentile is
    computed from the shared FreqIndex.  Capped at 1 000 words.
    """
    import textstat

    from app.adaptations.highlight import _get_shared

    words = text.split()
    word_count = len(words)
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)

    try:
        fk = textstat.flesch_kincaid_grade(text)
    except Exception:
        fk = 8.0

    syllables = sum(_count_syllables_fast(w) for w in words[:1000])
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
    syllable_density = syllables / max(min(word_count, 1000), 1)

    # Frequency percentile mean via FreqIndex (cap 1000 tokens)
    try:
        _trie, fi = _get_shared()
        percentiles = [
            p for w in words[:1000]
            if (p := fi.percentile(w)) is not None
        ]
        freq_percentile_mean = sum(percentiles) / len(percentiles) if percentiles else 0.5
    except Exception:
        freq_percentile_mean = 0.5

    return TextFeatures(
        avg_word_len=round(avg_word_len, 2),
        syllable_density=round(syllable_density, 2),
        freq_percentile_mean=round(freq_percentile_mean, 3),
        sentence_count=sentences,
        flesch_kincaid=round(fk, 1),
    )


def _tokenise(text: str, cfg: AdaptationConfig) -> tuple[list[Token], list[list[int]]]:
    """Full DSA-powered tokeniser.

    Uses:
    - highlight.py  → emphasis flag (trie + freq_index, O(W·L))
    - hyphenation.py → soft hyphens via Knuth-Plass DP (O(W·B²))
    - chunking.py   → chunk indices (O(W log W))
    - spacing.py    → letter/word spacing CSS class hints
    - color.py      → warm overlay CSS class hint
    """
    words = text.split()
    if not words:
        return [], [[]]

    # Shared CSS class hints that apply to every token
    global_classes: list[str] = []
    global_classes.extend(get_spacing_classes(cfg.letter_spacing_em, cfg.word_spacing_em))
    global_classes.extend(get_color_classes(cfg.color_overlay_on))
    if cfg.opendyslexic_on:
        global_classes.append("lume-opendyslexic")

    # Emphasis mask: O(W · L) — uses trie + freq_index
    emphasis_mask = emphasize_tokens(words, cap=1000) if cfg.emphasis_on else [False] * len(words)

    # Chunks: O(W log W)
    chunk_groups = chunk_text(words, chunk_size=80) if cfg.chunked_on else [list(range(len(words)))]
    # Build a set of token indices that are chunk-break starts (first token of each chunk after the first)
    chunk_break_indices: set[int] = set()
    if cfg.chunked_on:
        for group in chunk_groups[1:]:
            if group:
                chunk_break_indices.add(group[0])

    tokens: list[Token] = []
    for i, word in enumerate(words):
        # Hyphenation: O(B²) memoised per word
        display_text = hyphenate_word(word) if cfg.hyphenation_on and len(word) >= 4 else word

        is_emph = emphasis_mask[i]
        class_hints = list(global_classes)
        if is_emph:
            class_hints.append("lume-emphasis")

        tokens.append(Token(
            text=display_text,
            is_emphasized=is_emph,
            class_hints=class_hints,
            is_chunk_break=(i in chunk_break_indices),
        ))

    # Return raw chunks (list[list[int]])
    return tokens, chunk_groups


# ── /render ──────────────────────────────────────────────────────────────────

@router.post("/render", response_model=RenderResponse)
async def render(req: RenderRequest) -> RenderResponse:
    """Render text with adaptation config.

    READ-ONLY on the events table (rev. 4 fix 52).
    Populates render_sessions[render_id] for /rate to read.
    """
    import time

    text = req.text.strip()
    th = _text_hash(text)
    words = text.split()
    word_count = len(words)

    # Determine adaptation config
    if req.adaptation_config is not None:
        # User manual override
        cfg = req.adaptation_config
        rec_source = req.recommendation_source or "user_override"
        arm_idx = req.arm_index if req.arm_index is not None else -1
    else:
        # Mode-based (Phase 2 will wire recommender for lume_tuned)
        cfg, rec_source, arm_idx = config_for_mode(req.mode)

        # If lume_tuned, use the full recommender (bandit → model as events grow)
        if req.mode == "lume_tuned":
            try:
                from app.ml.recommender import recommend

                # Extract features first so the recommender can use them
                # (features may not yet be in cache; compute a lightweight version)
                _features_for_rec = _extract_features(text)
                with get_conn() as _conn:
                    cfg, arm_idx, rec_source = recommend(req.user_id, _features_for_rec, _conn)
            except Exception:
                pass  # Fall back to mode_lume_tuned config set above

    # Check render cache
    cfg_hash = _config_hash(cfg)
    cache_key = (th, cfg_hash)
    if cache_key in render_cache:
        cached = render_cache[cache_key]
        tokens = [Token(**t) for t in cached["tokens"]]
        chunks = cached["chunks"]
        features = TextFeatures(**cached["features"])
    else:
        features = _extract_features(text)
        tokens, chunks = _tokenise(text, cfg)
        render_cache[cache_key] = {
            "tokens": [t.model_dump() for t in tokens],
            "chunks": chunks,
            "features": features.model_dump(),
        }

    render_id = str(uuid.uuid4())

    # Populate render_sessions (in-memory, process-local)
    render_sessions[render_id] = {
        "text_hash": th,
        "features_json": features.model_dump(),
        "word_count": word_count,
        "arm_index": arm_idx,
        "adaptation_config": cfg.model_dump(),
        "text_id": req.text_id,
        "created_at": int(time.time() * 1000),
    }

    return RenderResponse(
        render_id=render_id,
        text_hash=th,
        text_id=req.text_id,
        features=features,
        word_count=word_count,
        arm_index=arm_idx,
        adaptation_config=cfg,
        recommendation_source=rec_source,  # type: ignore[arg-type]
        tokens=tokens,
        chunks=chunks,
    )


# ── /rate ────────────────────────────────────────────────────────────────────

@router.post("/rate", response_model=RateResponse)
async def rate(req: RateRequest) -> RateResponse:
    """Log a reading event.

    SOLE WRITER of events table (rev. 4 fix 53).
    Reads render_sessions[render_id] for context; falls back to client-supplied fields.
    """

    # Reconstruct context from render_sessions or fallback
    session = render_sessions.get(req.render_id)
    if session:
        text_hash = session["text_hash"]
        features_json = session["features_json"]
        word_count = session["word_count"]
        text_id = session.get("text_id")
    else:
        # Fallback: client-supplied fields (e.g., dev hot-reload cleared sessions)
        text_hash = req.text_hash
        features_json = req.features_json
        word_count = req.word_count
        text_id = req.text_id

    # Validate word_count
    if word_count is None or word_count < MIN_WORD_COUNT:
        return RateResponse(
            ok=False,
            event_id=-1,
            reward=0.0,
            next_recommendation=None,
        )

    # Validate required fallback fields
    if not text_hash or features_json is None:
        raise HTTPException(
            status_code=400,
            detail="render_id not found and fallback fields missing",
        )

    # Infer data_source server-side (rev. 4 fix 51)
    lume_collect_mode = os.environ.get("LUME_COLLECT_MODE", "")
    if lume_collect_mode == "real_user":
        data_source = "real_user"
    else:
        data_source = "demo"

    # Blend comprehension signals server-side
    if req.self_rating is not None or req.mcq_correct is not None:
        comprehension = blend_comprehension(req.self_rating, req.mcq_correct)
    else:
        # Legacy / single-signal path: caller supplied comprehension_score directly
        comprehension = req.comprehension_score if req.comprehension_score is not None else 0.0

    # Compute reward
    reward = compute_reward(req.wpm, comprehension)

    # Build event record
    event = dict(
        user_id=req.user_id,
        render_id=req.render_id,
        text_id=text_id,
        text_hash=text_hash,
        features_json=features_json,
        adaptation_config_json=req.adaptation_config.model_dump(),
        arm_index=req.arm_index,
        recommendation_source=req.recommendation_source,
        was_user_modified=req.was_user_modified,
        word_count=word_count,
        wpm=req.wpm,
        comprehension_score=comprehension,
        comprehension_type=req.comprehension_type,
        self_rating=req.self_rating,
        mcq_correct=req.mcq_correct,
        reward=reward,
        data_source=data_source,
    )

    with get_conn() as conn:
        event_id = insert_event(conn, event)

    # Update bandit posteriors if arm was used
    if req.arm_index >= 0 and not req.was_user_modified:
        try:
            from app.ml.bandit import get_bandit
            bandit = get_bandit()
            bandit.update(req.user_id, req.arm_index, reward)
        except Exception:
            pass

    return RateResponse(
        ok=True,
        event_id=event_id,
        reward=round(reward, 3),
        next_recommendation=None,  # Phase 2 wires the recommender here
    )


# ── /top-arms ─────────────────────────────────────────────────────────────────

@router.get("/top-arms/{user_id}")
async def top_arms(user_id: str, k: int = 3) -> dict:
    """Return the top-k performing arm configs for a user (uses AdaptationHeap DSA).

    Reads events from the DB, accumulates mean reward per arm via AdaptationHeap,
    and returns the top-k arms sorted by descending mean reward.
    """
    k = max(1, min(k, 16))
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT arm_index, AVG(reward) as mean_reward, COUNT(*) as n_events
            FROM events
            WHERE user_id = ? AND arm_index >= 0 AND was_user_modified = 0
            GROUP BY arm_index
            """,
            (user_id,),
        ).fetchall()

    heap = AdaptationHeap(k=k)
    for arm_index, mean_reward, n_events in rows:
        if arm_index < len(ARMS):
            heap.push(arm_index, mean_reward, config=ARMS[arm_index])

    top = heap.top_k()
    result = []
    for entry in top:
        arm_cfg = ARMS[entry.arm_index] if entry.arm_index < len(ARMS) else {}
        # Build a human-readable label from the arm config
        features = []
        if arm_cfg.get("letter_spacing_em", 0) > 0:
            features.append("Letter spacing")
        if arm_cfg.get("word_spacing_em", 0) > 0:
            features.append("Word spacing")
        if arm_cfg.get("hyphenation_on"):
            features.append("Hyphenation")
        if arm_cfg.get("emphasis_on"):
            features.append("Emphasis")
        if arm_cfg.get("color_overlay_on"):
            features.append("Warm overlay")
        if arm_cfg.get("chunked_on"):
            features.append("Chunked")
        if arm_cfg.get("opendyslexic_on"):
            features.append("OpenDyslexic")
        label = ", ".join(features) if features else "Default"
        result.append({
            "arm_index": entry.arm_index,
            "mean_reward": round(entry.score, 3),
            "label": label,
        })

    return {"user_id": user_id, "top_arms": result}


# ── /generate-mcq ─────────────────────────────────────────────────────────────

@router.post("/generate-mcq", response_model=MCQQuestion)
async def generate_mcq_endpoint(req: MCQRequest) -> MCQQuestion:
    """Generate a single MCQ from the passage text the user just read.

    Edge-case guarantee: the MCQ is derived exclusively from `req.text`.
    For known seed passages (matched by `req.text_id`), a pre-defined
    question is returned — ensuring the question is always about that
    exact passage regardless of the algorithmic path.
    """
    result = generate_mcq(req.text, text_id=req.text_id)
    return MCQQuestion(**result)
