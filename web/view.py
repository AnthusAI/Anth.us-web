"""The Anth.us page: its head description, its envelope (header, footer, container) and its finishing pass."""

from __future__ import annotations

import dataclasses
import re
from html import escape, unescape

import anthus_dom as dom
import cards
import listings
import site_support as support
import links
from papyrus_content.markus_renderer.images import FADE_IN_SCRIPT
from papyrus_content.projection.standard.markdown import md_path
from papyrus_content.projection.standard.page_actions import render_page_actions

SITE_TITLE = "Anthus"
SITE_DESCRIPTION = (
    "Anthus builds self-aligning AI systems: custom models, agent harnesses, "
    "evaluation loops, and unattended automation with a human in the loop, "
    "grounded in production operations since 2007."
)
_CELL_ALIGN = re.compile(r'<(th|td) style="text-align:(?:left|right|center)">')


def route(page) -> str:
    """The production-shaped route the navigation matches: the articles index is /blog/ there."""
    return {"/articles/": "/blog/"}.get(page.path, page.path)


def templated(title: str) -> str:
    return SITE_TITLE if title.strip() == SITE_TITLE else f"{title} | {SITE_TITLE}"


# ------------------------------------------------------------------ head


def page_head(head, page):
    entry = page.entry
    if page.kind == "item" and entry is not None:
        node = support.node_of(page.site, entry.summary)
        images = support.images(page.site)
        preview = cards._preview(node, images) or links.pictogram_og(node) if node.rel_dir != "platform" else cards._preview(node, images)
        published = node.published and node.rel_dir != "platform"
        return dataclasses.replace(
            head,
            title=templated(entry.title),
            headline=node.title,
            description=node.excerpt_text or SITE_DESCRIPTION,
            image=preview or links.DEFAULT_COVER,
            og_type="article" if published else "website",
            json_ld_type="Article" if published else None,
            published=node.date_raw if published else "",
            modified="",
            authors=tuple(node.author_names) if published else (),
            tags=(),
            canonical=None,
            breadcrumbs=(),
        )
    return dataclasses.replace(head, title=templated(head.title), description=head.description or SITE_DESCRIPTION)


# ------------------------------------------------------------------ body


def body(page) -> str:
    """Everything between ``<body>`` and the scripts."""
    path = route(page)
    fragment = page_actions(page) + page.fragment if page.kind == "item" else main(page)
    return dom.render_envelope(fragment=fragment, route=path, scripts="", guarded=page.environment.guarded)


def page_actions(page) -> str:
    """Copy / view / open-in actions above an article: the site lays out its own body, so it asks core's renderer for them.

    The same eligibility as core's own article pages: switched on, Markdown twins published, a listed type, indexable.
    """
    settings, entry = page.settings, page.entry
    if not (settings.page_actions.enabled and settings.agents.markdown) or entry is None or entry.noindex:
        return ""
    if entry.type not in settings.listings.types or entry.key is None:
        return ""
    twin = md_path(entry.key)
    origin = page.environment.origin
    canonical = entry.canonical or (origin + entry.url if origin and entry.url else None)
    if twin is None:
        return ""
    return render_page_actions(settings.page_actions, markdown_path=twin, title=entry.title, canonical=canonical)


def main(page) -> str:
    """The inner HTML of ``<main>`` of a generated page; pages start with the marker that says they lay out their own sections."""
    if page.kind in ("custom", "not_found"):
        return dom.BARE_MARKER + page.fragment
    if page.kind == "listing":
        return listings.collection(page)
    if page.kind == "tag":
        return listings.tag(page)
    if page.kind == "tags":
        return listings.tag_index(page)
    raise ValueError(f"no page body for {page.kind} {page.path}")


# ------------------------------------------------------------------ finish


def finish(html: str, page) -> str:
    mapping = links.url_map(page.site)
    html = mapping.rewrite(html, base_dir=support.page_directory(page.path))
    html = html.replace('<body class="">', "<body>", 1)
    html = _CELL_ALIGN.sub(r"<\1>", html)
    if "twitter-tweet" in html and "platform.twitter.com/widgets.js" not in html:
        html = html.replace("</head>", '<script src="https://platform.twitter.com/widgets.js"></script>\n</head>', 1)
    if "data-main-image" in page.fragment:
        html = html.replace("</body>", f"<script>{FADE_IN_SCRIPT}</script></body>", 1) if "</body>" in html else html
    dom.assert_no_markus_classes(html, page.path)
    return html
