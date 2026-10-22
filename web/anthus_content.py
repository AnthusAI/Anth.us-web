"""The content of Anth.us as the arcade templates see it: an item as a ``ContentNode``, the sets of nodes each page lists,
and the image index. Nodes are made from the projection's item summaries (``site_support.node_for``), never from files.

Routing note: Gatsby served every non-platform MDX node at ``/blog/<slug>/``; this site serves it at ``/articles/<slug>/``
and every legacy URL shape 301s onto it. ``anthus_urls`` owns that map and the URL shape itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from pathlib import Path

from solution_sites import is_external, is_folded

def html_to_text(value: str | None) -> str:
    """Flatten an HTML-bearing scalar (``excerpt``, ``author``) to plain text.

    Anth.us excerpts are stored as HTML (``<p>``, ``<ul>``, ``<a>``, ``<mark>``) because Gatsby injected them with
    ``dangerouslySetInnerHTML``. Card blurbs and ``<meta>`` descriptions need the text, not the markup.
    """
    if not value:
        return ""
    text = re.sub(r"<li\b[^>]*>", " • ", value)
    text = re.sub(r"</(p|div|ul|ol|li|h[1-6])>", " ", text)
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


POSTS_PER_PAGE = 12  # matches gatsby-node.js

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}

@dataclass
class ContentNode:
    """One MDX source file, classified the way ``gatsby-node.js`` classifies it."""

    slug: str
    source: Path
    front_matter: dict
    rel_dir: str  # "", "posts", "solutions", "platform"

    @property
    def authored_slug(self) -> str:
        """The slug exactly as written in front matter, before normalization.

        Kept so a redirect stub can be emitted at the URL the live Gatsby site
        serves, which preserves capitalization.
        """
        return str(self.front_matter.get("slug") or self.source.stem).strip()

    @property
    def title(self) -> str:
        return str(self.front_matter.get("title") or self.slug.replace("-", " ").title())

    @property
    def tags(self) -> list[str]:
        raw = self.front_matter.get("tags") or []
        if isinstance(raw, str):
            return [raw]
        return [str(tag) for tag in raw]

    @property
    def state(self) -> str:
        return str(self.front_matter.get("state") or "")

    @property
    def published(self) -> bool:
        return self.state == "published"

    @property
    def draft(self) -> bool:
        """`state: draft`: served, but noindexed and left out of every normal listing."""
        return self.state == "draft"

    @property
    def is_platform(self) -> bool:
        return (
            self.front_matter.get("content_type") == "platform-product"
            or self.rel_dir == "platform"
        )

    @property
    def excerpt_text(self) -> str:
        return html_to_text(self.front_matter.get("excerpt"))

    @property
    def date_raw(self) -> str:
        return str(self.front_matter.get("date") or "").strip()

    @property
    def date(self) -> datetime:
        return parse_date(self.date_raw)

    @property
    def formatted_date(self) -> str:
        """`formatPostDate(date)`: always the parsed date, never `display_date`."""
        parsed = self.date
        return parsed.strftime("%B %-d, %Y") if parsed != datetime.min else self.date_raw

    @property
    def display_date(self) -> str:
        explicit = self.front_matter.get("display_date")
        if explicit:
            return str(explicit)
        parsed = self.date
        return parsed.strftime("%B %-d, %Y") if parsed != datetime.min else self.date_raw

    @property
    def month_year_date(self) -> str:
        parsed = self.date
        return parsed.strftime("%B %Y") if parsed != datetime.min else self.date_raw

    @property
    def author_names(self) -> list[str]:
        """Plain-text author names (the authored values may carry markup)."""
        return [
            html_to_text(entry.get("author"))
            for entry in (self.front_matter.get("authors") or [])
            if isinstance(entry, dict) and entry.get("author")
        ]


def parse_date(raw: str) -> datetime:
    """Tolerant date parse. Unknown shapes sort last rather than crash the build."""
    raw = (raw or "").strip().strip("\"'")
    if not raw:
        return datetime.min
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y", "%Y-%m"):
        try:
            return datetime.strptime(raw[: len(fmt) + 8] if "T" in fmt else raw, fmt)
        except ValueError:
            continue
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return datetime.min


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "untitled"


# --------------------------------------------------------------------------
# Image index
# --------------------------------------------------------------------------


@dataclass
class ImageIndex:
    """Resolve the image an item names (``preview_image:``) to the URL of its listing copy.

    The images the site has are known by their rendition records (``HookSite.rendition_records``), not by files.
    A path is looked up relative to the item first (items live at the content root, platform items one level
    down), then by file name; site chrome (``assets/site``) is found by name too.
    """

    content_root: Path
    site_assets: Path
    by_relpath: dict[str, Path] = field(default_factory=dict)
    by_basename: dict[str, Path] = field(default_factory=dict)
    site_by_name: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def from_sources(cls, sources, *, content_root: Path, site_assets: Path) -> "ImageIndex":
        """``by_basename`` takes the first of the sorted sources for a basename that two directories share."""
        index = cls(content_root=content_root, site_assets=site_assets)
        for source in sorted(sources):
            index.by_relpath[source] = content_root / source
            index.by_basename.setdefault(Path(source).name, content_root / source)
        if site_assets.is_dir():
            for path in sorted(site_assets.rglob("*")):
                if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES:
                    index.site_by_name.setdefault(path.name, path)
        return index

    def resolve_name(self, name: str) -> str | None:
        name = (name or "").strip()
        if not name:
            return None
        base = name.split("/")[-1]
        path = self.by_basename.get(base)
        if path:
            return "/assets/content/" + path.relative_to(self.content_root).as_posix()
        site = self.site_by_name.get(base)
        if site:
            return "/assets/site/" + site.relative_to(self.site_assets).as_posix()
        return None

    def resolve_path(self, src: str, *, relative_to: Path | None = None) -> str | None:
        src = (src or "").strip()
        if not src:
            return None
        if src.startswith(("http://", "https://", "data:")):
            return src
        if relative_to is not None and not src.startswith("/"):
            candidate = (relative_to.parent / src).resolve()
            try:
                rel = candidate.relative_to(self.content_root.resolve()).as_posix()
            except ValueError:
                rel = None
            if rel and rel in self.by_relpath:
                return "/assets/content/" + rel
        return self.resolve_name(src)


# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------


@dataclass
class Collections:
    """The node sets each Gatsby page/template queried for, computed once."""

    all_nodes: list[ContentNode]
    platform: list[ContentNode]
    blog: list[ContentNode]
    articles: list[ContentNode]
    posts: list[ContentNode]
    solutions: list[ContentNode]
    tags: dict[str, list[ContentNode]]
    #: platform nodes that live on their own site: no page here, only redirects and link rewrites.
    external_platform: list[ContentNode] = field(default_factory=list)
    #: `state: draft` items (not platform): served and noindexed, listed only in the hidden review sections.
    drafts: list[ContentNode] = field(default_factory=list)
    #: items folded into another page (`solution_sites.FOLDED_INTO`): no page, redirects and link rewrites only.
    folded: list[ContentNode] = field(default_factory=list)

    @classmethod
    def from_nodes(cls, nodes: list[ContentNode]) -> "Collections":
        # Date descending; ties in ascending filename order (what live production
        # shows, measured against its listings).
        by_date = sorted(sorted(nodes, key=lambda n: n.source.name), key=lambda n: n.date, reverse=True)
        every_platform = [n for n in by_date if n.is_platform]
        platform = [n for n in every_platform if not is_external(n.slug)]
        external_platform = [n for n in every_platform if is_external(n.slug)]
        every_blog = [n for n in by_date if not n.is_platform]
        folded = [n for n in every_blog if is_folded(n.slug)]
        blog = [n for n in every_blog if not is_folded(n.slug)]
        # blog.jsx: published, tags nin [solutions, posts], not platform.
        articles = [
            n
            for n in blog
            if n.published and not ({"solutions", "posts"} & set(n.tags))
        ]
        # posts-list.jsx: published and tagged posts.
        posts = [n for n in blog if n.published and "posts" in n.tags]
        # ai-solutions.js: tagged solutions (state not filtered, matching Gatsby).
        solutions = [n for n in blog if "solutions" in n.tags and not n.draft]
        drafts = [n for n in blog if n.draft]
        tags: dict[str, list[ContentNode]] = {}
        for node in blog:
            if node.draft:
                continue
            for tag in node.tags:
                tags.setdefault(tag, []).append(node)
        platform.sort(
            key=lambda n: (
                int(n.front_matter.get("platform_order") or 9999),
                n.title,
            )
        )
        return cls(
            all_nodes=[n for n in by_date if not is_folded(n.slug)],
            platform=platform,
            blog=blog,
            articles=articles,
            posts=posts,
            solutions=solutions,
            tags=tags,
            external_platform=external_platform,
            drafts=drafts,
            folded=folded,
        )
