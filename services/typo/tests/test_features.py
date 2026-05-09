"""Tests for 47-dim feature vector (Phase 2.1, §A.10)."""
import numpy as np
import pytest

from app.ml.features import (
    FEATURE_DIM,
    adaptation_indicators,
    build_feature_vector,
    text_main_effects,
)
from app.schemas import AdaptationConfig, TextFeatures

DEFAULT_FEATURES = TextFeatures(
    avg_word_len=4.5,
    syllable_density=1.3,
    freq_percentile_mean=0.6,
    sentence_count=5,
    flesch_kincaid=8.0,
)
DEFAULT_CFG = AdaptationConfig(
    letter_spacing_em=0.0,
    word_spacing_em=0.0,
    hyphenation_on=False,
    emphasis_on=False,
    color_overlay_on=False,
    chunked_on=False,
    opendyslexic_on=False,
)


def test_feature_dim_constant():
    assert FEATURE_DIM == 47


def test_feature_vector_length():
    vec = build_feature_vector(DEFAULT_FEATURES, DEFAULT_CFG)
    assert len(vec) == 47


def test_feature_vector_order():
    """Exact order: 5 text + 7 indicators + 35 interactions."""
    vec = build_feature_vector(DEFAULT_FEATURES, DEFAULT_CFG)
    # Text main effects
    t = text_main_effects(DEFAULT_FEATURES)
    assert vec[:5].tolist() == pytest.approx(t)
    # Adaptation indicators
    a = adaptation_indicators(DEFAULT_CFG)
    assert vec[5:12].tolist() == pytest.approx(a)
    # Interactions: row-major t[i] * a[j]
    for i, ti in enumerate(t):
        for j, aj in enumerate(a):
            expected = ti * aj
            idx = 12 + i * 7 + j
            assert vec[idx] == pytest.approx(expected), f"Mismatch at interaction [{i},{j}] (index {idx})"


def test_feature_vector_dtype():
    vec = build_feature_vector(DEFAULT_FEATURES, DEFAULT_CFG)
    assert vec.dtype == np.float64


def test_all_zero_default_config():
    """Default config → all adaptation indicators zero → interactions zero."""
    vec = build_feature_vector(DEFAULT_FEATURES, DEFAULT_CFG)
    # Indicators 5:12 should all be 0.0
    assert np.all(vec[5:12] == 0.0)
    # Interactions 12:47 should all be 0.0
    assert np.all(vec[12:] == 0.0)


def test_different_configs_produce_different_vectors():
    cfg_on = AdaptationConfig(
        letter_spacing_em=0.04,
        word_spacing_em=0.16,
        hyphenation_on=True,
        emphasis_on=True,
        color_overlay_on=False,
        chunked_on=False,
        opendyslexic_on=False,
    )
    v1 = build_feature_vector(DEFAULT_FEATURES, DEFAULT_CFG)
    v2 = build_feature_vector(DEFAULT_FEATURES, cfg_on)
    assert not np.array_equal(v1, v2)
