"""Locked mode → AdaptationConfig mappings (rev. 4 fix 33).

mode_default:    all toggles off, both spacings 0.0
mode_bionic:     emphasis_on=True, all others off
mode_lume_tuned: bandit/model recommendation; bandit if n_events < 30
"""
from app.schemas import AdaptationConfig

MODE_DEFAULT = AdaptationConfig(
    letter_spacing_em=0.0,
    word_spacing_em=0.0,
    hyphenation_on=False,
    emphasis_on=False,
    color_overlay_on=False,
    chunked_on=False,
    opendyslexic_on=False,
)

MODE_BIONIC = AdaptationConfig(
    letter_spacing_em=0.0,
    word_spacing_em=0.0,
    hyphenation_on=False,
    emphasis_on=True,   # bionic = frequency-aware emphasis only
    color_overlay_on=False,
    chunked_on=False,
    opendyslexic_on=False,
)

# mode_lume_tuned is dynamic — resolved by the recommender at request time.
# Placeholder returned here when recommender is unavailable.
MODE_LUME_TUNED_FALLBACK = AdaptationConfig(
    letter_spacing_em=0.04,
    word_spacing_em=0.16,
    hyphenation_on=False,
    emphasis_on=True,
    color_overlay_on=False,
    chunked_on=False,
    opendyslexic_on=False,
)


def config_for_mode(mode: str) -> tuple[AdaptationConfig, str, int]:
    """Return (AdaptationConfig, recommendation_source, arm_index) for a mode.

    arm_index=-1 for mode_default and mode_bionic (non-arm modes).
    mode_lume_tuned falls back to MODE_LUME_TUNED_FALLBACK until recommender
    is wired in Phase 2.
    """
    if mode == "default":
        return MODE_DEFAULT, "mode_default", -1
    elif mode == "bionic":
        return MODE_BIONIC, "mode_bionic", -1
    elif mode == "lume_tuned":
        # Replaced by recommender in Phase 2.5; stub returns fallback
        return MODE_LUME_TUNED_FALLBACK, "mode_lume_tuned", -1
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Valid modes: 'default', 'bionic', 'lume_tuned'.")
