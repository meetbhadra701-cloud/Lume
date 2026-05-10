"""Pydantic schemas for Lume API (locked in Phase 0.5).

These are the single source of truth for request/response shapes.
Frontend types must match docs/api_examples/*.json.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class TextFeatures(BaseModel):
    avg_word_len: float
    syllable_density: float
    freq_percentile_mean: float
    sentence_count: int
    flesch_kincaid: float


class AdaptationConfig(BaseModel):
    letter_spacing_em: float = 0.0       # binary: one of [0.0, 0.04]
    word_spacing_em: float = 0.0         # binary: one of [0.0, 0.16]
    hyphenation_on: bool = False
    emphasis_on: bool = False
    color_overlay_on: bool = False       # binary
    chunked_on: bool = False
    opendyslexic_on: bool = False


class Token(BaseModel):
    text: str
    is_emphasized: bool
    class_hints: list[str]               # CSS classes the frontend may apply
    is_chunk_break: bool
    # Token.hyphenated REMOVED for hackathon scope (rev. 4 fix 35)
    # Hyphenation is applied server-side: emit final display-ready tokens with class_hints


class RenderRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=10_000)]
    user_id: str
    mode: Literal["default", "bionic", "lume_tuned"]
    # Optional manual overrides (rev. 4 fix 6) — when present, backend renders exactly this config
    adaptation_config: AdaptationConfig | None = None
    arm_index: int | None = None          # -1 means user_override (rev. 4 fix 34)
    recommendation_source: Literal["user_override"] | None = None
    text_id: str | None = None            # set when frontend loaded a seed passage

    @field_validator("text")
    @classmethod
    def text_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be whitespace-only")
        return v


class RenderResponse(BaseModel):
    render_id: str
    text_hash: str
    text_id: str | None
    features: TextFeatures
    word_count: int                       # used by /rate logging gate
    arm_index: int                        # 16-arm index, or -1 for non-arm
    adaptation_config: AdaptationConfig
    recommendation_source: Literal[
        "bandit", "model", "demo_seed",
        "mode_default", "mode_bionic", "mode_lume_tuned", "user_override"
    ]
    tokens: list[Token]
    chunks: list[list[int]]


class RateRequest(BaseModel):
    render_id: str                        # links the rated event back to a render
    user_id: str
    # Backend reconstructs from render_sessions[render_id] if available;
    # these are fallbacks if the server was reloaded between render and rate
    text_hash: str | None = None
    features_json: dict | None = None
    word_count: int | None = None
    text_id: str | None = None
    adaptation_config: AdaptationConfig
    arm_index: int                        # -1 if user_override
    recommendation_source: Literal[
        "bandit", "model", "demo_seed",
        "mode_default", "mode_bionic", "mode_lume_tuned", "user_override"
    ]
    was_user_modified: bool
    wpm: float
    # ── Comprehension signals ────────────────────────────────────────────────
    # When comprehension_type == "both", send self_rating + mcq_correct and
    # omit comprehension_score — the backend blends them server-side.
    # For legacy paths (synthetic seed rows, "mc"-only, "self_rated"-only) pass
    # comprehension_score directly.
    comprehension_score: float | None = Field(default=None, ge=0.0, le=1.0)
    comprehension_type: Literal["mc", "self_rated", "both"]
    self_rating: int | None = Field(default=None, ge=1, le=5)
    mcq_correct: bool | None = None

    @model_validator(mode="after")
    def _enforce_one_signal(self) -> "RateRequest":
        if (
            self.self_rating is None
            and self.mcq_correct is None
            and self.comprehension_score is None
        ):
            raise ValueError(
                "At least one of self_rating / mcq_correct / comprehension_score is required"
            )
        return self


class RateResponse(BaseModel):
    ok: bool
    event_id: int
    reward: float
    next_recommendation: AdaptationConfig | None


class ErrorBody(BaseModel):
    code: str
    message: str


class MCQRequest(BaseModel):
    """Request body for /generate-mcq."""

    text: Annotated[str, Field(min_length=1, max_length=10_000)]
    text_id: str | None = None          # matches seed passage → pre-defined question


class MCQQuestion(BaseModel):
    """A single multiple-choice question with 4 choices."""

    question: str
    choices: list[str]                  # exactly 4 items
    correct_index: int = Field(ge=0, le=3)   # index into choices[]
