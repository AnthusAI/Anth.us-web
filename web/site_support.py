"""Shared helpers of the Anth.us hooks: items seen as the arcade templates expect them, the site's image index and URL map.

Everything here is derived from the site (``HookSite``) of one projection and memoised on it, so a projection of one
item reads the rendition records once and a listing never reads an item body.
"""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath

import anthus_dom as dom
import anthus_urls as urls
from anthus_content import Collections, ContentNode, ImageIndex, _slugify
from solution_sites import is_external, is_folded

WEB = Path(os.environ.get("PAPYRUS_SITE_STATIC_DIR") or Path(__file__).resolve().parent)
CONTENT_ROOT = Path(os.environ.get("ANTHUS_BUILD_DIR", "/tmp/build")) / "content-root-projector"
SITE_ASSETS = WEB / "assets" / "site"
SECTIONS = ("articles", "platform")


def node_for(summary) -> ContentNode:
    """The item as the arcade templates know it: front matter, slug, the section it lives in."""
    stem = PurePosixPath(summary.output_path).stem
    relative_directory = "platform" if summary.section == "platform" else ""
    relative = f"platform/{stem}.mdx" if relative_directory else f"{stem}.mdx"
    slug = _slugify(str(summary.front_matter.get("slug") or "").strip() or stem)
    return ContentNode(slug=slug, source=CONTENT_ROOT / relative, front_matter=summary.front_matter, rel_dir=relative_directory)


def lives_elsewhere(summary) -> bool:
    """Items with their own site, or folded into another page, get no page here (redirects and link rewrites only)."""
    slug = node_for(summary).slug
    return is_external(slug) if summary.section == "platform" else is_folded(slug)


def nodes(site) -> list[ContentNode]:
    return site.memo("nodes", lambda: sorted(
        (node_for(summary) for summary in site.items if summary.section in SECTIONS), key=lambda node: node.source
    ))


def node_of(site, summary) -> ContentNode:
    by_item = site.memo("node_by_item", lambda: {summary.item_id: node_for(summary) for summary in site.items})
    return by_item[summary.item_id]


def collections(site) -> Collections:
    return site.memo("collections", lambda: Collections.from_nodes(nodes(site)))


def images(site) -> ImageIndex:
    """The images the site has (the rendition records of its store), and where to measure them."""
    def build() -> ImageIndex:
        records = site.rendition_records()
        index = ImageIndex.from_sources([record["source"] for record in records], content_root=CONTENT_ROOT, site_assets=SITE_ASSETS)
        dom.set_asset_roots({"/assets/content/": CONTENT_ROOT, "/assets/site/": SITE_ASSETS})
        dom._DIMENSION_CACHE.update({"/assets/content/" + record["source"]: tuple(record["size"]) for record in records if record["size"]})
        return index

    return site.memo("images", build)


def page_directory(path: str) -> str:
    """The directory a page is written in (``articles/x`` for ``/articles/x/``): the base its relative links were made against."""
    path = path.split("?", 1)[0]
    stripped = path.strip("/")
    return stripped if path.endswith("/") else stripped.rpartition("/")[0]
