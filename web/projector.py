"""Anth.us as a Papyrus SiteProjector: render pages from stored item data, in process.

Inputs: the image rendition records of the site store (made when an image is uploaded, read through
Papyrus's ``RenditionCatalog``; the site keeps no list of its images) and the optional
``projector-config.json`` next to this module that pins the two cache-busting version tokens
(``markus_pages``, ``generated_pages``). Without it both tokens are derived from the
stylesheet, chrome scripts and site images (the parity test pins them to a reference build).

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
from datetime import datetime
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

#: In the content-actions function this file is bundled as ``site_projector.py`` and the ``web``
#: directory as ``site_static``, named by PAPYRUS_SITE_STATIC_DIR.
MODULE_DIRECTORY = Path(os.environ.get("PAPYRUS_SITE_STATIC_DIR") or Path(__file__).resolve().parent)
os.environ.setdefault("ANTHUS_BUILD_DIR", "/tmp/build")
os.environ.setdefault("SITE_ENV", "production")
os.environ.setdefault("AWS_BRANCH", "main")
sys.path.insert(0, str(MODULE_DIRECTORY))

import markusmd  # noqa: E402

import anthus_dom as dom  # noqa: E402
import anthus_pages as pages  # noqa: E402
import anthus_urls as urls  # noqa: E402
import site_css  # noqa: E402
import site_env  # noqa: E402
from solution_sites import is_external, is_folded  # noqa: E402
import build_via_papyrus as site_build  # noqa: E402
from anthus_content import Collections, ContentNode, ImageIndex, _slugify, stage_nodes  # noqa: E402
from papyrus_content.markus_renderer import build as markus_build  # noqa: E402
from papyrus_content.projection.projector import static_version  # noqa: E402
from papyrus_content.projection.writers import request_paths_for_key  # noqa: E402
from papyrus_content.markus_renderer import shell as markus_shell  # noqa: E402
from papyrus_content.renditions import RenditionCatalog, S3RenditionStore, StoredRenditionImageBuilder  # noqa: E402

CONTENT_ROOT = Path(os.environ["ANTHUS_BUILD_DIR"]) / "content-root-projector"
REDIRECTS_DIRECTORY = MODULE_DIRECTORY / "content-redirects"
PROJECTED_SECTIONS = ("articles", "platform")
SITEMAP_KEY = "sitemap-0.xml"
STATIC_SITE_FILES = ("robots.txt", "sitemap-index.xml")
OWNED_TOP_LEVEL_DIRECTORIES = frozenset(
    {"articles", "platform", "posts", "tags", "about", "ai-solutions", "ryan", "engage", "decision-models", "benchmarks", "reading", "research"}
)
LEGACY_OG_IMAGES_PATH = MODULE_DIRECTORY / "legacy-og-images.json"
LEGACY_REDIRECT_RULES_PATH = MODULE_DIRECTORY / "legacy-redirect-rules.json"
SNAPSHOTS_KEPT = 4
PROJECTION_SETTINGS_PATH = MODULE_DIRECTORY / "projection.json"
SITE_THEME_KEY = "css/site-theme.css"
CHROME_SCRIPT_NAMES = ("site-nav.js", "conversion-events.js", "px-live.js", "drafts.js")
SITE_IMAGES_DIRECTORY = MODULE_DIRECTORY / "assets" / "site"
STATIC_ROOT_DIRECTORY = MODULE_DIRECTORY / "static-root"
_HREF_RE = re.compile(r"""\bhref=(["'])(.*?)\1""", re.S)


def files_under(directory: Path, key_prefix: str = "") -> dict[str, bytes]:
    return {
        key_prefix + path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def read_committed_static_files() -> dict[str, bytes]:
    """The stylesheet, chrome scripts, site images and root files the full build copies into the site, byte for byte."""
    files = {SITE_THEME_KEY: site_css.stylesheet_bytes()}
    for name in CHROME_SCRIPT_NAMES:
        script = MODULE_DIRECTORY / "assets" / name
        if script.is_file():
            files[f"assets/{name}"] = script.read_bytes()
    files.update(files_under(SITE_IMAGES_DIRECTORY, "assets/site/"))
    files.update(files_under(STATIC_ROOT_DIRECTORY))
    return files


def placeholder_source_matcher(source: str):
    """Compile a redirect source the way the previous host matched it: ``<name>`` is one path segment, ``<*>`` is the rest."""
    escaped = re.escape(source)
    escaped = escaped.replace("<\\*>", ".*").replace("<*>", ".*")
    return re.compile("^" + re.sub(r"<(\w+)>", r"[^/]+", escaped) + "$")


def effective_exact_redirects(ordered_rules: list[dict], page_request_paths: set[str]) -> dict[str, str]:
    """The exact 301 rules that can fire: the previous host took the first matching rule, ahead of any file.

    An exact rule listed after a pattern rule that matches its source never fired, and a rule whose
    source is now a page of this site must not hide that page.
    """
    patterns: list[re.Pattern] = []
    exact: dict[str, str] = {}
    for rule in ordered_rules:
        if rule["status"] != "301":
            continue
        source, target = rule["source"], rule["target"]
        if "<" in source:
            patterns.append(placeholder_source_matcher(source))
            continue
        if source in exact or source in page_request_paths:
            continue
        if any(pattern.match(source) for pattern in patterns):
            continue
        exact[source] = target
    return exact


def convert_fragment_in_process(source, *, theme=None, markus_executable="markus", transform=None):
    text = Path(source).read_text(encoding="utf-8")
    html = markusmd.convert(text, allow_html=False, include_css=False, full_document=False, theme=theme)
    if not html.endswith("\n"):
        html += "\n"
    return html if transform is None else transform.apply(html)


markus_build.convert_fragment = convert_fragment_in_process


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
        self.public_data_settings = projector.public_data_settings
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
        self.draft_hrefs = set(site_build._DRAFT_HREFS)
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
        site_build._DRAFT_HREFS.clear()
        site_build._DRAFT_HREFS.update(self.draft_hrefs)
        site_build._SITE_URLS = self.urls

    def sitemap_urls(self) -> list[str]:
        outputs = [urls.page_output(href) for href in sorted(self.page_set - self.draft_hrefs)]
        return sorted({urls.page_url(output) for output in outputs if output != "404.html"})

    def sitemap_bytes(self) -> bytes:
        return site_env.sitemap_0_xml(self.sitemap_urls()).encode("utf-8")

    def public_data_pages(self) -> dict[str, bytes]:
        """The search index and the latest list; empty unless projection.json opts in with ``publicData``."""
        settings = self.public_data_settings
        if settings is None:
            return {}
        from papyrus_content.projection.public_data import PublicEntry, clipped, public_data_files

        entries = []
        for summary in self.items:
            node = self.nodes_by_item.get(summary.item_id)
            if node is None or not (node.published or node.is_platform) or is_folded(node.slug):
                continue
            href = f"{summary.section}/{markus_build.slugify(node.slug)}.html"
            parsed = node.date
            entries.append(
                PublicEntry(
                    title=clipped(node.title, 200),
                    url=request_paths_for_key(urls.page_output(href))[0],
                    summary=clipped(node.excerpt_text, settings.summary_characters),
                    tags=tuple(dict.fromkeys(tag.strip() for tag in node.tags if tag.strip())),
                    date=parsed.strftime("%Y-%m-%d") if parsed != datetime.min else "",
                )
            )
        return public_data_files(entries, settings)

    def inputs(self) -> dict[str, str]:
        if self._inputs is None:
            self.activate()
            inputs: dict[str, str] = {}
            for href, (title, fragment) in sorted(self.generated.items()):
                rewritten = site_build._rewrite_internal_links(fragment, active_href=href)
                inputs[self.output_by_href[href]] = digest_of(title, rewritten)
            inputs[SITEMAP_KEY] = digest_of(self.sitemap_bytes().decode("utf-8"))
            for key, body in self.public_data_pages().items():
                inputs[key] = digest_of(body.decode("utf-8"))
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
            legacy_rules = json.loads(LEGACY_REDIRECT_RULES_PATH.read_text(encoding="utf-8"))
            generated_sources = {rule["source"] for rule in ruleset.rules}
            ordered_rules = [*ruleset.rules, *(rule for rule in legacy_rules if rule["source"] not in generated_sources)]
            page_request_paths = {
                request_path for output in self.output_by_href.values() for request_path in request_paths_for_key(output)
            } | {
                request_path
                for href in self.page_set
                for request_path in request_paths_for_key(urls.page_output(href))
            }
            self._redirects = effective_exact_redirects(ordered_rules, page_request_paths)
        return self._redirects


class AnthusProjector:
    def __init__(self, config: dict, catalog: RenditionCatalog, public_data_settings=None) -> None:
        self._config = config
        self._catalog = catalog
        self._records: list[dict] | None = None
        self._snapshots: list[Snapshot] = []
        self.public_data_settings = public_data_settings

    def image_records(self) -> list[dict]:
        """The rendition records of the site store, read once per projector: the images the site has."""
        if self._records is None:
            self._records = self._catalog.all_records()
        return self._records

    def build_image_index(self) -> ImageIndex:
        images = ImageIndex.from_sources(
            [record["source"] for record in self.image_records()],
            content_root=CONTENT_ROOT,
            site_assets=site_build.SITE_ASSETS,
        )
        dom.set_asset_roots({"/assets/content/": CONTENT_ROOT, "/assets/site/": site_build.SITE_ASSETS})
        dom._DIMENSION_CACHE.update(
            {"/assets/content/" + record["source"]: tuple(record["size"]) for record in self.image_records() if record["size"]}
        )
        return images

    @staticmethod
    def reset_globals() -> None:
        site_build.GENERATED.clear()
        site_build._PAGE_META.clear()
        site_build._ARTICLE_LD.clear()
        site_build._DRAFT_HREFS.clear()
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
        builder = StoredRenditionImageBuilder(site_build.IMAGES, self._catalog)
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

    @staticmethod
    def _lives_elsewhere(summary) -> bool:
        """Items with their own site, or folded into another page, get no page here (redirect + link rewrite only)."""
        slug = node_for(summary).slug
        if summary.section == "platform":
            return is_external(slug)
        return is_folded(slug)

    def item_page_paths(self, summary):
        if summary.section not in PROJECTED_SECTIONS or self._lives_elsewhere(summary):
            return ()
        slug = markus_build.slugify(node_for(summary).slug)
        return (urls.page_output(f"{summary.section}/{slug}.html"),)

    def item_pages(self, item, site):
        if item.summary.section not in PROJECTED_SECTIONS or self._lives_elsewhere(item.summary):
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
        for key, body in snapshot.public_data_pages().items():
            if wanted is None or key in wanted:
                pages[key] = body
        return pages

    def shared_inputs(self, site):
        return self._snapshot(site).shared()

    def owns_page_key(self, key):
        if key in ("index.html", "404.html", SITEMAP_KEY) or (self.public_data_settings is not None and key.startswith("_data/")):
            return True
        return key.endswith(".html") and key.split("/", 1)[0] in OWNED_TOP_LEVEL_DIRECTORIES

    def static_files(self):
        files = {
            "robots.txt": site_env.robots_txt().encode("utf-8"),
            "sitemap-index.xml": site_env.sitemap_index_xml().encode("utf-8"),
        }
        files.update(read_committed_static_files())
        if self.public_data_settings is not None:
            from papyrus_content.projection.public_data import public_static_files

            files.update(public_static_files(self.public_data_settings))
        return files

    def redirects(self, site):
        return dict(self._snapshot(site).redirects())


def default_projector_config() -> dict:
    """The cache-busting token of the stylesheet, chrome scripts and site images, for Markus-rendered and generated pages alike."""
    token = static_version(read_committed_static_files())
    return {"markus_pages": token, "generated_pages": token}


def create_projector() -> AnthusProjector:
    config_path = MODULE_DIRECTORY / "projector-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else default_projector_config()
    bucket = (os.environ.get("PAPYRUS_SITE_BUCKET") or "").strip()
    if not bucket:
        raise RuntimeError("PAPYRUS_SITE_BUCKET is required: the image rendition records are read from the site store.")
    return AnthusProjector(config, RenditionCatalog(S3RenditionStore(bucket), site_build.IMAGES), public_data_settings_of_site())


def public_data_settings_of_site():
    """The ``publicData`` block of projection.json, or None: the search index and latest list are opt-in."""
    raw = json.loads(PROJECTION_SETTINGS_PATH.read_text(encoding="utf-8")) if PROJECTION_SETTINGS_PATH.is_file() else {}
    if "publicData" not in raw:
        return None
    from papyrus_content.projection.public_data import public_data_settings_from_mapping

    return public_data_settings_from_mapping(raw["publicData"])
