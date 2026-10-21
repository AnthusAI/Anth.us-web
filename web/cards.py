"""The arcade components that cards, listings and the page hero are made of (web/DESIGN.md).

Cards are what the ``card`` hook returns for an entry; the listing views (a collection page, a tag page, the tag index)
are composed here from the standard projector's view of the page.
"""

from __future__ import annotations

from html import escape

import anthus_dom
import arcade_pictograms
from anthus_content import ContentNode, ImageIndex
from anthus_urls import FEATURED_COUNT, GRID_SIZE, collection_page_count, tag_slug

BARE = anthus_dom.BARE_MARKER


_HIDDEN_TAGS = frozenset({"featured", "solutions", "engagement", "integrations"})


def _esc(value: str) -> str:
    return escape(str(value), quote=True)


def blog_href(node: ContentNode) -> str:
    """The production route for one article or post."""
    return f"/blog/{node.slug}/"


def platform_href(node: ContentNode) -> str:
    return f"/platform/{node.slug}/"


def _preview(node: ContentNode, images: ImageIndex) -> str | None:
    """The item's preview image path (listing visual and social-share image)."""
    raw = node.front_matter.get("preview_image")
    if not raw:
        return None
    return images.resolve_path(str(raw), relative_to=node.source)


def _fm(node: ContentNode, key: str) -> str:
    value = node.front_matter.get(key)
    return "" if value in (None, "") else str(value)


def _page_hero(
    eyebrow: str,
    title: str,
    lead_html: str,
    *,
    art: str = "",
    actions: str = "",
    compact: bool = False,
    cursor: bool = True,
) -> str:
    """Page hero: eyebrow, Jersey 25 h1, lead, optional art (pictogram or photo) from 64rem."""
    solo = "" if art else " hero__grid--solo"
    cur = '<span class="cursor" aria-hidden="true"></span>' if cursor else ""
    art_html = f'<div class="hero__art">{art}</div>' if art else ""
    return (
        f'<section class="hero hero--page{" hero--compact" if compact else ""}">'
        f'<div class="container hero__grid{solo}"><div class="hero__copy">'
        f'<p class="eyebrow">{escape(eyebrow)}</p><h1>{escape(title)}{cur}</h1>'
        + (f'<p class="lead">{lead_html}</p>' if lead_html else "")
        + (f'<div class="btn-row">{actions}</div>' if actions else "")
        + f"</div>{art_html}</div></section>"
    )


def _short_date(node: ContentNode) -> str:
    """YYYY-MM-DD for the card meta line, however the front matter spells the date."""
    raw = node.date_raw
    return node.date.strftime("%Y-%m-%d") if "T" in raw and node.date.year > 1 else raw


def _card_visual(node: ContentNode, images: ImageIndex | None, eager: bool = False, draft: bool = False) -> str:
    """The 16:10 visual slot of a listing card.

    A `pictogram:` front-matter name wins (inline, animated, follows light/dark);
    else the item's preview image (shown whole, `contain`, unless its aspect is within
    ~10% of 16:10); else a first-letter tile so cards still align.
    """
    name = anthus_dom.node_pictogram(node)
    if name:
        return f'<div class="acard__vis acard__vis--px">{arcade_pictograms.render(name)}</div>'
    src = _preview(node, images) if images is not None else None
    if src:
        size = anthus_dom._dimensions(src)
        dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
        fit = " acard__vis--cover" if size and abs(size[0] / size[1] / 1.6 - 1) <= 0.10 else ""
        load = "eager" if eager else "lazy"
        decode = "" if draft else ' decoding="async"'  # draft cards are revealed late: decode synchronously
        return (
            f'<div class="acard__vis{fit}"><img src="{_esc(src)}" alt="" loading="{load}"{decode}{dims}></div>'
        )
    letter = next((c for c in node.title if c.isalnum()), "A").upper()
    return f'<div class="acard__vis acard__vis--letter" aria-hidden="true"><span>{escape(letter)}</span></div>'


def _text_card(
    node: ContentNode,
    images: ImageIndex | None = None,
    *,
    headline: bool = False,
    display_date: bool = False,
    month_year_date: bool = False,
    link: bool = True,
    code: bool = True,
    eager: bool = False,
    draft: bool = False,
) -> str:
    """The listing card: visual, mono date + tags, Jersey 25 title, clamped excerpt.

    `headline`: posts, whose excerpt is the headline (no separate excerpt).
    """
    tags = [t for t in node.tags if t not in _HIDDEN_TAGS][:2]
    if month_year_date:
        date = node.month_year_date
    elif display_date:
        date = node.display_date
    else:
        date = _short_date(node)
    meta = f"<time>{escape(date)}</time>" + "".join(f"<span>#{escape(t)}</span>" for t in tags)
    if draft:
        meta = '<span class="pill pill--draft">DRAFT</span>' + meta
    nofollow = ' rel="nofollow"' if draft else ""
    title = (node.excerpt_text.strip() or node.title) if headline else node.title
    target = str(node.front_matter.get("external_url") or blog_href(node))
    heading = f'<h3><a href="{_esc(target)}"{nofollow}>{escape(title)}</a></h3>' if link else f"<h3>{escape(title)}</h3>"
    excerpt = "" if headline else f'<p class="acard__ex">{escape(node.excerpt_text)}</p>'
    repository = _fm(node, "repository") if code else ""
    extra = ""
    if repository:
        label = repository.removeprefix("https://github.com/")
        extra = (
            '<div class="card__links"><a href="'
            f'{_esc(repository)}" target="_blank" rel="noopener noreferrer">Code: {escape(label)}</a></div>'
        )
    foot = '<span class="card__link" aria-hidden="true">Read</span>' if link else ""
    cls = "card--link" if link else "card--static"
    return (
        f'<li class="card notch acard {cls}">{_card_visual(node, images, eager, draft)}<div class="acard__body">'
        f'<p class="acard__meta">{meta}</p>{heading}{excerpt}{extra}{foot}</div></li>'
    )


def _drafts_section(drafts: list[ContentNode] | None, images: ImageIndex | None) -> str:
    """Hidden review section: shown only by `drafts.js` when the URL has `?drafts`. No UI links to it."""
    if not drafts:
        return ""
    cards = "".join(_text_card(n, images, code=False, draft=True) for n in drafts)
    return (
        '<section class="drafts-review" hidden><div class="container">'
        '<p class="eyebrow">NOT PUBLISHED</p><h2>Drafts</h2>'
        "<p>Served but hidden from search engines and from the normal lists.</p>"
        f'<ul class="grid grid--list">{cards}</ul></div></section>'
    )


def collection_page_path(base: str, page: int) -> str:
    """Production route of a collection page (rewritten by the link mapper)."""
    return f"/{base}/" if page == 1 else f"/{base}/page/{page}/"


def collection_nav(title: str, base: str, page: int, total: int) -> str:
    """The pagination `<nav>`, rendered only when there is more than one page."""
    if total <= 1:
        return ""
    previous = (
        f'<a href="{_esc(collection_page_path(base, page - 1))}">&larr; Previous</a>'
        if page > 1
        else "<span></span>"
    )
    following = (
        f'<a href="{_esc(collection_page_path(base, page + 1))}">Next &rarr;</a>'
        if page < total
        else "<span></span>"
    )
    return (
        f'<nav class="pager" aria-label="{escape(title)} pagination">'
        f"{previous}<span>Page {page} of {total}</span>{following}</nav>"
    )


def _links(items: list[tuple[str, str]]) -> str:
    return '<div class="card__links">' + "".join(
        f'<a href="{_esc(h)}">{escape(t)}</a>' for t, h in items
    ) + "</div>"

def _card(title: str, body_html: str, *, href: str = "", extra: str = "", cls: str = "", title_badge_html: str = "") -> str:
    """A plain notched card; with `href` the whole card is the click target."""
    head = (
        f'<h3><a href="{_esc(href)}">{escape(title)}</a>{title_badge_html}</h3>'
        if href
        else f"<h3>{escape(title)}{title_badge_html}</h3>"
    )
    return (
        f'<li class="card notch {cls}{" card--link" if href else " card--static"}">'
        f"{head}{body_html}{extra}</li>"
    )


# ------------------------------------------------------------------ the card hook

def _flags(text: str) -> dict:
    """``a,b=0`` is ``{"a": True, "b": "0"}``: the options of a card variant."""
    found = {}
    for part in filter(None, (piece.strip() for piece in text.split(","))):
        name, equals, value = part.partition("=")
        found[name] = value if equals else True
    return found


def _on(flags: dict, name: str, default: bool = False) -> bool:
    value = flags.get(name, default)
    return value not in ("0", "false", False)


def render_card(node: ContentNode, images: ImageIndex, variant: str | None, index: int) -> str:
    """One entry as the arcade design draws it. ``variant`` is ``name`` or ``name:option,option=value``.

    text   the listing card (visual, date and tags, title, excerpt); options: headline, display_date, month_year_date,
           link=0, code=0, grid (the first three cards load their image eagerly), draft
    mini   a small image card: image, date, title
    line   a dated link
    chip   the title as a chip
    """
    name, _, options = (variant or "text").partition(":")
    flags = _flags(options)
    if name == "text":
        return _text_card(
            node, images,
            headline=_on(flags, "headline"), display_date=_on(flags, "display_date"), month_year_date=_on(flags, "month_year_date"),
            link=_on(flags, "link", True), code=_on(flags, "code", True), eager=_on(flags, "grid") and index < 3, draft=_on(flags, "draft"),
        )
    if name == "mini":
        return (
            f'<li class="mini"><a href="{_esc(blog_href(node))}">{_card_visual(node, images)}'
            f"<time>{escape(node.display_date)}</time><span>{escape(node.title)}</span></a></li>"
        )
    if name == "line":
        return f'<li><time>{escape(node.display_date)}</time><a href="{_esc(blog_href(node))}">{escape(node.title)}</a></li>'
    if name == "chip":
        return f'<li><span class="chip">{escape(node.title)}</span></li>'
    raise ValueError(f"unknown card variant {variant!r}")
