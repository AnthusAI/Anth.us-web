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


#: Pages folded into another page: slug -> the page that now carries them (all were
#: aspects of Venue Driver, with no body of their own). Like EXTERNAL_SITES they get no
#: page, drop out of every listing, the sitemap and the search data, every URL shape
#: they ever had 301s to the target, and links to them are rewritten to it.
FOLDED_INTO: dict[str, str] = {
    slug: "/articles/venue-driver/"
    for slug in (
        "ticket-driver", "ticket-driver-copilot", "store-driver", "checkout-driver", "menu-driver",
        "paytronix", "salesforce", "salesforce-marketing-cloud", "marketo", "vault", "ticketing-analysis",
    )
}


def is_folded(slug: str) -> bool:
    return (slug or "").strip().lower() in FOLDED_INTO


def is_external(slug: str) -> bool:
    return (slug or "").strip().lower() in EXTERNAL_SITES
