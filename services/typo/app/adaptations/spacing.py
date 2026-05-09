"""Spacing adaptation helpers.

Applies letter-spacing and word-spacing by injecting CSS class hints into
tokens.  The actual CSS is applied by the frontend — this module just
decides which tokens should receive which hints.

The values are binary (per §A.8 of the plan):
  letter_spacing_em : 0.0 (off) or 0.04 (on)
  word_spacing_em   : 0.0 (off) or 0.16 (on)

Public API
----------
- get_spacing_classes(letter_spacing_em, word_spacing_em) → list[str]
"""

from __future__ import annotations


# CSS class names emitted into Token.class_hints
_CLASS_LETTER = "lume-letter-spaced"
_CLASS_WORD = "lume-word-spaced"


def get_spacing_classes(
    letter_spacing_em: float,
    word_spacing_em: float,
) -> list[str]:
    """Return the list of CSS class names appropriate for the given spacings.

    Parameters
    ----------
    letter_spacing_em:
        Letter spacing in em (0.0 = off, 0.04 = on).
    word_spacing_em:
        Word spacing in em (0.0 = off, 0.16 = on).

    Returns
    -------
    A (possibly empty) list of CSS class name strings to include in
    ``Token.class_hints`` for every token in the passage.
    """
    classes: list[str] = []
    if letter_spacing_em > 0.0:
        classes.append(_CLASS_LETTER)
    if word_spacing_em > 0.0:
        classes.append(_CLASS_WORD)
    return classes
