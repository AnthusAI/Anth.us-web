"""Anth.us as a Papyrus SiteProjector: render pages from stored item data, in process.

Deploy-time inputs next to this module: ``site-state.json`` (written by
``bin/make_site_state.py``) and ``projector-config.json`` with the two cache-busting
version tokens of the build (``markus_pages`` for Markus-rendered pages,
``generated_pages`` for generated ones).

Scope of this first version: blog (articles) item pages and every generated page.
Platform item pages and the sitemap, redirects and static files belong to the migration.
"""

from __future__ import annotations

import json
import os
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


class AnthusProjector:
    def __init__(self, state: dict, config: dict) -> None:
        self._state = state
        self._config = config

    def _prepare(self, site, target=None):
        if CONTENT_ROOT.exists():
            shutil.rmtree(CONTENT_ROOT)
        CONTENT_ROOT.mkdir(parents=True)
        if site_build.STAGING.exists():
            shutil.rmtree(site_build.STAGING)
        nodes = [node_for(summary) for summary in site.items if summary.section in PROJECTED_SECTIONS]
        nodes.sort(key=lambda node: node.source)
        collections = Collections.from_nodes(nodes)
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
        site_build.GENERATED.clear()
        site_build._PAGE_META.clear()
        site_build._ARTICLE_LD.clear()
        site_build._UNRESOLVED_LINKS.clear()
        if target is not None:
            stem = PurePosixPath(target.summary.output_path).stem
            target_node = next(node for node in collections.blog if node.source.stem == stem)
            target_node.source.parent.mkdir(parents=True, exist_ok=True)
            target_node.source.write_text(target.source_text, encoding="utf-8")
            stage_nodes([target_node], staging=site_build.STAGING, directory="articles", images=images)
        site_build.register_article_metadata(collections, images)
        for node in collections.platform:
            site_build._register_meta(f"platform/{node.slug}.html", node.excerpt_text, pages._preview(node, images))
        site_build.generate_pages(collections, images)
        page_set = set(site_build.GENERATED)
        page_set |= {f"articles/{markus_build.slugify(node.slug)}.html" for node in collections.blog}
        page_set |= {f"platform/{markus_build.slugify(node.slug)}.html" for node in collections.platform}
        site_build._SITE_URLS = urls.SiteUrls.from_collections(collections, pages=page_set, posts_per_page=site_build.POSTS_PER_PAGE)
        site_build._SITE_URLS.add_content_redirect_stubs(REDIRECTS_DIRECTORY)

    def _finished(self, href: str, html: str) -> bytes:
        page_path = site_build.DIST / href
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(html, encoding="utf-8")
        site_build.finish_pages(SimpleNamespace(pages=[page_path], out_dir=site_build.DIST))
        return page_path.read_text(encoding="utf-8").encode("utf-8")

    def _render_item(self, item) -> dict[str, bytes]:
        stem = markus_build.slugify(PurePosixPath(item.summary.output_path).stem)
        href = f"articles/{stem}.html"
        staged = site_build.STAGING / "articles" / f"{stem}.md"
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

    def _render_generated(self) -> dict[str, bytes]:
        rendered = {}
        for href, (title, fragment) in sorted(site_build.GENERATED.items()):
            html = markus_shell.render_page(
                title=title,
                fragment=fragment,
                active_href=href,
                nav_items=[],
                depth=href.count("/"),
                chrome=site_build.ANTHUS_CHROME,
                css_version=self._config["generated_pages"],
            )
            rendered[urls.page_output(href)] = self._finished(href, html)
        return rendered

    def item_page_paths(self, summary):
        if summary.section != "articles":
            return ()
        return (urls.page_output(f"articles/{markus_build.slugify(PurePosixPath(summary.output_path).stem)}.html"),)

    def item_pages(self, item, site):
        if item.summary.section != "articles":
            return {}
        self._prepare(site, item)
        return self._render_item(item)

    def listing_pages(self, site):
        self._prepare(site)
        return self._render_generated()

    def dependent_pages(self, change, site):
        return self.listing_pages(site)

    def static_files(self):
        return {}

    def redirects(self, site):
        return {}


def create_projector() -> AnthusProjector:
    state = json.loads((MODULE_DIRECTORY / "site-state.json").read_text(encoding="utf-8"))
    config = json.loads((MODULE_DIRECTORY / "projector-config.json").read_text(encoding="utf-8"))
    return AnthusProjector(state, config)
