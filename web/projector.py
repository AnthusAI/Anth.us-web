"""Anth.us as a Papyrus SiteProjector: render pages from stored item data, in process.

Deploy-time inputs next to this module: ``site-state.json`` (written by
``bin/make_site_state.py``) and ``projector-config.json`` with the two cache-busting
version tokens of the build (``markus_pages`` for Markus-rendered pages,
``generated_pages`` for generated ones).

Pages: blog (articles) and platform item pages, every generated page (home,
collections and their pagination, tags, topic pages), the sitemap, and the exact-match
redirect rules.

Dependency rule: a generated page is rewritten when, and only when, the generated
fragment it is rendered from, with its internal links resolved against the site's URL
map, differs between the site before a change and the site after it. That covers
membership, order, pagination boundaries and every field a card shows without a
hand-kept table of which page lists which item; ``tests/test_projector_incremental.py``
proves it against a full re-projection after random edits. Item pages depend on the URL
map (rewritten internal links): when it moves, the engine re-renders them as a follow-up.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

MODULE_DIRECTORY = Path(__file__).resolve().parent
os.environ.setdefault("ANTHUS_BUILD_DIR", "/tmp/build")
os.environ.setdefault("SITE_ENV", "production")
os.environ.setdefault("AWS_BRANCH", "main")
sys.path.insert(0, str(MODULE_DIRECTORY))

import markusmd  # noqa: E402

import anthus_dom as dom  # noqa: E402
import anthus_pages as pages  # noqa: E402
import anthus_urls as urls  # noqa: E402
import site_env  # noqa: E402
import build_via_papyrus as site_build  # noqa: E402
from anthus_content import Collections, ContentNode, ImageIndex, _slugify, stage_nodes  # noqa: E402
from papyrus_content.markus_renderer import build as markus_build  # noqa: E402
from papyrus_content.markus_renderer import images as markus_images  # noqa: E402
from papyrus_content.markus_renderer import shell as markus_shell  # noqa: E402
from papyrus_content.markus_renderer.images import (  # noqa: E402
    _SUFFIX_FOR_FORMAT,
    ImageBuilder,
    ImagePipelineError,
    Rendition,
    _GatsbyMeta,
    gatsby_widths,
)

CONTENT_ROOT = Path(os.environ["ANTHUS_BUILD_DIR"]) / "content-root-projector"
REDIRECTS_DIRECTORY = MODULE_DIRECTORY / "content-redirects"
PROJECTED_SECTIONS = ("articles", "platform")
SITEMAP_KEY = "sitemap-0.xml"
STATIC_SITE_FILES = ("robots.txt", "sitemap-index.xml")
OWNED_TOP_LEVEL_DIRECTORIES = frozenset(
    {"articles", "platform", "posts", "tags", "about", "ai-solutions", "ryan", "engage", "decision-models", "benchmarks", "reading", "research"}
)
LEGACY_OG_IMAGES_PATH = MODULE_DIRECTORY / "legacy-og-images.json"
SNAPSHOTS_KEPT = 4
_HREF_RE = re.compile(r"""\bhref=(["'])(.*?)\1""", re.S)


def convert_fragment_in_process(source, *, theme=None, markus_executable="markus", transform=None):
    text = Path(source).read_text(encoding="utf-8")
    html = markusmd.convert(text, allow_html=False, include_css=False, full_document=False, theme=theme)
    if not html.endswith("\n"):
        html += "\n"
    return html if transform is None else transform.apply(html)


markus_build.convert_fragment = convert_fragment_in_process


class StoredMetadataImageBuilder(ImageBuilder):
    """ImageBuilder that reads stored image metadata instead of decoding images."""

    def __init__(self, pipeline, *, content_dir, out_dir, metadata, passthrough):
        super().__init__(pipeline, content_dir=content_dir, out_dir=out_dir)
        self._metadata = metadata
        self._passthrough = passthrough

    def _locate(self, src):
        if src in self._metadata or src in self._passthrough:
            return self.source_dir / src
        return None

    def _passthrough_href(self, src, path):
        return f"{self.pipeline.out_subdir}/{Path(src).as_posix()}"

    def _stored_size(self, path):
        size = self._passthrough.get(path.relative_to(self.source_dir).as_posix())
        return tuple(size) if size else None

    def _raster_size(self, path):
        return self._stored_size(path)

    def _gatsby_renditions(self, src, path):
        cached = self._gatsby.get(src)
        if cached is not None:
            return cached
        entry = self._metadata.get(src)
        if entry is None:
            raise ImagePipelineError(f"No image metadata for {src!r}")
        relative = Path(src)
        href_directory = f"{self.pipeline.out_subdir}/{relative.parent.as_posix()}".rstrip("/.")
        href_directory = href_directory if href_directory.endswith("/") else href_directory + "/"
        intrinsic_width, intrinsic_height = entry["size"]
        fallback_format = "png" if entry["alpha"] else "jpeg"
        widths, display = gatsby_widths(intrinsic_width, max_width=self.pipeline.max_width)
        formats = list(dict.fromkeys([*self._formats, fallback_format]))
        renditions = []
        for width in widths:
            height = max(1, round(intrinsic_height * width / intrinsic_width))
            for image_format in formats:
                name = f"{relative.stem}-{width}{_SUFFIX_FOR_FORMAT[image_format]}"
                renditions.append(Rendition(width=width, height=height, href=f"{href_directory}{name}", fmt=image_format))
        if self.pipeline.placeholder == "blurred":
            raise ImagePipelineError("blurred placeholders need pixels")
        metadata = _GatsbyMeta(
            renditions=renditions,
            intrinsic=(intrinsic_width, intrinsic_height),
            display_width=display,
            fallback_fmt=fallback_format,
            placeholder=None,
        )
        self._gatsby[src] = metadata
        return metadata


def node_for(summary) -> ContentNode:
    stem = PurePosixPath(summary.output_path).stem
    relative_directory = "platform" if summary.section == "platform" else ""
    relative = f"platform/{stem}.mdx" if relative_directory else f"{stem}.mdx"
    slug = _slugify(str(summary.front_matter.get("slug") or "").strip() or stem)
    return ContentNode(slug=slug, source=CONTENT_ROOT / relative, front_matter=summary.front_matter, rel_dir=relative_directory)


def digest_of(*parts: str) -> str:
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


class Snapshot:
    """Everything derived from one SiteIndex without rendering a page: collections, the URL map, the generated fragments."""

    def __init__(self, projector: "AnthusProjector", site) -> None:
        self.items = site.items
        self.nodes_by_item = {
            summary.item_id: node_for(summary) for summary in site.items if summary.section in PROJECTED_SECTIONS
        }
        nodes = sorted(self.nodes_by_item.values(), key=lambda node: node.source)
        self.collections = Collections.from_nodes(nodes)
        self.images = projector.build_image_index()
        projector.reset_globals()
        site_build.register_article_metadata(self.collections, self.images)
        for node in self.collections.platform:
            site_build._register_meta(f"platform/{node.slug}.html", node.excerpt_text, pages._preview(node, self.images))
        site_build.generate_pages(self.collections, self.images)
        self.generated = dict(site_build.GENERATED)
        self.page_meta = dict(site_build._PAGE_META)
        self.article_ld = dict(site_build._ARTICLE_LD)
        page_set = set(self.generated)
        page_set |= {f"articles/{markus_build.slugify(node.slug)}.html" for node in self.collections.blog}
        page_set |= {f"platform/{markus_build.slugify(node.slug)}.html" for node in self.collections.platform}
        self.page_set = page_set
        self.urls = urls.SiteUrls.from_collections(self.collections, pages=page_set, posts_per_page=site_build.POSTS_PER_PAGE)
        self.urls.add_content_redirect_stubs(REDIRECTS_DIRECTORY)
        site_build._SITE_URLS = self.urls
        self.output_by_href = {href: urls.page_output(href) for href in self.generated}
        self._inputs: dict[str, str] | None = None
        self._shared: str | None = None
        self._redirects: dict[str, str] | None = None

    def activate(self) -> None:
        """Point the build module's globals at this snapshot before rendering from it."""
        site_build.GENERATED.clear()
        site_build.GENERATED.update(self.generated)
        site_build._PAGE_META.clear()
        site_build._PAGE_META.update(self.page_meta)
        site_build._ARTICLE_LD.clear()
        site_build._ARTICLE_LD.update(self.article_ld)
        site_build._SITE_URLS = self.urls

    def sitemap_urls(self) -> list[str]:
        outputs = [urls.page_output(href) for href in sorted(self.page_set)]
        return sorted(
            {site_build._canonical_url(output) for output in outputs if output != "404.html"}
        )

    def sitemap_bytes(self) -> bytes:
        return site_env.sitemap_0_xml(self.sitemap_urls()).encode("utf-8")

    def inputs(self) -> dict[str, str]:
        if self._inputs is None:
            self.activate()
            inputs: dict[str, str] = {}
            for href, (title, fragment) in sorted(self.generated.items()):
                rewritten = site_build._rewrite_internal_links(fragment, active_href=href)
                inputs[self.output_by_href[href]] = digest_of(title, rewritten)
            inputs[SITEMAP_KEY] = digest_of(self.sitemap_bytes().decode("utf-8"))
            self._inputs = inputs
        return self._inputs

    def shared(self) -> str:
        if self._shared is None:
            fields = {
                name: (sorted(value) if isinstance(value, set) else value)
                for name, value in vars(self.urls).items()
            }
            self._shared = digest_of(json.dumps(fields, sort_keys=True, default=str))
        return self._shared

    def redirects(self) -> dict[str, str]:
        if self._redirects is None:
            self.activate()
            ruleset = urls.legacy_rules(
                self.urls,
                og_images=json.loads(LEGACY_OG_IMAGES_PATH.read_text(encoding="utf-8")),
                page_images={href: image for href, (_description, image) in site_build._PAGE_META.items()},
                dist=None,
            )
            self._redirects = {
                rule["source"]: rule["target"]
                for rule in ruleset.rules
                if rule["status"] == "301" and "<" not in rule["source"] and "<" not in rule["target"]
            }
        return self._redirects


class AnthusProjector:
    def __init__(self, state: dict, config: dict) -> None:
        self._state = state
        self._config = config
        self._snapshots: list[Snapshot] = []

    def build_image_index(self) -> ImageIndex:
        images = ImageIndex(content_root=CONTENT_ROOT, site_assets=site_build.SITE_ASSETS)
        image_state = self._state["images"]
        for relative in image_state["by_relpath"]:
            images.by_relpath[relative] = CONTENT_ROOT / relative
        for name, relative in image_state["by_basename"].items():
            images.by_basename[name] = CONTENT_ROOT / relative
        for name, relative in image_state["site_by_name"].items():
            images.site_by_name[name] = site_build.SITE_ASSETS / relative
        dom.set_asset_roots({"/assets/content/": CONTENT_ROOT, "/assets/site/": site_build.SITE_ASSETS})
        dom._DIMENSION_CACHE.update({key: tuple(value) for key, value in self._state["dimensions"].items()})
        return images

    @staticmethod
    def reset_globals() -> None:
        site_build.GENERATED.clear()
        site_build._PAGE_META.clear()
        site_build._ARTICLE_LD.clear()
        site_build._UNRESOLVED_LINKS.clear()

    def _snapshot(self, site) -> Snapshot:
        for snapshot in self._snapshots:
            if snapshot.items is site.items:
                self._snapshots.remove(snapshot)
                self._snapshots.append(snapshot)
                return snapshot
        snapshot = Snapshot(self, site)
        self._snapshots.append(snapshot)
        del self._snapshots[:-SNAPSHOTS_KEPT]
        return snapshot

    def _reset_staging(self) -> None:
        for directory in (CONTENT_ROOT, site_build.STAGING):
            if directory.exists():
                shutil.rmtree(directory)
        CONTENT_ROOT.mkdir(parents=True)

    def _stage_item(self, snapshot: Snapshot, item) -> str:
        node = snapshot.nodes_by_item[item.summary.item_id]
        self._reset_staging()
        node.source.parent.mkdir(parents=True, exist_ok=True)
        node.source.write_text(item.source_text, encoding="utf-8")
        if node.rel_dir == "platform":
            site_build.stage_platform_page(node, snapshot.images, source_text=item.source_text)
            return "platform"
        stage_nodes([node], staging=site_build.STAGING, directory="articles", images=snapshot.images)
        return "articles"

    def _finished(self, href: str, html: str) -> bytes:
        page_path = site_build.DIST / href
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(html, encoding="utf-8")
        site_build.finish_pages(SimpleNamespace(pages=[page_path], out_dir=site_build.DIST))
        return page_path.read_text(encoding="utf-8").encode("utf-8")

    def _render_item(self, node: ContentNode, directory: str) -> dict[str, bytes]:
        stem = markus_build.slugify(node.slug)
        href = f"{directory}/{stem}.html"
        staged = site_build.STAGING / directory / f"{node.slug}.md"
        builder = StoredMetadataImageBuilder(
            site_build.IMAGES,
            content_dir=site_build.STAGING,
            out_dir=site_build.DIST,
            metadata=self._state["gatsby"],
            passthrough=self._state["passthrough"],
        )
        markus_images._svg_dimensions = builder._stored_size
        fragment = markus_build.render_fragment(
            staged,
            theme=None,
            depth=1,
            images=site_build.IMAGES,
            image_builder=builder,
            citations=site_build.CITATIONS,
            transform=site_build.ANTHUS_TRANSFORM,
        )
        html = markus_shell.render_page(
            title=markus_build._read_title(staged, stem.replace("-", " ").title()),
            fragment=fragment,
            active_href=href,
            nav_items=[],
            depth=1,
            chrome=site_build.ANTHUS_CHROME,
            css_version=self._config["markus_pages"],
        )
        return {urls.page_output(href): self._finished(href, html)}

    def _render_generated(self, snapshot: Snapshot, keys) -> dict[str, bytes]:
        snapshot.activate()
        rendered: dict[str, bytes] = {}
        for href, (title, fragment) in sorted(snapshot.generated.items()):
            output = snapshot.output_by_href[href]
            if keys is not None and output not in keys:
                continue
            html = markus_shell.render_page(
                title=title,
                fragment=fragment,
                active_href=href,
                nav_items=[],
                depth=href.count("/"),
                chrome=site_build.ANTHUS_CHROME,
                css_version=self._config["generated_pages"],
            )
            rendered[output] = self._finished(href, html)
        return rendered

    def item_page_paths(self, summary):
        if summary.section not in PROJECTED_SECTIONS:
            return ()
        slug = markus_build.slugify(node_for(summary).slug)
        return (urls.page_output(f"{summary.section}/{slug}.html"),)

    def item_pages(self, item, site):
        if item.summary.section not in PROJECTED_SECTIONS:
            return {}
        snapshot = self._snapshot(site)
        snapshot.activate()
        directory = self._stage_item(snapshot, item)
        return self._render_item(snapshot.nodes_by_item[item.summary.item_id], directory)

    def listing_inputs(self, site):
        return dict(self._snapshot(site).inputs())

    def listing_pages(self, site, keys=None):
        snapshot = self._snapshot(site)
        wanted = None if keys is None else set(keys)
        pages = self._render_generated(snapshot, wanted)
        if wanted is None or SITEMAP_KEY in wanted:
            pages[SITEMAP_KEY] = snapshot.sitemap_bytes()
        return pages

    def shared_inputs(self, site):
        return self._snapshot(site).shared()

    def owns_page_key(self, key):
        if key in ("index.html", "404.html", SITEMAP_KEY):
            return True
        return key.endswith(".html") and key.split("/", 1)[0] in OWNED_TOP_LEVEL_DIRECTORIES

    def static_files(self):
        return {
            "robots.txt": site_env.robots_txt().encode("utf-8"),
            "sitemap-index.xml": site_env.sitemap_index_xml().encode("utf-8"),
        }

    def redirects(self, site):
        return dict(self._snapshot(site).redirects())


def create_projector() -> AnthusProjector:
    state = json.loads((MODULE_DIRECTORY / "site-state.json").read_text(encoding="utf-8"))
    config = json.loads((MODULE_DIRECTORY / "projector-config.json").read_text(encoding="utf-8"))
    return AnthusProjector(state, config)
