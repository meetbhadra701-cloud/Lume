"""Synthetic reading-event generator for EDA.

Generates 200 paired observations (same passage × user under two conditions)
for hypothesis testing.  The synthetic reward function encodes known effects:
  - letter_spacing_em > 0 → +0.12 WPM lift (H1)
  - emphasis_on × high syllable_density → +0.08 comprehension lift (H3)

Random seed: 42 (documented in docs/data_sources.md).

Usage
-----
    from app.eda.synthesize import generate_synthetic_events
    df = generate_synthetic_events(n_pairs=100, seed=42)
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.ml.arms import ARMS
from app.ml.reward import WPM_CEIL, WPM_FLOOR, compute_reward

# Arms that have letter_spacing_em > 0 (for H1 paired design)
# §A.14: adapted condition MUST have letter spacing so pairs are well-formed
_LS_ARM_INDICES = [i for i, a in enumerate(ARMS) if a["letter_spacing_em"] > 0]

# ── Baseline user profiles ───────────────────────────────────────────────────

_USER_PROFILES = [
    {"user_id": f"synth_user_{i:02d}", "base_wpm": wpm, "base_comp": comp}
    for i, (wpm, comp) in enumerate([
        (130, 0.6), (155, 0.65), (180, 0.7), (110, 0.55), (200, 0.75),
        (145, 0.62), (165, 0.68), (125, 0.58), (190, 0.72), (140, 0.63),
    ])
]

# ── Passage feature distributions ────────────────────────────────────────────

_FEATURE_TEMPLATES = [
    {"avg_word_len": 5.2, "syllable_density": 1.7, "freq_percentile_mean": 0.45,
     "sentence_count": 6, "flesch_kincaid": 11.0},
    {"avg_word_len": 4.3, "syllable_density": 1.3, "freq_percentile_mean": 0.62,
     "sentence_count": 8, "flesch_kincaid": 7.5},
    {"avg_word_len": 6.1, "syllable_density": 2.1, "freq_percentile_mean": 0.35,
     "sentence_count": 4, "flesch_kincaid": 13.5},
    {"avg_word_len": 4.8, "syllable_density": 1.5, "freq_percentile_mean": 0.55,
     "sentence_count": 7, "flesch_kincaid": 9.0},
]


def _jitter(val: float, sigma: float, rng: np.random.Generator) -> float:
    return float(val + rng.normal(0, sigma))


def _apply_adaptations(
    base_wpm: float,
    base_comp: float,
    cfg: dict,
    features: dict,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """Apply synthetic adaptation effects on top of baseline."""
    wpm = base_wpm
    comp = base_comp

    # H1: letter spacing → WPM improvement (H2 interaction: more complex text benefits more)
    if cfg["letter_spacing_em"] > 0:
        # Base effect + complexity bonus (H2: text complexity moderates benefit)
        complexity_bonus = max(0.0, (features["flesch_kincaid"] - 7.0) / 7.0)  # 0 at FK=7, ~1 at FK=14
        wpm += rng.normal(12.0 + 20.0 * complexity_bonus, 6.0)   # 12–32 WPM depending on complexity

    # word spacing: smaller WPM gain
    if cfg["word_spacing_em"] > 0:
        wpm += rng.normal(6.0, 5.0)

    # H3 interaction: emphasis × high syllable density → comprehension
    if cfg["emphasis_on"] and features["syllable_density"] > 1.6:
        comp += rng.normal(0.10, 0.05)

    # hyphenation: small comprehension gain for long-word passages
    if cfg["hyphenation_on"] and features["avg_word_len"] > 5.0:
        comp += rng.normal(0.05, 0.03)

    # chunking: helps slower readers
    if cfg["chunked_on"] and base_wpm < 150:
        comp += rng.normal(0.06, 0.04)

    # opendyslexic: some readers benefit, some don't (high variance)
    if cfg["opendyslexic_on"]:
        comp += rng.normal(0.0, 0.08)

    # Clip to valid ranges
    wpm = max(WPM_FLOOR, min(wpm, WPM_CEIL))
    comp = max(0.0, min(comp, 1.0))
    return wpm, comp


def generate_synthetic_events(
    n_pairs: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate *n_pairs* paired observations.

    Each pair = same (user_id, text_hash) under TWO conditions:
      - "default" (all off)
      - one randomly-chosen non-default arm

    Returns a DataFrame with one row per observation (2 × n_pairs rows total).
    Columns match the events table schema.
    """
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)

    corpus_path = Path(__file__).resolve().parent / "sample_corpus.jsonl"
    passages = [json.loads(l) for l in corpus_path.read_text().splitlines() if l.strip()]

    rows: list[dict[str, Any]] = []

    for pair_idx in range(n_pairs):
        passage = py_rng.choice(passages)
        text_hash = f"synth_{passage['id']}_{pair_idx:03d}"
        user = py_rng.choice(_USER_PROFILES)
        feature_tmpl = py_rng.choice(_FEATURE_TEMPLATES)

        # Jitter features slightly for each pair
        features = {
            "avg_word_len": _jitter(feature_tmpl["avg_word_len"], 0.3, rng),
            "syllable_density": _jitter(feature_tmpl["syllable_density"], 0.15, rng),
            "freq_percentile_mean": max(0.1, min(0.9, _jitter(feature_tmpl["freq_percentile_mean"], 0.05, rng))),
            "sentence_count": max(2, int(feature_tmpl["sentence_count"] + rng.integers(-2, 3))),
            "flesch_kincaid": _jitter(feature_tmpl["flesch_kincaid"], 0.8, rng),
        }

        # Condition A: default
        default_arm = ARMS[0]
        wpm_a, comp_a = _apply_adaptations(
            user["base_wpm"], user["base_comp"], default_arm, features, rng,
        )
        reward_a = compute_reward(wpm_a, comp_a)

        rows.append({
            "user_id": user["user_id"],
            "text_hash": text_hash,
            "features_json": json.dumps(features),
            "adaptation_config_json": json.dumps(default_arm),
            "arm_index": 0,
            "recommendation_source": "demo_seed",
            "was_user_modified": False,
            "word_count": 75,
            "wpm": round(wpm_a, 1),
            "comprehension_score": round(comp_a, 3),
            "comprehension_type": "self_rated",
            "reward": round(reward_a, 4),
            "data_source": "synthetic",
            "has_letter_spacing": default_arm["letter_spacing_em"] > 0,
            "condition": "default",
        })

        # Condition B: always a letter-spacing arm (§A.14 — H1 paired design)
        non_default_arm_idx = py_rng.choice(_LS_ARM_INDICES)
        non_default_arm = ARMS[non_default_arm_idx]
        wpm_b, comp_b = _apply_adaptations(
            user["base_wpm"], user["base_comp"], non_default_arm, features, rng,
        )
        reward_b = compute_reward(wpm_b, comp_b)

        rows.append({
            "user_id": user["user_id"],
            "text_hash": text_hash,
            "features_json": json.dumps(features),
            "adaptation_config_json": json.dumps(non_default_arm),
            "arm_index": non_default_arm_idx,
            "recommendation_source": "demo_seed",
            "was_user_modified": False,
            "word_count": 75,
            "wpm": round(wpm_b, 1),
            "comprehension_score": round(comp_b, 3),
            "comprehension_type": "self_rated",
            "reward": round(reward_b, 4),
            "data_source": "synthetic",
            "has_letter_spacing": non_default_arm["letter_spacing_em"] > 0,
            "condition": "adapted",
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_synthetic_events(n_pairs=100, seed=42)
    print(f"Generated {len(df)} rows for {df['user_id'].nunique()} unique users")
    print(df.groupby("condition")[["wpm", "comprehension_score", "reward"]].mean().round(3))
