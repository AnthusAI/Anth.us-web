"""The blocks pages include (``::include{kind="block" name="..."}``): generated markup the page files do not spell out."""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import anthus_dom
import arcade_pictograms
import cards
import inquiry_form
import product_availability_labels
import site_support as support
import solution_marks
from cards import _card, _esc, _fm, _links, blog_href, platform_href

_SOLUTION_EVIDENCE = {
    "Cyclotron": ("Built from Call Criteria", "/blog/call-criteria/"),
    "Papyrus": ("Anth.us runs on it", "/about/#loop"),
}

_SOLUTION_DESCRIPTIONS = {
    "Cyclotron": "It starts on day one with a decision model’s general training, refits a small model on each "
                 "correction, and lets an LLM propose better questions that code tests before they go live. "
                 "The loop is open source under the MIT license.",
    "Chatticus": "A collaborative workplace with named teammates, one shared computer, skills, routines, and human "
                 "approval boundaries.",
    "Papyrus": "Stories move through Kanbus-governed stages from pitch to draft to published, with a human editor "
               "approving each move. Anth.us runs its own newsroom on it, and the board is public.",
    "Auritus": "A drop-in embed that turns any page into speech with open models you choose, so visitors can listen "
               "instead of read.",
}

def _product_card(name: str, url: str, line: str, pictogram: str, page: str | None, *, describe: bool = False) -> str:
    also = f'<a href="{_esc(page)}">On anth.us</a>' if page else ""
    desc = f"<p>{escape(_SOLUTION_DESCRIPTIONS[name])}</p>" if describe and name in _SOLUTION_DESCRIPTIONS else ""
    if describe:
        # Evidence next to the ask: the engagement the solution came out of, then the way in.
        evidence = _SOLUTION_EVIDENCE.get(name)
        if evidence:
            also += f'<a href="{_esc(evidence[1])}">{escape(evidence[0])}</a>'
        also += f'<a href="/engage/?solution={quote(name)}">Work with us on {escape(name)}</a>'
    return (
        f'<li class="card notch product card--static{" product--desc" if desc else ""}">'
        f'<div class="card__px">{_px(pictogram)}</div><h3 class="product__name">{escape(name)}{solution_marks.mark(name)}{product_availability_labels.availability_chip_markup(name)}</h3>'
        f'<p>{escape(line)}</p>{desc}'
        f'<div class="card__links"><a href="{_esc(url)}" rel="noopener">Visit {escape(name)}</a>{also}</div></li>'
    )

def _products_grid(*, describe: bool = False) -> str:
    return '<ul class="grid grid--products">' + "".join(
        _product_card(*p, describe=describe) for p in anthus_dom.PRODUCTS
    ) + "</ul>"

def _supporting_row() -> str:
    noopener = ' rel="noopener"'
    links = " ".join(
        f'<a href="{_esc(href)}"{noopener if ext else ""}>{escape(name)}</a>{product_availability_labels.availability_chip_markup(name)}'
        for name, href, _line, ext in anthus_dom.SUPPORTING
    )
    return f'<p class="supporting"><strong>Supporting technology</strong> {links}</p>'

def _pills(node: ContentNode) -> str:
    items = [_fm(node, k) for k in ("platform_category", "platform_stage") if _fm(node, k)]
    return '<ul class="pills">' + "".join(f'<li class="pill">{escape(i)}</li>' for i in items) + "</ul>" if items else ""

def _platform_line(node: ContentNode) -> str:
    """Compact entry for the least prominent tier on /platform/: name and one line."""
    return (
        f'<li><a href="{_esc(platform_href(node))}">{escape(node.title)}</a>{product_availability_labels.availability_chip_markup(node.title)} '
        f"{escape(_fm(node, 'excerpt'))}</li>"
    )

def _px(name: str) -> str:
    """Inline pictogram. An unknown name fails the build (no placeholder frames in production)."""
    if name not in arcade_pictograms.NAMES:
        raise KeyError(f"unknown pictogram {name!r}; known: {', '.join(arcade_pictograms.NAMES)}")
    return arcade_pictograms.render(name)


def supporting_cards() -> str:
    return '<ul class="grid grid--thirds">' + "".join(
        _card(
            name, f"<p>{escape(line)}</p>",
            title_badge_html=product_availability_labels.availability_chip_markup(name),
            extra=_links(
                ([("Visit " + name, href)] if ext else [])
                + ([("On anth.us", f"/platform/{name.lower()}/")] if name in anthus_dom.SUPPORTING_PAGES else [])
            ),
        )
        for name, href, line, ext in anthus_dom.SUPPORTING
    ) + "</ul>"


def further_reading(page) -> str:
    """The six newest projects and featured articles: the solutions that are neither engagements nor integrations,
    the published articles tagged ``project``, and the published articles tagged ``featured``."""
    blog = support.collections(page.site).blog
    solutions = [n for n in blog if "solutions" in n.tags and not n.draft]
    projects = {n.slug: n for n in solutions if "engagement" not in n.tags and "integrations" not in n.tags}
    projects.update({n.slug: n for n in blog if n.published and "project" in n.tags})
    featured = {
        n.slug: n for n in blog
        if n.published and "featured" in n.tags and not n.is_platform and not ({"solutions", "posts"} & set(n.tags))
    }
    newest = sorted(list({**projects, **featured}.values()), key=lambda n: n.date, reverse=True)[:6]
    return "".join(f'<li><time>{escape(n.month_year_date)}</time><a href="{_esc(blog_href(n))}">{escape(n.title)}</a></li>' for n in newest)


def platform_lines(page) -> str:
    """The platform pages that are not the flagship, in ``platform_order``."""
    platform = support.collections(page.site).platform
    return "".join(_platform_line(n) for n in platform if n.slug not in {"biblicus"})


BLOCKS = {
    "pictogram": lambda attributes, page: _px(attributes["id"]),
    "products-grid": lambda attributes, page: _products_grid(describe=attributes.get("describe") == "1"),
    "supporting-row": lambda attributes, page: _supporting_row(),
    "supporting-cards": lambda attributes, page: supporting_cards(),
    "further-reading": lambda attributes, page: further_reading(page),
    "platform-lines": lambda attributes, page: platform_lines(page),
    "inquiry-form": lambda attributes, page: inquiry_form.render(),
}


def render(name: str, attributes: dict, page) -> str:
    if name not in BLOCKS:
        raise KeyError(f"no block named {name!r}; known: {', '.join(sorted(BLOCKS))}")
    return BLOCKS[name](attributes, page)
