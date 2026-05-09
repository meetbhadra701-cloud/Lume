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

from app.api.mode_configs import config_for_mode
from app.ml.reward import compute_reward
from app.schemas import (
    AdaptationConfig,
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


def _stub_features(text: str) -> TextFeatures:
    """Stub text feature extraction (fast — no slow textstat.syllable_count)."""
    import textstat

    words = text.split()
    word_count = len(words)
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)

    try:
        fk = textstat.flesch_kincaid_grade(text)
    except Exception:
        fk = 8.0

    syllables = sum(_count_syllables_fast(w) for w in words)
    avg_word_len = (sum(len(w) for w in words) / max(word_count, 1))
    syllable_density = syllables / max(word_count, 1)

    return TextFeatures(
        avg_word_len=round(avg_word_len, 2),
        syllable_density=round(syllable_density, 2),
        freq_percentile_mean=0.5,   # stub: uniform 50th percentile
        sentence_count=sentences,
        flesch_kincaid=round(fk, 1),
    )


def _tokenise(text: str, cfg: AdaptationConfig) -> tuple[list[Token], list[list[int]]]:
    """Stub tokeniser — returns word tokens with basic emphasis and chunk breaks.

    Phase 1 will replace this with trie/freq_index/hyphenation/chunking.
    """
    words = text.split()
    tokens = []
    chunk_size = 80
    chunks: list[list[int]] = []
    current_chunk_start = 0

    for i, word in enumerate(words):
        # Stub emphasis: emphasize words longer than 7 chars
        is_emphasized = cfg.emphasis_on and len(word) > 7
        class_hints = []
        if is_emphasized:
            class_hints.append("lume-emphasis")

        # Chunk break
        is_chunk_break = cfg.chunked_on and (i > 0) and (i % chunk_size == 0)
        if is_chunk_break:
            chunks.append(list(range(current_chunk_start, i)))
            current_chunk_start = i

        tokens.append(
            Token(
                text=word,
                is_emphasized=is_emphasized,
                class_hints=class_hints,
                is_chunk_break=is_chunk_break,
            )
        )

    # Final chunk
    if len(words) > 0:
        chunks.append(list(range(current_chunk_start, len(words))))
    else:
        chunks = [[]]

    return tokens, chunks


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

        # If lume_tuned and bandit is available, sample
        if req.mode == "lume_tuned":
            try:
                from app.ml.bandit import get_bandit
                from app.ml.arms import ARMS

                bandit = get_bandit()
                arm_idx = bandit.sample(req.user_id)
                arm_cfg_dict = ARMS[arm_idx]
                cfg = AdaptationConfig(**arm_cfg_dict)
                rec_source = "bandit"
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
        features = _stub_features(text)
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
    import time

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

    # Compute reward
    reward = compute_reward(req.wpm, req.comprehension_score)

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
        comprehension_score=req.comprehension_score,
        comprehension_type=req.comprehension_type,
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
