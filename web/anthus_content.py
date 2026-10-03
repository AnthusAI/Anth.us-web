"""Discover, classify, and stage Anth.us content for the Markus build.

The content submodule (``content/anthus-site-content``) is the same repo the
live Gatsby site renders from, and is treated as strictly read-only. This
module reads it and writes a derived Markdown tree into ``web/staging/``
(gitignored) laid out the way Papyrus's Markus renderer expects:

    web/staging/
      index.md              homepage
      about.md              bespoke pages (depth 0, rendered standalone)
      ai-solutions.md
      ryan.md
      404.md
      articles/             blog corpus + archive index  (depth 1)
      platform/             platform overview + products (depth 1)
      posts/                paginated short-post listings (depth 1)
      tags/                 one page per tag             (depth 1)
      assets/content/…      referenced images, downscaled
      assets/site/…         committed site-chrome images

Routing note (parity gap, deliberate)
-------------------------------------
Gatsby serves every non-platform MDX node at ``/blog/<slug>/``. Papyrus's
``build_markus_site`` hard-requires the primary collection to live in
``content/articles/``, so the canonical path here is ``/articles/<slug>.html``.
``build_via_papyrus.py`` emits ``/blog/<slug>.html`` redirect stubs so inbound
links to the live site's URLs still resolve, and rewrites in-content
``/blog/…`` links to the canonical path. Changing the collection directory name
would be a change to Papyrus, which this repo does not own.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from anthus_mdx import (
    ConversionReport,
    html_to_inline_markdown,
    html_to_text,
    normalize_body,
    split_front_matter,
    staged_markdown,
    write_if_changed,
)

POSTS_PER_PAGE = 12  # matches gatsby-node.js
DEFAULT_AUTHOR_MD = "[Ryan Porter](/ryan)"

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}
_MAX_IMAGE_WIDTH = 1600

# Files the Gatsby config ignores; mirror that so review notes and image briefs
# never become pages.
_IGNORED_NAMES = re.compile(r"(?:README\.md|\.IMAGE\.(?:md|txt)|\.STYLE-NOTES\.(?:md|txt))$")


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
    def display_date(self) -> str:
        explicit = self.front_matter.get("display_date")
        if explicit:
            return str(explicit)
        parsed = self.date
        return parsed.strftime("%B %-d, %Y") if parsed != datetime.min else self.date_raw

    @property
    def byline(self) -> str:
        authors = self.front_matter.get("authors") or []
        names = [
            html_to_inline_markdown(entry.get("author"))
            for entry in authors
            if isinstance(entry, dict) and entry.get("author")
        ]
        names = [name for name in names if name]
        if not names:
            names = [DEFAULT_AUTHOR_MD]
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return ", ".join(names[:-1]) + f", and {names[-1]}"


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


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def discover(content_root: Path) -> list[ContentNode]:
    """Collect every MDX node in the content submodule.

    Mirrors ``gatsby-source-filesystem``'s ignore list. Drafts living outside
    the submodule (``Anth.us/src/drafts``) are not visible here by design —
    they are not part of the content repo, so this port cannot and does not
    publish them.
    """
    nodes: list[ContentNode] = []
    for path in sorted(content_root.rglob("*.mdx")):
        if ".git" in path.parts:
            continue
        if _IGNORED_NAMES.search(path.name):
            continue
        rel = path.relative_to(content_root)
        rel_dir = rel.parts[0] if len(rel.parts) > 1 else ""
        if rel_dir in {"images", "diagrams", "redirects", ".github"}:
            continue
        front_matter, _ = split_front_matter(path.read_text(encoding="utf-8"))
        slug = str(front_matter.get("slug") or "").strip()
        if not slug:
            slug = path.stem
        # Papyrus's collection discovery only accepts `^[a-z0-9][a-z0-9-]*\.md$`,
        # so a node whose front-matter slug has capitals (e.g. `Paytronix`) was
        # staged and then silently skipped at render time — a missing page with
        # a successful build. Normalize here and keep the authored spelling for
        # the redirect stub.
        slug = _slugify(slug)
        nodes.append(
            ContentNode(
                slug=slug,
                source=path,
                front_matter=front_matter,
                rel_dir=rel_dir,
            )
        )
    return nodes


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "untitled"


# --------------------------------------------------------------------------
# Image index
# --------------------------------------------------------------------------


@dataclass
class ImageIndex:
    """Resolve authored image references to staged asset paths.

    Two lookup modes, because the content uses two conventions:

    * ``<BlogImage name="x.png">`` gives a bare basename and relies on
      Gatsby's ``allFile`` query to find it anywhere in the graph.
    * ``<img src="../images/x.png">`` and ``preview_image:`` give a path,
      sometimes relative to the MDX file and sometimes site-absolute
      (``/assets/images/…``, ``/images/…``) pointing at files that live in the
      **Anth.us** repo's ``static/`` directory rather than the content repo.
      Those are vendored into ``web/assets/site/`` in this repo.

    And two *output* modes, because there are now two image paths:

    * ``content_src()`` returns a path **relative to the content submodule**,
      which is what ``::image{}`` needs: Papyrus's ``ImagePipeline`` is pointed
      at the submodule as its source root and generates the renditions itself,
      so nothing has to be copied or pre-downscaled. Used for article bodies.
    * ``resolve_name()`` / ``resolve_path()`` return a **staged asset URL**
      (``/assets/content/…``) and record the file for ``stage()`` to copy.
      Used for listing-card thumbnails and site chrome, which are emitted as
      plain Markdown images by ``anthus_pages`` and are not responsive.
    """

    content_root: Path
    site_assets: Path
    by_relpath: dict[str, Path] = field(default_factory=dict)
    by_basename: dict[str, Path] = field(default_factory=dict)
    site_by_name: dict[str, Path] = field(default_factory=dict)
    used: set[Path] = field(default_factory=set)
    used_site: set[Path] = field(default_factory=set)
    missing: set[str] = field(default_factory=set)

    @classmethod
    def build(cls, content_root: Path, site_assets: Path) -> "ImageIndex":
        index = cls(content_root=content_root, site_assets=site_assets)
        for path in content_root.rglob("*"):
            if ".git" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() not in _IMAGE_SUFFIXES:
                continue
            rel = path.relative_to(content_root).as_posix()
            index.by_relpath[rel] = path
            # First writer wins so a deterministic file is chosen when two
            # directories hold the same basename.
            index.by_basename.setdefault(path.name, path)
        if site_assets.is_dir():
            for path in site_assets.rglob("*"):
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
            self.used.add(path)
            return "/assets/content/" + path.relative_to(self.content_root).as_posix()
        site = self.site_by_name.get(base)
        if site:
            self.used_site.add(site)
            return "/assets/site/" + site.relative_to(self.site_assets).as_posix()
        self.missing.add(name)
        return None

    def content_src(self, src: str, *, relative_to: Path | None = None) -> str | None:
        """A ``::image{src=}`` value: relative to the content submodule root.

        Falls back to a staged ``/assets/site/…`` URL for the handful of
        site-chrome images the content references by absolute path
        (``<img src="/images/sqlbot-arch-1.png">``), which live in the Anth.us
        repo rather than here and so have no path under the pipeline's source
        root. ``anthus_mdx`` emits those as a plain ``:::figure`` instead.
        """
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
                return rel
        base = src.split("/")[-1]
        path = self.by_basename.get(base)
        if path:
            return path.relative_to(self.content_root).as_posix()
        site = self.site_by_name.get(base)
        if site:
            self.used_site.add(site)
            return "/assets/site/" + site.relative_to(self.site_assets).as_posix()
        self.missing.add(src)
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
                self.used.add(self.by_relpath[rel])
                return "/assets/content/" + rel
        return self.resolve_name(src)

    # -- staging ----------------------------------------------------------

    def stage(self, staging_assets: Path) -> tuple[int, int]:
        """Copy only the referenced images, downscaled, into the staging tree.

        Copying the whole content image tree would ship ~313 MB of originals,
        most of them unreferenced, and serve multi-megabyte PNGs at thumbnail
        size — Gatsby's sharp pipeline is what hid that today. Until the
        responsive-image pipeline lands, cap the long edge at
        ``_MAX_IMAGE_WIDTH`` and copy nothing that no page asks for.
        """
        copied = downscaled = 0
        for path in sorted(self.used):
            rel = path.relative_to(self.content_root).as_posix()
            dest = staging_assets / "content" / rel
            if _copy_image(path, dest):
                downscaled += 1
            copied += 1
        for path in sorted(self.used_site):
            rel = path.relative_to(self.site_assets).as_posix()
            dest = staging_assets / "site" / rel
            if _copy_image(path, dest):
                downscaled += 1
            copied += 1
        return copied, downscaled


def _copy_image(source: Path, dest: Path) -> bool:
    """Copy one image, downscaling raster originals. Returns True if resized."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_mtime >= source.stat().st_mtime:
        return False
    if source.suffix.lower() in {".svg", ".gif"}:
        # SVG is resolution-independent; animated GIF frames do not survive a
        # naive Pillow resize, so both are copied verbatim.
        shutil.copy2(source, dest)
        return False
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(source, dest)
        return False
    try:
        with Image.open(source) as image:
            if image.width <= _MAX_IMAGE_WIDTH:
                shutil.copy2(source, dest)
                return False
            height = round(image.height * _MAX_IMAGE_WIDTH / image.width)
            resized = image.resize((_MAX_IMAGE_WIDTH, height), Image.LANCZOS)
            if resized.mode in {"P", "RGBA"} and dest.suffix.lower() in {".jpg", ".jpeg"}:
                resized = resized.convert("RGB")
            resized.save(dest)
            return True
    except Exception:
        # A corrupt or exotic file must not fail the whole build; ship the
        # original and let the size report show it.
        shutil.copy2(source, dest)
        return False


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

    @classmethod
    def from_nodes(cls, nodes: list[ContentNode]) -> "Collections":
        by_date = sorted(nodes, key=lambda n: (n.date, n.slug), reverse=True)
        platform = [n for n in by_date if n.is_platform]
        blog = [n for n in by_date if not n.is_platform]
        # blog.jsx: published, tags nin [solutions, posts], not platform.
        articles = [
            n
            for n in blog
            if n.published and not ({"solutions", "posts"} & set(n.tags))
        ]
        # posts-list.jsx: published and tagged posts.
        posts = [n for n in blog if n.published and "posts" in n.tags]
        # ai-solutions.js: tagged solutions (state not filtered, matching Gatsby).
        solutions = [n for n in blog if "solutions" in n.tags]
        tags: dict[str, list[ContentNode]] = {}
        for node in blog:
            for tag in node.tags:
                tags.setdefault(tag, []).append(node)
        platform.sort(
            key=lambda n: (
                int(n.front_matter.get("platform_order") or 9999),
                n.title,
            )
        )
        return cls(
            all_nodes=by_date,
            platform=platform,
            blog=blog,
            articles=articles,
            posts=posts,
            solutions=solutions,
            tags=tags,
        )


# --------------------------------------------------------------------------
# Staging
# --------------------------------------------------------------------------


def stage_nodes(
    nodes: list[ContentNode],
    *,
    staging: Path,
    directory: str,
    images: ImageIndex,
) -> ConversionReport:
    """Normalize and write one collection of MDX nodes into the staging tree."""
    total = ConversionReport()
    out_dir = staging / directory
    out_dir.mkdir(parents=True, exist_ok=True)
    for node in nodes:
        front_matter, body = split_front_matter(node.source.read_text(encoding="utf-8"))
        text, report = normalize_body(
            body,
            resolve_image_name=images.content_src,
            resolve_image_path=lambda src, n=node: images.content_src(
                src, relative_to=n.source
            ),
        )
        total.merge(report)
        front = {
            "title": node.title,
            "date": node.display_date,
            # Native `citations:` from the converted corpus, plus anything
            # lifted out of legacy `<Citation>` elements on an un-migrated
            # branch. Read before `merge()`, which deliberately drops it.
            "citations": {
                **(front_matter.get("citations") or {}),
                **report.citation_entries,
            },
        }
        header = _article_header(node, images)
        write_if_changed(out_dir / f"{node.slug}.md", staged_markdown(front, header + text))
    return total


def _article_header(node: ContentNode, images: ImageIndex) -> str:
    """Byline, draft banner, and cover image, above the article body.

    Reproduces ``blog-post.jsx``'s ``.heading`` block: title (emitted by
    Markus from front matter), date, ``by <authors>``, plus the DRAFT overlay
    the template renders for anything not ``state: published``.
    """
    parts: list[str] = []
    if not node.published:
        parts.append(
            ':::callout{kind="warning" title="DRAFT"}\n'
            "This article is not published. It has a live URL for review only.\n:::\n"
        )
    parts.append(f"*by {node.byline}*\n")
    assistants = node.front_matter.get("assistants") or []
    names = [
        html_to_inline_markdown(entry.get("assistant"))
        for entry in assistants
        if isinstance(entry, dict) and entry.get("assistant")
    ]
    names = [name for name in names if name]
    if names:
        parts.append(f"*with assistance from {', '.join(names)}*\n")
    return "\n".join(parts) + "\n"
