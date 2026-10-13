"""Animated pixel pictograms for the Anth.us arcade design (see DESIGN.md §6).

Public API (stable; page code depends on it):

    render(name: str) -> str
        Returns one self-contained ``<figure class="px" data-px="<name>">``
        string: inline SVG + figcaption with a drawn legend. Raises KeyError
        for an unknown name.

    NAMES: tuple[str, ...]
        Every pictogram name, in display order.

Styling lives in web/css/arcade-pictograms.css; the on-screen toggle is
web/assets/px-live.js.
"""

from __future__ import annotations

NAMES: tuple[str, ...] = (
    "hero-loop",
    "knowledge-base",
    "self-aligning",
    "agent-harness",
    "confidence-gate",
    "scorecard",
    "relocate",
    "platform-stack",
    "engagement-path",
    "verdict-meter",
    "leaderboard",
    "timeline",
    "lost-sprite",
)


def render(name: str) -> str:
    """Placeholder until the pictogram set lands: an empty labelled frame."""
    if name not in NAMES:
        raise KeyError(name)
    return (
        f'<figure class="px" data-px="{name}">'
        f'<svg class="px__svg" viewBox="0 0 64 40" role="img" aria-label="{name}" '
        f'shape-rendering="crispEdges"><rect x="0" y="0" width="64" height="40" '
        f'fill="none" stroke="var(--px-dim)"/></svg>'
        f"</figure>"
    )
