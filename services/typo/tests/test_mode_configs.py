"""Tests for mode → config mappings (Phase 2.0, rev. 4 fix 33)."""
import pytest

from app.api.mode_configs import config_for_mode
from app.schemas import AdaptationConfig


def test_mode_default_all_off():
    cfg, source, arm = config_for_mode("default")
    assert cfg.letter_spacing_em == 0.0
    assert cfg.word_spacing_em == 0.0
    assert cfg.hyphenation_on is False
    assert cfg.emphasis_on is False
    assert cfg.color_overlay_on is False
    assert cfg.chunked_on is False
    assert cfg.opendyslexic_on is False
    assert source == "mode_default"
    assert arm == -1


def test_mode_bionic_emphasis_only():
    cfg, source, arm = config_for_mode("bionic")
    assert cfg.emphasis_on is True
    assert cfg.letter_spacing_em == 0.0
    assert cfg.word_spacing_em == 0.0
    assert cfg.hyphenation_on is False
    assert cfg.color_overlay_on is False
    assert cfg.chunked_on is False
    assert cfg.opendyslexic_on is False
    assert source == "mode_bionic"
    assert arm == -1


def test_mode_lume_tuned_returns_config():
    cfg, source, arm = config_for_mode("lume_tuned")
    assert isinstance(cfg, AdaptationConfig)
    assert source == "mode_lume_tuned"
    assert arm == -1


def test_invalid_mode_raises():
    with pytest.raises((ValueError, KeyError, Exception)):
        config_for_mode("nonexistent_mode")
