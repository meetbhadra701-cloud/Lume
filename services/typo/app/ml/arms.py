"""16 explicit arms for the Thompson-sampling bandit (rev. 4 §A.8).

Spacing is binary toggleable: off=0.0, on=0.04em letter / 0.16em word.
"""

ARMS: list[dict] = [
    # 0: default (all off)
    {
        "letter_spacing_em": 0.0,
        "word_spacing_em": 0.0,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 1: letter spacing only
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.0,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 2: word spacing only
    {
        "letter_spacing_em": 0.0,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 3: letter + word spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 4: hyphenation + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": True,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 5: emphasis only
    {
        "letter_spacing_em": 0.0,
        "word_spacing_em": 0.0,
        "hyphenation_on": False,
        "emphasis_on": True,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 6: emphasis + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": True,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 7: color overlay + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": True,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 8: chunked + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": True,
        "opendyslexic_on": False,
    },
    # 9: opendyslexic only
    {
        "letter_spacing_em": 0.0,
        "word_spacing_em": 0.0,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": True,
    },
    # 10: opendyslexic + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": False,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": True,
    },
    # 11: bionic full (emphasis + opendyslexic + spacing)
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": True,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": True,
    },
    # 12: all adaptations except opendyslexic
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": True,
        "emphasis_on": True,
        "color_overlay_on": True,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
    # 13: chunked + emphasis + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": True,
        "color_overlay_on": False,
        "chunked_on": True,
        "opendyslexic_on": False,
    },
    # 14: color + emphasis + chunked + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": False,
        "emphasis_on": True,
        "color_overlay_on": True,
        "chunked_on": True,
        "opendyslexic_on": False,
    },
    # 15: hyphen + emphasis + spacing
    {
        "letter_spacing_em": 0.04,
        "word_spacing_em": 0.16,
        "hyphenation_on": True,
        "emphasis_on": True,
        "color_overlay_on": False,
        "chunked_on": False,
        "opendyslexic_on": False,
    },
]

assert len(ARMS) == 16, f"Expected 16 arms, got {len(ARMS)}"
