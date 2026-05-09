"""47-dimensional feature vector for per-user Ridge regression.

Layout (locked, §A.10):
  [0:5]   text main effects   (5)
  [5:12]  adaptation indicators (7)
  [12:47] text × adaptation interactions (35 = 5 × 7)

Feature ordering is tested by test_features.py::test_feature_vector_order.

Public API
----------
- build_feature_vector(features: TextFeatures, cfg: AdaptationConfig) → np.ndarray
- FEATURE_DIM: int = 47
"""

from __future__ import annotations

import numpy as np

from app.schemas import AdaptationConfig, TextFeatures

FEATURE_DIM = 47  # 5 + 7 + 35


def text_main_effects(features: TextFeatures) -> list[float]:
    """Return the 5 text feature values in canonical order."""
    return [
        features.avg_word_len,
        features.syllable_density,
        features.freq_percentile_mean,
        float(features.sentence_count),
        features.flesch_kincaid,
    ]


def adaptation_indicators(cfg: AdaptationConfig) -> list[float]:
    """Return the 7 adaptation indicators in canonical order.

    Binary spacing values (0.0 / 0.04 and 0.0 / 0.16) are used as-is
    (numeric, not boolean flags) so the feature space is consistent with
    the binary toggle UI.
    """
    return [
        cfg.letter_spacing_em,                # 0.0 or 0.04
        cfg.word_spacing_em,                  # 0.0 or 0.16
        float(cfg.hyphenation_on),
        float(cfg.emphasis_on),
        float(cfg.color_overlay_on),
        float(cfg.chunked_on),
        float(cfg.opendyslexic_on),
    ]


def build_feature_vector(
    features: TextFeatures,
    cfg: AdaptationConfig,
) -> np.ndarray:
    """Build the 47-dim feature vector.

    Concatenation:
        v = [text_effects (5)] + [indicators (7)] + [interactions (35)]

    Interactions = outer product: text_effects[i] * indicators[j]
    for all i in [0,5), j in [0,7), flattened row-major.

    Returns
    -------
    np.ndarray of shape (47,), dtype float64.
    """
    t = text_main_effects(features)          # len 5
    a = adaptation_indicators(cfg)           # len 7

    # 35 pairwise interactions (5 × 7), row-major
    interactions = [ti * aj for ti in t for aj in a]

    vec = t + a + interactions               # len 5 + 7 + 35 = 47
    assert len(vec) == FEATURE_DIM, f"Expected {FEATURE_DIM} dims, got {len(vec)}"
    return np.array(vec, dtype=np.float64)
