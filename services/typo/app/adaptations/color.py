"""Warm colour overlay adaptation.

When color_overlay_on=True the frontend applies a CSS background using the
locked WCAG-AA-tested value:
  --lume-overlay-warm: oklch(0.97 0.03 80)   (parchment-warm)

This module emits the CSS class hint that the frontend looks for.  We
deliberately do NOT apply any colour server-side (tokens are plain text);
the class hint is the only coupling point.

Public API
----------
- get_color_classes(color_overlay_on) → list[str]
"""

from __future__ import annotations

_CLASS_OVERLAY = "lume-color-overlay"


def get_color_classes(color_overlay_on: bool) -> list[str]:
    """Return class hints for the warm colour overlay.

    Parameters
    ----------
    color_overlay_on:
        Whether the overlay is active.

    Returns
    -------
    ``["lume-color-overlay"]`` if on, ``[]`` if off.
    """
    return [_CLASS_OVERLAY] if color_overlay_on else []
