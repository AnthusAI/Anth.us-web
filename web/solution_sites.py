"""Solutions and technology that have their own marketing site.

Such a thing gets NO page on anth.us: every link goes straight to its site, and the
old `/platform/<slug>/` URL redirects (301) there. This is the one mapping; the
content MDX files stay untouched in the content repository and are simply not
emitted as pages.
"""

from __future__ import annotations

#: platform slug -> site
EXTERNAL_SITES: dict[str, str] = {
    "primus": "https://primus.anth.us",
    "chatticus": "https://chattic.us",
    "kanbus": "https://kanb.us",
    "tactus": "https://tactus.anth.us",
}


def is_external(slug: str) -> bool:
    return (slug or "").strip().lower() in EXTERNAL_SITES
