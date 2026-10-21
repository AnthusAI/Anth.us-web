"""The listing pages: a collection (articles, posts, reading list, research), a tag page and the tag index."""

from __future__ import annotations

from html import escape

import cards
import site_support as support

BARE = cards.BARE
#: Per collection: eyebrow, heading, the card options (and whether the lead is the collection's description).
COLLECTIONS = {
    "articles": ("ARTICLES", None, "text:code=0,grid"),
    "posts": ("POSTS", None, "text:headline,code=0,grid"),
    "reading": ("WHAT WE READ", "Reading list", "text:grid"),
    "research": ("EXPERIMENTS", "Research", "text:grid"),
}
RESEARCH_LEAD = (
    "Jev, Laya and the rest of the field-coverage roster answer millions of bounded "
    "questions a day, so we run the experiments that check what they’re actually doing: "
    "where their verdicts move on a name or a pronoun, how well their confidence tracks "
    "reality, and what survives when you fine-tune, distill or gate them. Every piece here "
    "comes with the method and the numbers, not just the headline. If you’re here to align "
    'Jev or another decision model to your own data, start with the '
    '<a href="/decision-models/">guide to aligning decision models</a>.'
)


def _nodes(page, entries):
    return [support.node_of(page.site, entry.summary) for entry in entries]


def _grid(nodes, images, variant):
    if not nodes:
        return ""
    return '<ul class="grid grid--list">' + "".join(cards.render_card(node, images, variant, index) for index, node in enumerate(nodes)) + "</ul>"


def collection(page) -> str:
    view = page.listing
    eyebrow, heading, variant = COLLECTIONS[view.collection]
    images = support.images(page.site)
    config = page.settings.collection(view.collection)
    title = heading or view.label
    single = view.collection in ("reading", "research")
    lead = RESEARCH_LEAD if view.collection == "research" else escape(config.description)
    if single:
        assert view.pages == 1, f"{view.base} outgrew one page"
        hero = cards._page_hero(eyebrow, title, lead, compact=True)
        nav = ""
    else:
        hero = cards._page_hero(eyebrow, view.label if view.page == 1 else f"{view.label}, page {view.page}", lead, compact=True)
        nav = cards.collection_nav(view.label, view.base, view.page, view.pages)
    body = (
        '<section class="section section--tight"><div class="container">'
        + _grid(_nodes(page, view.entries), images, variant)
        + nav
        + "</div></section>"
    )
    drafts = _nodes(page, view.drafts)
    return BARE + hero + body + (cards._drafts_section(drafts, images) if view.page == 1 else "")


def merged_tags(page) -> dict[str, tuple[str, list]]:
    """slug -> (label, nodes): case variants of one tag are one tag, labelled with the spelling most pieces use."""
    merged: dict[str, tuple[str, list]] = {}
    for tag, nodes in support.collections(page.site).tags.items():
        slug = cards.tag_slug(tag)
        label, existing = merged.get(slug, (tag.strip(), []))
        combined = {node.slug: node for node in existing}
        combined.update({node.slug: node for node in nodes})
        if len(nodes) > len(existing):
            label = tag.strip()
        merged[slug] = (label, list(combined.values()))
    return merged


def tag(page) -> str:
    slug = page.path.strip("/").split("/")[-1]
    label, nodes = merged_tags(page)[slug]
    ordered = sorted(nodes, key=lambda node: (node.date, node.slug), reverse=True)
    images = support.images(page.site)
    return BARE + cards._page_hero(
        "TAG", f"Tagged: {label}",
        f'{len(ordered)} {"article" if len(ordered) == 1 else "articles"}. <a href="/tags/">All tags</a>.',
        compact=True, cursor=False,
    ) + (
        '<section class="section section--tight"><div class="container">'
        + _grid(ordered, images, "text:code=0,grid")
        + "</div></section>"
    )


def tag_index(page) -> str:
    cloud = "".join(
        f'<li><a class="chip" href="/tags/{cards._esc(slug)}/">{escape(label)}<small>{len(nodes)}</small></a></li>'
        for slug, (label, nodes) in sorted(merged_tags(page).items())
    )
    return BARE + cards._page_hero(
        "TOPICS", "Tags", "Every topic we write about, with the number of pieces under each.", compact=True
    ) + f'<section class="section section--tight"><div class="container"><ul class="chips">{cloud}</ul></div></section>'
