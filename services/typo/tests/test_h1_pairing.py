"""Test H1 paired design: pivot must produce ≥80% paired rows (§A.14)."""

from app.eda.synthesize import generate_synthetic_events


def test_h1_pairing_at_least_80_percent():
    """Pivot on (user_id, text_hash) must pair ≥80% of expected rows.

    The synthetic generator creates one 'default' and one 'adapted' row per pair.
    All adapted conditions use letter-spacing arms (§A.14).
    A merge on (user_id, text_hash) should recover ≥80% of the 100 expected pairs.
    """
    df = generate_synthetic_events(n_pairs=100, seed=42)

    # All adapted rows must have letter spacing (generator guarantee)
    adapted = df[df["condition"] == "adapted"]
    assert all(adapted["has_letter_spacing"]), (
        "All adapted rows should have letter spacing (synthesize.py §A.14)"
    )

    # Separate conditions
    df_default = df[df["condition"] == "default"]
    df_adapted = df[df["condition"] == "adapted"]

    # Pivot on (user_id, text_hash) — should pair all rows
    paired = df_default[["user_id", "text_hash", "wpm"]].merge(
        df_adapted[["user_id", "text_hash", "wpm"]],
        on=["user_id", "text_hash"],
        suffixes=("_default", "_letter_spacing"),
    )

    n_expected = len(df_default)   # 100 pairs
    n_paired = len(paired)
    pair_pct = n_paired / n_expected

    assert pair_pct >= 0.80, (
        f"Only {n_paired}/{n_expected} ({pair_pct*100:.0f}%) pairs recovered — "
        "expected ≥80% (§A.14)"
    )
    print(f"H1 pairing: {n_paired}/{n_expected} ({pair_pct*100:.0f}%) ✓")


def test_h1_wpm_lift_positive():
    """The letter-spacing adapted condition should have higher WPM than default."""
    df = generate_synthetic_events(n_pairs=100, seed=42)
    mean_wpm_default = df[df["condition"] == "default"]["wpm"].mean()
    mean_wpm_adapted = df[df["condition"] == "adapted"]["wpm"].mean()
    assert mean_wpm_adapted > mean_wpm_default, (
        f"Adapted WPM ({mean_wpm_adapted:.1f}) should exceed default ({mean_wpm_default:.1f})"
    )
