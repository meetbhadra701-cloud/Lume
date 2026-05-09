"""Tests for Pydantic schema validation and round-trips."""
import pytest
from pydantic import ValidationError

from app.schemas import (
    AdaptationConfig,
    RateRequest,
    RenderRequest,
    RenderResponse,
    TextFeatures,
    Token,
)


class TestRenderRequest:
    def test_valid_request(self):
        req = RenderRequest(
            text="The ability to read quickly and accurately is important for learning.",
            user_id="demo",
            mode="lume_tuned",
        )
        assert req.mode == "lume_tuned"
        assert req.adaptation_config is None

    def test_text_too_long_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest(
                text="x" * 10_001,
                user_id="demo",
                mode="default",
            )

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest(text="", user_id="demo", mode="default")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest(text="   \n\t  ", user_id="demo", mode="default")

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest(text="hello world test", user_id="demo", mode="invalid")

    def test_with_optional_override(self):
        cfg = AdaptationConfig(letter_spacing_em=0.04, emphasis_on=True)
        req = RenderRequest(
            text="Valid text for testing the schema",
            user_id="demo",
            mode="default",
            adaptation_config=cfg,
            arm_index=-1,
            recommendation_source="user_override",
        )
        assert req.arm_index == -1
        assert req.adaptation_config is not None
        assert req.adaptation_config.emphasis_on is True


class TestAdaptationConfig:
    def test_defaults(self):
        cfg = AdaptationConfig()
        assert cfg.letter_spacing_em == 0.0
        assert cfg.word_spacing_em == 0.0
        assert cfg.hyphenation_on is False
        assert cfg.emphasis_on is False
        assert cfg.color_overlay_on is False
        assert cfg.chunked_on is False
        assert cfg.opendyslexic_on is False

    def test_all_on(self):
        cfg = AdaptationConfig(
            letter_spacing_em=0.04,
            word_spacing_em=0.16,
            hyphenation_on=True,
            emphasis_on=True,
            color_overlay_on=True,
            chunked_on=True,
            opendyslexic_on=True,
        )
        assert cfg.letter_spacing_em == 0.04
        assert cfg.word_spacing_em == 0.16


class TestRateRequest:
    def test_valid_request(self):
        cfg = AdaptationConfig(emphasis_on=True)
        req = RateRequest(
            render_id="render-001",
            user_id="demo",
            adaptation_config=cfg,
            arm_index=3,
            recommendation_source="bandit",
            was_user_modified=False,
            wpm=175.5,
            comprehension_score=0.8,
            comprehension_type="self_rated",
        )
        assert req.wpm == 175.5
        assert req.comprehension_score == 0.8

    def test_comprehension_score_out_of_range(self):
        cfg = AdaptationConfig()
        with pytest.raises(ValidationError):
            RateRequest(
                render_id="render-001",
                user_id="demo",
                adaptation_config=cfg,
                arm_index=-1,
                recommendation_source="mode_default",
                was_user_modified=False,
                wpm=100.0,
                comprehension_score=1.5,   # invalid
                comprehension_type="self_rated",
            )

    def test_token_has_no_hyphenated_field(self):
        """Ensure Token does not have a 'hyphenated' field (rev. 4 fix 35)."""
        token = Token(
            text="reading",
            is_emphasized=False,
            class_hints=[],
            is_chunk_break=False,
        )
        assert not hasattr(token, "hyphenated")
        # Passing hyphenated should be ignored or error (extra fields off by default)
        token_dict = token.model_dump()
        assert "hyphenated" not in token_dict
