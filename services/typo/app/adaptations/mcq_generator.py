"""MCQ generator for passage comprehension assessment.

Guarantees the question is always derived from the passage the user read.

Strategy (in priority order):
1. Pre-defined MCQs for known seed passage text_ids — highest quality, exact match.
2. Number-extraction — find a sentence with a specific number, ask about it.
3. Proper-noun extraction — find a sentence with a name/place, ask about it.
4. Sentence-order fallback — ask which sentence opens the passage.

All strategies produce a question + 4 choices + correct_index (0–3).
"""
from __future__ import annotations

import random
import re

# ── Pre-defined MCQs for seed passages ───────────────────────────────────────
# These are hardcoded so demo MCQs are always accurate, specific, and unambiguous.
# Each entry keyed by the text_id defined in apps/web/lib/seed_passages.ts.

SEED_MCQS: dict[str, dict] = {
    "gutenberg_001": {
        "question": "According to the passage, what colour were the Time Traveller's eyes?",
        "choices": ["Brown", "Grey", "Blue", "Green"],
        "correct_index": 1,  # "Grey"
    },
    "gutenberg_002": {
        "question": "How high was the board fence that Tom was whitewashing?",
        "choices": ["Six feet", "Eight feet", "Nine feet", "Twelve feet"],
        "correct_index": 2,  # "Nine feet"
    },
    "gutenberg_003": {
        "question": "What is the name of the property mentioned as having been let at last?",
        "choices": ["Pemberley", "Longbourn", "Rosings Park", "Netherfield Park"],
        "correct_index": 3,  # "Netherfield Park"
    },
    "gutenberg_004": {
        "question": "What name does the narrator ask to be called in the opening line?",
        "choices": ["Ahab", "Ishmael", "Queequeg", "Starbuck"],
        "correct_index": 1,  # "Ishmael"
    },
    "gutenberg_005": {
        "question": "Which city does the narrator mention walking through in the passage?",
        "choices": ["Berlin", "London", "Petersburgh", "Stockholm"],
        "correct_index": 2,  # "Petersburgh"
    },
}

# ── Internal helpers ──────────────────────────────────────────────────────────

_COMMON_CAPS = frozenset({
    "The", "A", "An", "This", "That", "These", "Those",
    "I", "He", "She", "It", "We", "They",
    "My", "His", "Her", "Its", "Our", "Their", "Your",
    "In", "On", "At", "To", "Of", "For", "And", "Or", "But",
    "With", "From", "By", "As", "Is", "Are", "Was", "Were",
    "Be", "Been", "Have", "Has", "Had", "Do", "Did", "Does",
    "Will", "Would", "Could", "Should", "May", "Might", "Must",
    "Not", "No", "So", "If", "Then", "When", "Where", "How",
    "What", "Who", "Which", "Whose", "Whom", "There", "Here",
    "Now", "Just", "Never", "Always", "Still", "Yet", "Even",
})


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences that contain at least 5 words."""
    raw = re.split(r"(?<=[.!?;])\s+", text.strip())
    return [s.strip() for s in raw if len(s.split()) >= 5]


def _truncate(s: str, max_chars: int = 90) -> str:
    """Trim a string to max_chars at a word boundary."""
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


# ── Strategy 1: number-based question ────────────────────────────────────────

_NUM_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\b")
# Noun AFTER a number — e.g. "42 days" → "days"; "200 thousand" → "thousand"
_NOUN_AFTER_NUM_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s+([a-z][a-z-]+)")


def _try_number_question(sentences: list[str], rng: random.Random) -> dict | None:
    """Ask about a specific number mentioned in the passage."""
    candidates: list[tuple[str, list[str]]] = []
    for sent in sentences:
        nums = _NUM_RE.findall(sent)
        if nums:
            candidates.append((sent, nums))

    if not candidates:
        return None

    sent, nums = rng.choice(candidates)
    correct = rng.choice(nums)

    # Build a natural question using the noun that follows the number (e.g. "42 days" → "days")
    m_after = _NOUN_AFTER_NUM_RE.search(sent)
    noun_after = m_after.group(1) if m_after else None
    _skip_nouns = {"thousand", "million", "billion", "hundred", "percent", "per"}

    if noun_after and noun_after not in _skip_nouns:
        question = (
            f'According to the passage, how many {noun_after} '
            f'are mentioned in: "{_truncate(sent, 85)}"?'
        )
    else:
        question = (
            f'According to the passage, which number appears in: "{_truncate(sent, 85)}"?'
        )

    # Build distractor pool from other numbers in the text
    all_nums = list({n for _, ns in candidates for n in ns} - {correct})
    rng.shuffle(all_nums)
    distractors = all_nums[:3]

    # Pad with arithmetic variants if the pool is thin
    try:
        val = float(correct.replace(",", ""))
        extras = [
            str(int(val * 2)),
            str(int(val + max(1, int(val * 0.5)))),
            str(int(max(1, val - max(1, int(val * 0.5))))),
        ]
        for e in extras:
            if e != correct and e not in distractors:
                distractors.append(e)
    except ValueError:
        pass

    distractors = list(dict.fromkeys(distractors))[:3]
    while len(distractors) < 3:
        distractors.append(str(rng.randint(2, 50)))

    choices = [correct] + distractors[:3]
    rng.shuffle(choices)

    return {
        "question": question,
        "choices": choices,
        "correct_index": choices.index(correct),
    }


# ── Strategy 2: proper-noun question ─────────────────────────────────────────

_GENERIC_FALLBACK_NAMES = [
    "London", "Paris", "James", "Elizabeth", "Monday", "January",
    "Edinburgh", "Boston", "William", "Margaret",
]


def _try_proper_noun_question(sentences: list[str], rng: random.Random) -> dict | None:
    """Ask about a proper noun (name or place) in the passage."""
    candidates: list[tuple[str, list[str]]] = []
    for sent in sentences:
        words = sent.split()
        # Proper nouns: capitalised words not at sentence start, not common
        proper = [
            w.strip(".,;:\"'!?()") for w in words[1:]
            if w and w[0].isupper()
            and w.strip(".,;:\"'!?()") not in _COMMON_CAPS
            and len(w.strip(".,;:\"'!?()")) > 1
            and w.strip(".,;:\"'!?()").replace("'", "").isalpha()
        ]
        if proper:
            candidates.append((sent, proper))

    if not candidates:
        return None

    sent, nouns = rng.choice(candidates)
    correct = rng.choice(nouns)

    question = (
        f'According to the passage, which name or place is mentioned in: '
        f'"{_truncate(sent, 85)}"?'
    )

    # Distractors: other proper nouns in the text
    all_nouns = list({n for _, ns in candidates for n in ns} - {correct})
    rng.shuffle(all_nouns)
    distractors = all_nouns[:3]

    # Pad with generic names if needed
    generic = [n for n in _GENERIC_FALLBACK_NAMES if n != correct and n not in distractors]
    rng.shuffle(generic)
    for g in generic:
        if len(distractors) >= 3:
            break
        distractors.append(g)

    choices = [correct] + distractors[:3]
    rng.shuffle(choices)

    return {
        "question": question,
        "choices": choices,
        "correct_index": choices.index(correct),
    }


# ── Strategy 3: sentence-order fallback ──────────────────────────────────────

def _fallback_question(sentences: list[str], rng: random.Random) -> dict:
    """Ask which sentence appears at the opening of the passage."""
    if len(sentences) < 2:
        correct = _truncate(sentences[0], 80) if sentences else "the passage text"
        return {
            "question": "What does the opening of the passage describe?",
            "choices": [correct, "A scientific discovery", "A historical battle", "A mathematical proof"],
            "correct_index": 0,
        }

    correct = _truncate(sentences[0], 80)
    pool = [_truncate(s, 80) for s in sentences[1:] if s.strip() != sentences[0].strip()]
    rng.shuffle(pool)
    distractors = pool[:3]

    while len(distractors) < 3:
        distractors.append("None of the above sentences")

    choices = [correct] + distractors[:3]
    rng.shuffle(choices)

    return {
        "question": "Which of the following appears at the opening of the passage?",
        "choices": choices,
        "correct_index": choices.index(correct),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def generate_mcq(text: str, text_id: str | None = None, seed: int | None = None) -> dict:
    """Generate a single MCQ tied to the provided passage text.

    Args:
        text:    The exact passage text the user read.
        text_id: Optional identifier — if it matches a seed passage, the
                 pre-defined MCQ is returned immediately (no algorithmic
                 generation needed).
        seed:    Optional RNG seed for reproducibility in tests.

    Returns:
        {
            "question": str,
            "choices": list[str],   # exactly 4 items
            "correct_index": int,   # 0–3
        }
    """
    # Seed passages: guaranteed accurate, hardcoded to that specific text
    if text_id and text_id in SEED_MCQS:
        return SEED_MCQS[text_id]

    rng = random.Random(seed)
    sentences = _split_sentences(text)

    if not sentences:
        return {
            "question": "What is this passage about?",
            "choices": [
                "The content of the text provided",
                "An unrelated scientific theory",
                "A historical military campaign",
                "A mathematical theorem",
            ],
            "correct_index": 0,
        }

    # Try strategies in priority order
    result = _try_number_question(sentences, rng)
    if result:
        return result

    result = _try_proper_noun_question(sentences, rng)
    if result:
        return result

    return _fallback_question(sentences, rng)
