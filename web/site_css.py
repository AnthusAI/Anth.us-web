"""The one stylesheet the site ships: arcade.css + arcade-pictograms.css.

Both sources are hand-written (DESIGN.md). The build stages their
concatenation and hands it to Papyrus as ``site_css``; the projector reads the
same bytes, so the two delivery paths cannot drift.
"""

from __future__ import annotations

from pathlib import Path

CSS_DIR = Path(__file__).resolve().parent / "css"
#: In cascade order. The pictogram sheet is optional (tolerated absent).
SOURCES = ("arcade.css", "arcade-pictograms.css")


def stylesheet_bytes() -> bytes:
    parts = []
    for name in SOURCES:
        path = CSS_DIR / name
        if path.is_file():
            parts.append(f"/* ---- {name} ---- */\n".encode() + path.read_bytes().rstrip() + b"\n")
        elif name == SOURCES[0]:
            raise FileNotFoundError(path)
    return b"\n".join(parts)


def stage(destination: Path) -> Path:
    """Write the concatenated sheet to ``destination`` and return it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(stylesheet_bytes())
    return destination
