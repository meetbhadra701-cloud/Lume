"""Tests for MCQ generator (Phase MCQ feature)."""

from app.adaptations.mcq_generator import (
    SEED_MCQS,
    _split_sentences,
    generate_mcq,
)

# ── Seed-passage tests ────────────────────────────────────────────────────────

def test_seed_passage_returns_predefined_mcq():
    """Known text_ids return the hardcoded MCQ, not an algorithmic one."""
    for text_id, expected in SEED_MCQS.items():
        result = generate_mcq("any text", text_id=text_id)
        assert result["question"] == expected["question"]
        assert result["choices"] == expected["choices"]
        assert result["correct_index"] == expected["correct_index"]


def test_seed_passage_correct_index_in_range():
    """correct_index is always within [0, 3]."""
    for text_id in SEED_MCQS:
        result = generate_mcq("x", text_id=text_id)
        assert 0 <= result["correct_index"] <= 3


def test_seed_passage_exactly_4_choices():
    """Seed MCQs have exactly 4 choices."""
    for text_id in SEED_MCQS:
        result = generate_mcq("x", text_id=text_id)
        assert len(result["choices"]) == 4


# ── Gutenberg-001 specific (Time Machine) ────────────────────────────────────

TIME_MACHINE_TEXT = (
    "The Time Traveller, for so it will be convenient to speak of him, was expounding "
    "a recondite matter to us. His grey eyes shone and twinkled, and his usually pale "
    "face was flushed and animated. The fire burned brightly, and the soft radiance of "
    "the incandescent lights in the lilies of silver caught the bubbles that flashed "
    "and passed in our glasses."
)


def test_time_machine_correct_answer_is_grey():
    result = generate_mcq(TIME_MACHINE_TEXT, text_id="gutenberg_001")
    correct_choice = result["choices"][result["correct_index"]]
    assert correct_choice == "Grey"


# ── Tom Sawyer specific ───────────────────────────────────────────────────────

TOM_SAWYER_TEXT = (
    "Tom appeared on the sidewalk with a bucket of whitewash and a long-handled brush. "
    "He surveyed the fence, and all gladness left him and a deep melancholy settled "
    "down upon his spirit. Thirty yards of board fence nine feet high."
)


def test_tom_sawyer_correct_answer_is_nine_feet():
    result = generate_mcq(TOM_SAWYER_TEXT, text_id="gutenberg_002")
    correct_choice = result["choices"][result["correct_index"]]
    assert correct_choice == "Nine feet"


# ── Algorithmic generation tests ──────────────────────────────────────────────

NUMBER_TEXT = (
    "The project was completed in 42 days. The team had 8 engineers working "
    "on it. They wrote over 15,000 lines of code during that period. "
    "The budget was fixed at 200 thousand dollars."
)


def test_algorithmic_returns_4_choices():
    result = generate_mcq(NUMBER_TEXT, seed=42)
    assert len(result["choices"]) == 4


def test_algorithmic_correct_index_valid():
    result = generate_mcq(NUMBER_TEXT, seed=42)
    assert 0 <= result["correct_index"] <= 3


def test_algorithmic_correct_answer_in_choices():
    result = generate_mcq(NUMBER_TEXT, seed=42)
    assert result["choices"][result["correct_index"]] in result["choices"]


def test_number_in_text_triggers_number_question():
    """When the text has prominent numbers, the question references one of them."""
    result = generate_mcq(NUMBER_TEXT, seed=42)
    correct = result["choices"][result["correct_index"]]
    # The correct answer should be a number string from the text
    assert any(n in correct for n in ["42", "8", "200", "15", "000"])


PROPER_NOUN_TEXT = (
    "Elizabeth Bennet arrived at Netherfield Park on a cold Tuesday morning. "
    "She had travelled from Longbourn with her sister Jane. "
    "Mr Darcy greeted them at the door with characteristic reserve."
)


def test_proper_noun_text_returns_named_entity():
    result = generate_mcq(PROPER_NOUN_TEXT, seed=0)
    correct = result["choices"][result["correct_index"]]
    # Should be one of the proper nouns in the text
    assert any(n in correct for n in [
        "Elizabeth", "Bennet", "Netherfield", "Park",
        "Tuesday", "Longbourn", "Jane", "Darcy",
    ])


def test_unknown_text_id_triggers_algorithmic_generation():
    """A text_id not in SEED_MCQS falls through to algorithmic generation."""
    result = generate_mcq(NUMBER_TEXT, text_id="unknown_passage_xyz", seed=1)
    assert len(result["choices"]) == 4


def test_empty_sentences_returns_safe_fallback():
    """Very short or empty text does not crash — returns a safe fallback."""
    result = generate_mcq("OK", seed=0)
    assert "question" in result
    assert len(result["choices"]) == 4


def test_deterministic_with_seed():
    """Same seed → same question for arbitrary text."""
    r1 = generate_mcq(NUMBER_TEXT, seed=7)
    r2 = generate_mcq(NUMBER_TEXT, seed=7)
    assert r1 == r2


def test_no_duplicate_choices():
    """All 4 choices in any MCQ are distinct."""
    texts = [NUMBER_TEXT, PROPER_NOUN_TEXT, TIME_MACHINE_TEXT]
    for t in texts:
        result = generate_mcq(t, seed=99)
        assert len(set(result["choices"])) == 4, f"Duplicate choices: {result['choices']}"


def test_fallback_question_for_no_numbers_no_nouns():
    """Pure lowercase text with no numbers uses the sentence-order fallback."""
    plain = (
        "the cat sat on the mat and looked at the wall for a long time. "
        "it thought about various things that cats think about during the day. "
        "eventually it got up and walked away to find something to eat."
    )
    result = generate_mcq(plain, seed=0)
    assert "question" in result
    assert len(result["choices"]) == 4
    assert 0 <= result["correct_index"] <= 3


# ── split_sentences helper ────────────────────────────────────────────────────

def test_split_sentences_filters_short():
    text = "Hi. This is a short intro. The main content begins here with enough words to count."
    sents = _split_sentences(text)
    assert all(len(s.split()) >= 5 for s in sents)


def test_split_sentences_non_empty():
    assert _split_sentences(NUMBER_TEXT)
