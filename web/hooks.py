"""Anth.us named hooks for the standard Papyrus front end (web/projection.json names this module).

The site is the production Anth.us DOM and stylesheet (DESIGN.md), so what the hooks do is dress the standard
projector's pages in it: staging an article (heading block, closing call to action), the class vocabulary of the
converted fragment, the image wrapper, the page envelope (header, footer), cards, the head description of a page,
and the last text pass (canonical links).
"""

from __future__ import annotations

import dataclasses
import re
from html import unescape

import anthus_dom as dom
import site_support as support
import source_text
from papyrus_content.markus_renderer.images import DEFAULT_LAYOUT_SIZES
from papyrus_content.markus_renderer.transforms import FragmentTransform, block_sentinel

import cards
import links
import platform_product
import site_blocks
import view

#: Nothing is read beyond the page itself and the entries it shows, except the URL map item pages rewrite their links with.
DEPENDS_ON = {"*": [], "item": []}

ITEM_TRANSFORM = FragmentTransform(
    strip_header=True, allow_block_passthrough=True, class_map=dom.CLASS_MAP, drop_unmapped_classes=dom.DROP_PREFIXES
)


def item_filter(summary):
    return summary.section in support.SECTIONS and not support.lives_elsewhere(summary)


def source(summary, text, site):
    node = support.node_of(site, summary)
    front, body = source_text.split(text)
    body = source_text.clean(body)
    if node.rel_dir == "platform":
        tail = platform_product.platform_product_tail(node)
        document = block_sentinel(platform_product.platform_product_head(node)) + "\n\n" + body + ("\n\n" + block_sentinel(tail) + "\n" if tail else "")
    else:
        header = block_sentinel(dom.article_heading(node).html()) + "\n\n"
        cta = "\n\n" + block_sentinel(dom.ENGAGE_CTA_HTML) + "\n" if "client-acquisition" in node.tags else ""
        document = header + body + cta
    return front + document


def item_transform(summary):
    return ITEM_TRANSFORM


def image_pipeline(pipeline):
    return dataclasses.replace(
        pipeline,
        wrap=dom.anthus_image_wrap,
        layout_sizes=dom.anthus_layout_sizes(DEFAULT_LAYOUT_SIZES),
        eager_first=1000,
        upgrade_plain_images=False,
    )


def page_inputs(site):
    return links.url_map(site).fingerprint()


def redirects(site):
    return links.legacy_redirects(site)


# ------------------------------------------------------------------ the page


def page_head(head, page):
    return view.page_head(head, page)


def page_body(page):
    return view.body(page)


def page_finish(html, page):
    return view.finish(html, page)


def card(entry, page, variant=None, index=0):
    return cards.render_card(support.node_of(page.site, entry.summary), support.images(page.site), variant, index)


def block(name, attributes, page):
    return site_blocks.render(name, attributes, page)
