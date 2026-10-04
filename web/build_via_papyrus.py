#!/usr/bin/env python3
"""Build the Anth.us reader site through **Papyrus's** Markus renderer.

This is the Anth.us website rebuilt as a Papyrus/Markus static reader site, so
Anthus dogfoods its own CMS. The publication supplies only its own identity —
masthead, nav, footer, theme CSS, metadata — and the rendering itself is
Papyrus's (`papyrus_content.markus_renderer`). Architecturally this is the same
shape as `Pilobol.us/web/build_via_papyrus.py`.

**This is a STAGING build.** It is reviewed on its own Amplify
`*.amplifyapp.com` hostname. It must not be pointed at `anth.us` or any
production subdomain; see README.md.

Usage:
    PAPYRUS_ROOT=/path/to/Papyrus python3 web/build_via_papyrus.py

`PAPYRUS_ROOT` defaults to `../Papyrus` relative to this repo.

Pipeline
--------
1. ``anthus_content.discover`` reads the MDX content submodule (read-only).
2. ``anthus_mdx.normalize_body`` rewrites MDX/JSX/raw HTML into Markus-safe
   Markdown; ``anthus_pages`` generates the bespoke pages and listings.
   Both write only into the gitignored ``web/staging/`` tree.
3. Papyrus's ``build_markus_site`` renders ``web/staging`` to
   ``web/dist-papyrus`` with Anthus chrome.
4. Standalone depth-0 pages, redirect stubs, ``robots.txt`` and ``sitemap.xml``
   are written on top, then a parity report is printed.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import shutil
import sys
from html import escape, unescape
from pathlib import Path

POD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = POD_ROOT.parent
DEFAULT_PAPYRUS = REPO_ROOT.parent / "Papyrus"

PAPYRUS_ROOT = Path(os.environ.get("PAPYRUS_ROOT", DEFAULT_PAPYRUS)).resolve()
if not (PAPYRUS_ROOT / "src" / "papyrus_content").is_dir():
    sys.exit(
        f"Papyrus not found at {PAPYRUS_ROOT}. "
        "Set PAPYRUS_ROOT to your Papyrus checkout."
    )

sys.path.insert(0, str(PAPYRUS_ROOT / "src"))
sys.path.insert(0, str(POD_ROOT))

from papyrus_content.markus_renderer import build as markus_build  # noqa: E402
from papyrus_content.markus_renderer import shell as markus_shell  # noqa: E402
from papyrus_content.markus_renderer.build import build_markus_site  # noqa: E402
from papyrus_content.markus_renderer.citations import CitationRendering  # noqa: E402
from papyrus_content.markus_renderer.images import (  # noqa: E402
    DEFAULT_LAYOUT_SIZES,
    ImagePipeline,
)
from papyrus_content.markus_renderer.shell import (  # noqa: E402
    BodyParts,
    PageContext,
    SiteChrome,
)
from papyrus_content.markus_renderer.transforms import (  # noqa: E402
    FragmentTransform,
    block_sentinel,
)

import anthus_dom as dom  # noqa: E402
import anthus_page_html  # noqa: E402
import anthus_pages as pages  # noqa: E402
import anthus_urls as urls  # noqa: E402
import site_env  # noqa: E402  (PPY-f1f0a8)
from anthus_content import (  # noqa: E402
    POSTS_PER_PAGE,
    Collections,
    ConversionReport,
    ImageIndex,
    discover,
    stage_nodes,
)
from anthus_mdx import normalize_body, split_front_matter, staged_markdown, write_if_changed  # noqa: E402

#: `ANTHUS_CONTENT_DIR`, `ANTHUS_BUILD_DIR` exist for diagnostics only: build the
#: corpus the live site was built from (content 4b80f02) into a scratch tree, to
#: tell content-driven differences from design ones. The pin is not changed.
CONTENT_SUBMODULE = Path(
    os.environ.get("ANTHUS_CONTENT_DIR", REPO_ROOT / "content" / "anthus-site-content")
).resolve()
_BUILD_DIR = Path(os.environ["ANTHUS_BUILD_DIR"]).resolve() if os.environ.get("ANTHUS_BUILD_DIR") else POD_ROOT
SITE_ASSETS = POD_ROOT / "assets" / "site"
STAGING = _BUILD_DIR / "staging"
DIST = _BUILD_DIR / "dist-papyrus"
#: Generated image renditions, kept OUTSIDE both `STAGING` and `DIST` because
#: this script wipes the first and `build_markus_site` wipes the second. Put it
#: on the CI cache path; a cold build is ~230 sources x 6 widths x 2 formats.
IMAGE_CACHE = _BUILD_DIR / ".image-cache"

# ---- Papyrus content-markup capabilities (docs/markus-content-markup.md) ---
#
# `source_dir` is the content submodule, not the staging tree: `::image{}` src
# values in the corpus are repo-relative (`images/chart.png`) and the pipeline
# reads the originals and writes its own derivatives, so nothing has to be
# pre-copied or pre-downscaled.
#
# `upgrade_plain_images=False` is load-bearing. `anthus_pages` emits listing
# thumbnails and site chrome as plain Markdown images with site-ABSOLUTE
# hrefs (`/assets/content/…`, `/assets/site/…`), which `assert_safe_asset_src`
# rejects by design. Those assets are staged and copied by `ImageIndex.stage`
# instead, so `::image{}` is the only responsive path. Making them responsive
# too would mean giving the pipeline a second source root.
#
# `widths`/`max_width` are capped at 1366 on purpose. Every layout's `sizes`
# tops out at 48rem (768 CSS px), so a browser never asks for more than ~1536
# px even at 2x DPR, and the pipeline otherwise also offers each source's own
# intrinsic width -- the originals here run to 26 MB and several thousand
# pixels. The cap matters more than it looks: the source format is always
# emitted as the <picture> fallback, so each PNG rendition ships at PNG size
# (290 MB of PNG against 38 MB of WebP for the same renditions at a 1920 cap),
# and the artifact is uploaded as a zip.
IMAGES = ImagePipeline(
    source_dir=CONTENT_SUBMODULE,
    cache_dir=IMAGE_CACHE,
    widths=(480, 768, 1024, 1366),
    max_width=1366,
    upgrade_plain_images=False,
    # gatsby-plugin-image's constrained DOM, which the production stylesheet
    # positions absolutely; see anthus_dom.anthus_image_wrap.
    wrap=dom.anthus_image_wrap,
    layout_sizes=dom.anthus_layout_sizes(DEFAULT_LAYOUT_SIZES),
)
CITATIONS = CitationRendering()

# --- SITE_ENV guards (PPY-f1f0a8): all logic lives in site_env.py -----------
ENV = site_env.ENV
SITE_ORIGIN = ENV.origin
# TODO(analytics): pass ENV.analytics_enabled to Papyrus's Markus analytics
# capability (provider config for live anth.us) once it lands. Off unless production.
ANALYTICS_ENABLED = ENV.analytics_enabled


# --------------------------------------------------------------------------
# Chrome and fragment transform
# --------------------------------------------------------------------------

#: Papyrus hrefs whose production route differs from the one derived from the
#: path: the articles index is `/blog/` on production, and it is what the
#: "Articles" nav item matches.
_ROUTE_OVERRIDES = {"articles/index.html": "/blog/"}


def _route(active_href: str) -> str:
    return _ROUTE_OVERRIDES.get(active_href, dom.route_for(active_href))


def _render_masthead(ctx: PageContext) -> str:
    return dom.render_masthead(_route(ctx.active_href))


def _render_body(ctx: PageContext, parts: BodyParts) -> str:
    return dom.render_envelope(
        fragment=ctx.fragment, route=_route(ctx.active_href), scripts=parts.scripts
    )


ANTHUS_CHROME = SiteChrome(
    site_name=pages.SITE_TITLE,
    tagline=None,
    scripts=("assets/priority-plus.js", "assets/site-nav.js"),
    lang="en",
    # Production's <body> has no class. An empty value renders `class=""`
    # through Papyrus's shell; `_finish_page` removes the empty attribute.
    body_class="",
    # `build_markus_site(site_css=web/css/anthus-theme.css)` copies the file to
    # `css/site-theme.css`; the destination name is fixed by Papyrus.
    stylesheets=("css/site-theme.css",),
    head_html=dom.HEAD_HTML,
    title_template="{title} | Anthus",
    same_title_template="Anthus",
    asset_root="/",
    render_masthead=_render_masthead,
    render_body=_render_body,
)

#: Markus -> production class vocabulary for converted content bodies.
#: `<article class="markus-document">` becomes plain `<article>`, which is what
#: production has. Block passthrough carries the heading, svgs and span tables.
ANTHUS_TRANSFORM = FragmentTransform(
    strip_header=True,
    allow_block_passthrough=True,
    class_map=dom.CLASS_MAP,
    drop_unmapped_classes=dom.DROP_PREFIXES,
)


# --------------------------------------------------------------------------
# Link rewriting
# --------------------------------------------------------------------------

# Every internal reference the build emits is normalized here, in one pass over
# the rendered HTML, to the canonical site-absolute URL from `anthus_urls`.
#
# Site-absolute AND relative references both go through it. Relative ones have
# to, because the canonical output shape moves a page: Papyrus renders
# `articles/<slug>.md` to `articles/<slug>.html` at depth 1 and links its
# chrome with `../`, but the page is written to `articles/<slug>/index.html`,
# where `../css/site-theme.css` would resolve to `/articles/css/...`. Resolving
# every reference against the page's *Papyrus* location and re-emitting it
# absolute makes the output independent of where the file ends up, which is
# what lets `ANTHUS_URL_STYLE` be a single switch.
_REF_RE = re.compile(r'\b(?P<attr>href|src)="(?P<url>[^"]*)"')
_SRCSET_RE = re.compile(r'\bsrcset="(?P<value>[^"]*)"')
_SKIP_PREFIXES = ("//", "#", "?", "data:", "mailto:", "tel:", "http://", "https://")

#: Papyrus hrefs this build renders, and the authored-name tables that map a
#: live-site URL onto one of them. Both are populated from the staged corpus
#: before the first page renders; see `main`.
_SITE_URLS = urls.SiteUrls()
_UNRESOLVED_LINKS: dict[str, int] = {}


def _absolutize(url: str, *, base_dir: str) -> str:
    """Canonicalize one reference from one page.

    ``base_dir`` is the page's *Papyrus* output directory, which is what the
    authored relative references were written against.
    """
    if not url or url.startswith(_SKIP_PREFIXES):
        return url
    path, sep, tail = url.partition("#")
    if not sep:
        path, sep, tail = url.partition("?")
    if not path:
        return url
    if path.startswith("/"):
        absolute = path
    else:
        absolute = "/" + posixpath.normpath(posixpath.join(base_dir, path))
    if urls.is_non_page(absolute):
        return absolute + sep + tail
    href = _SITE_URLS.resolve(absolute)
    if href is not None:
        return urls.page_url(href) + sep + tail
    # No page here, on this site or on production: a content bug. Report it and
    # leave the reference exactly as authored. Reshaping it would hide the bug
    # behind a different broken URL -- which is what happened to the
    # scheme-less `arxiv.org/abs/...` link when this pass first absolutized
    # everything it touched.
    if absolute != "/":
        _UNRESOLVED_LINKS[path] = _UNRESOLVED_LINKS.get(path, 0) + 1
    return url


def _rewrite_internal_links(html: str, *, active_href: str) -> str:
    """Rewrite every internal reference on one page to its canonical URL.

    Done on rendered HTML rather than on Markdown so it also catches links
    that came out of front matter (``authors: <a href="/ryan">…</a>``), out of
    the generated page copy, and out of Papyrus's own page shell, in one place.
    """
    base_dir = posixpath.dirname(active_href.lstrip("/"))

    def one(match: re.Match[str]) -> str:
        url = unescape(match.group("url"))
        resolved = _absolutize(url, base_dir=base_dir)
        return f'{match.group("attr")}="{escape(resolved, quote=True)}"'

    def many(match: re.Match[str]) -> str:
        out = []
        for candidate in unescape(match.group("value")).split(","):
            parts = candidate.strip().split(None, 1)
            if not parts:
                continue
            resolved = _absolutize(parts[0], base_dir=base_dir)
            out.append(" ".join([resolved] + parts[1:]))
        return f'srcset="{escape(", ".join(out), quote=True)}"'

    return _SRCSET_RE.sub(many, _REF_RE.sub(one, html))


# --------------------------------------------------------------------------
# Social metadata
# --------------------------------------------------------------------------

_DEFAULT_COVER = "/assets/site/serverless-ai-software-solutions.png"
_PAGE_META: dict[str, tuple[str, str]] = {}  # active_href -> (description, image)
#: active_href -> JSON-LD `Article` object, for published articles only (as live).
_ARTICLE_LD: dict[str, dict] = {}


def _canonical_url(active_href: str) -> str:
    return f"{SITE_ORIGIN}{urls.page_url(active_href)}"


def _absolute(src: str) -> str:
    if src.startswith(("http://", "https://")):
        return src
    return f"{SITE_ORIGIN}/{src.lstrip('/')}"


def _inject_social_meta(html: str, *, active_href: str) -> str:
    title_match = re.search(r"<title>(.*?)</title>", html, re.S)
    title = unescape(title_match.group(1)) if title_match else ""
    description, image = _PAGE_META.get(
        active_href, (pages.SITE_DESCRIPTION, _DEFAULT_COVER)
    )
    if not description:
        description = pages.SITE_DESCRIPTION
    if not image:
        image = _DEFAULT_COVER
    page_title = (title or "").strip() or pages.SITE_TITLE
    url = _canonical_url(active_href)
    article_ld = _ARTICLE_LD.get(active_href)
    ld_json = ""
    if article_ld is not None:
        data = dict(article_ld, mainEntityOfPage=url)
        if image != _DEFAULT_COVER:
            data["image"] = _absolute(image)
        ld_json = (
            '<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
            + "</script>\n"
        )

    def q(value: str) -> str:
        return escape(value, quote=True)

    meta = (
        f'<meta name="description" content="{q(description)}">\n'
        f'<link rel="canonical" href="{q(url)}">\n'
        f'<meta property="og:site_name" content="{q(pages.SITE_TITLE)}">\n'
        f'<meta property="og:type" content="{"article" if article_ld is not None else "website"}">\n'
        f'<meta property="og:title" content="{q(page_title)}">\n'
        f'<meta property="og:description" content="{q(description)}">\n'
        f'<meta property="og:url" content="{q(url)}">\n'
        f'<meta property="og:image" content="{q(_absolute(image))}">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:creator" content="@RyanAlynPorter">\n'
        f'<meta name="twitter:title" content="{q(page_title)}">\n'
        f'<meta name="twitter:description" content="{q(description)}">\n'
        f'<meta name="twitter:image" content="{q(_absolute(image))}">\n'
        + site_env.head_extras(ENV)  # noindex (guarded only) + sitemap link
        + ld_json
    )
    if 'property="og:title"' in html:
        return html
    html2, count = re.subn(r"(</title>\s*)", r"\1" + meta, html, count=1)
    if count != 1:
        raise RuntimeError(f"social meta inject failed for {active_href!r}")
    return html2


# --------------------------------------------------------------------------
# Staging
# --------------------------------------------------------------------------


def _register_meta(href: str, description: str, image: str | None) -> None:
    _PAGE_META[href] = (description, image or _DEFAULT_COVER)


#: Pages whose body is generated HTML and bypasses Markus entirely:
#: Papyrus href -> (title, `<main>` inner HTML). Filled by `stage`.
GENERATED: dict[str, tuple[str, str]] = {}


def _page_title(plain: str) -> str:
    """`PAGE_META` titles carry the ` | Anthus` suffix the shell adds itself."""
    return plain.removesuffix(" | Anthus")


def _generated(href: str, title: str, fragment: str, *, meta_key: str | None = None) -> None:
    GENERATED[href] = (title, fragment)
    meta = anthus_page_html.PAGE_META.get(meta_key) if meta_key else None
    if meta:
        _register_meta(href, meta["description"], None)


def _collection_page(directory: str, title: str, number: int, fragment: str) -> None:
    """One page of a `collection.jsx` listing, at its canonical Papyrus href."""
    href = (
        f"{directory}/index.html"
        if number == 1
        else f"{directory}/page/{number}/index.html"
    )
    _generated(href, title if number == 1 else f"{title}, page {number}", fragment)
    _register_meta(href, pages.COLLECTION_DESCRIPTIONS[title], None)


def stage(collections: Collections, images: ImageIndex) -> ConversionReport:
    STAGING.mkdir(parents=True, exist_ok=True)
    GENERATED.clear()
    report = ConversionReport()

    # The blog corpus. `build_markus_site` hard-requires `articles/`, which is
    # why the canonical reader path is /articles/<slug>.html; see
    # anthus_content's module docstring.
    report.merge(
        stage_nodes(collections.blog, staging=STAGING, directory="articles", images=images)
    )

    # Platform products: Markus renders the MDX body; the production template's
    # heading and "where this fits" section are block sentinels around it.
    platform_dir = STAGING / "platform"
    platform_dir.mkdir(parents=True, exist_ok=True)
    for node in collections.platform:
        front_matter, body = split_front_matter(node.source.read_text(encoding="utf-8"))
        text, node_report = normalize_body(
            body,
            resolve_image_name=images.content_src,
            resolve_image_path=lambda src, n=node: images.content_src(
                src, relative_to=n.source
            ),
        )
        tail = pages.platform_product_tail(node)
        document = (
            block_sentinel(pages.platform_product_head(node))
            + "\n\n"
            + text
            + ("\n\n" + block_sentinel(tail) + "\n" if tail else "")
        )
        write_if_changed(
            platform_dir / f"{node.slug}.md",
            staged_markdown(
                {
                    "title": node.title,
                    "date": node.display_date,
                    # Read before merge(), which drops per-page citation keys.
                    "citations": {
                        **(front_matter.get("citations") or {}),
                        **node_report.citation_entries,
                    },
                },
                document,
            ),
        )
        report.merge(node_report)
        _register_meta(
            f"platform/{node.slug}.html",
            node.excerpt_text,
            pages._preview(node, images),
        )

    for node in collections.blog:
        href = f"articles/{node.slug}.html"
        _register_meta(href, node.excerpt_text, pages._preview(node, images))
        if node.published:
            _ARTICLE_LD[href] = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": node.title,
                "description": node.excerpt_text,
                "datePublished": node.date_raw,
                "author": [
                    {"@type": "Person", "name": name}
                    for name in node.author_names
                ],
                "publisher": {"@type": "Organization", "name": "Anthus AI Solutions"},
            }

    # Generated pages: HTML in the production DOM, never through Markus.
    meta = anthus_page_html.PAGE_META
    _generated(
        "index.html",
        "Home",
        pages.homepage(
            articles=collections.articles,
            posts=collections.posts,
            images=images,
            blog=collections.blog,
        ),
    )
    for number, text in pages.articles_collection(collections.articles, images).items():
        _collection_page("articles", "Articles", number, text)
    _generated("platform/index.html", "Anthus Platform", pages.platform_index(collections.platform))
    _register_meta(
        "platform/index.html",
        "Explore the Anthus Platform: the runtime, orchestration, MLOps, knowledge, "
        "observability, and media systems behind our AI-native delivery work.",
        None,
    )
    _generated(
        "about.html", _page_title(meta["/about/"]["title"]), pages.about_page(), meta_key="/about/"
    )
    _generated(
        "ai-solutions.html",
        _page_title(meta["/ai-solutions/"]["title"]),
        pages.ai_solutions_page(collections.blog, images),
        meta_key="/ai-solutions/",
    )
    _generated(
        "ryan.html",
        _page_title(meta["/ryan/"]["title"]),
        pages.ryan_page(collections.solutions, images),
        meta_key="/ryan/",
    )
    _generated(
        "404.html",
        _page_title(meta["/404.html"]["title"]),
        pages.not_found_page(),
        meta_key="/404.html",
    )
    _generated(
        "engage.html", _page_title(meta["/engage/"]["title"]), pages.engage_page(), meta_key="/engage/"
    )
    _generated(
        "decision-models.html",
        _page_title(meta["/decision-models/"]["title"]),
        pages.decision_models_page(),
        meta_key="/decision-models/",
    )
    _generated(
        "reading.html",
        _page_title(meta["/reading/"]["title"]),
        pages.reading_page(collections.blog, images),
        meta_key="/reading/",
    )
    _generated(
        "research.html",
        _page_title(meta["/research/"]["title"]),
        pages.research_page(collections.blog, images),
        meta_key="/research/",
    )

    for number, text in pages.posts_collection(collections.posts, images).items():
        _collection_page("posts", "Posts", number, text)

    for slug, (label, text) in pages.tag_pages(collections.tags).items():
        _generated(f"tags/{slug}.html", label if slug != "index" else "Tags", text)

    # Images: only what pages actually reference, downscaled.
    copied, downscaled = images.stage(STAGING / "assets")
    print(f"  staged {copied} image(s), {downscaled} downscaled to <= 1600px")
    if images.missing:
        print(f"  WARNING: {len(images.missing)} unresolved image reference(s)")
        for name in sorted(images.missing)[:10]:
            print(f"    - {name}")

    # Chrome scripts and committed site imagery travel with the staging tree
    # so Papyrus's `_copy_tree(content/assets -> dist/assets)` picks them up.
    #
    # `web/assets/site/` is copied WHOLESALE rather than through ImageIndex.
    # The generated page copy hard-codes `/assets/site/...` paths (the hero,
    # the capability tiles, the lifecycle diagram), so those files are never
    # "resolved" and never land in `used_site`.
    staging_assets = STAGING / "assets"
    staging_assets.mkdir(parents=True, exist_ok=True)
    if SITE_ASSETS.is_dir():
        dest = staging_assets / "site"
        dest.mkdir(parents=True, exist_ok=True)
        for path in sorted(SITE_ASSETS.rglob("*")):
            if path.is_file():
                target = dest / path.relative_to(SITE_ASSETS)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    for script in ("site-nav.js", "priority-plus.js"):
        shutil.copy2(POD_ROOT / "assets" / script, staging_assets / script)

    # Fail loudly on a chrome image the generated pages reference but that is
    # not committed -- a silently broken hero is worse than a failed build.
    referenced = {
        match
        for _title, fragment in GENERATED.values()
        # Filenames contain spaces ("Anthus AI Application Lifecycle.png"),
        # so stop only at the closing quote or paren, never at whitespace.
        for match in re.findall(r"/assets/site/([^\"')]+)", fragment)
    }
    absent = sorted(name for name in referenced if not (staging_assets / "site" / name).is_file())
    if absent:
        raise RuntimeError(
            "Generated pages reference site assets that are not committed in "
            f"web/assets/site/: {', '.join(absent)}"
        )
    return report


# --------------------------------------------------------------------------
# Staging audit
# --------------------------------------------------------------------------

_MDX_LEFTOVER_RE = re.compile(r"<(?:BlogImage|Citation|CitationsList)\b")
_IMAGE_DIRECTIVE_RE = re.compile(r"^[ \t]*::image\{", re.M)
_CITATIONS_DIRECTIVE_RE = re.compile(r"^[ \t]*::citations\b", re.M)
_CITE_MARKER_RE = re.compile(r"\[@[^\]\n]+\]")


def audit_staging(staging: Path) -> tuple[int, int, int]:
    """Count the Papyrus markup actually handed to the renderer, and refuse
    to go on if a Gatsby component survived into it.

    `markus convert` fails a whole page on an unregistered directive, so a
    leftover `<BlogImage>` would not break the build -- it would be escaped
    into visible angle brackets on a page nobody looks at. Counting here is
    what makes "zero leftovers" an assertion rather than a hope.
    """
    images = markers = lists = 0
    leftovers: list[str] = []
    for path in sorted(staging.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        images += len(_IMAGE_DIRECTIVE_RE.findall(text))
        lists += len(_CITATIONS_DIRECTIVE_RE.findall(text))
        markers += len(_CITE_MARKER_RE.findall(text))
        if _MDX_LEFTOVER_RE.search(text):
            leftovers.append(path.relative_to(staging).as_posix())
    if leftovers:
        raise RuntimeError(
            "Gatsby MDX components survived normalization into the staging "
            f"tree: {', '.join(leftovers[:10])}"
        )
    return images, markers, lists


# --------------------------------------------------------------------------
# Standalone pages and redirects
# --------------------------------------------------------------------------


def write_generated(result) -> None:
    """Render every generated page through the same shell, bypassing Markus.

    ``markus_shell.render_page`` is called directly with the generated
    `<main>` HTML as the fragment; the chrome hooks do the rest. Pages Papyrus
    already wrote (`index.html`, `articles/index.html`, a placeholder from its
    fallback) are overwritten and keep their entry in ``result.pages``.
    """
    css_version = markus_build._css_version(result.out_dir / "css", result.out_dir / "assets")
    known = {page.relative_to(result.out_dir).as_posix() for page in result.pages}
    for href, (title, fragment) in sorted(GENERATED.items()):
        page_path = result.out_dir / href
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            markus_shell.render_page(
                title=title,
                fragment=fragment,
                active_href=href,
                nav_items=[],
                depth=href.count("/"),
                chrome=ANTHUS_CHROME,
                css_version=css_version,
            ),
            encoding="utf-8",
        )
        if href not in known:
            result.pages.append(page_path)


_CELL_ALIGN_RE = re.compile(r'<(th|td) style="text-align:(?:left|right|center)">')


def finish_pages(result) -> None:
    """Post-pass over every rendered page, before relocation to canonical paths.

    Link canonicalization, social meta and the staging `noindex` guard are
    applied to Markus-rendered and generated pages alike, keyed by each file's
    Papyrus href. Then the output gate: no `markus-`/`papyrus-` class may
    survive, because the production stylesheet has no rule for either.
    """
    for page in result.pages:
        active_href = page.relative_to(result.out_dir).as_posix()
        text = page.read_text(encoding="utf-8")
        text = _rewrite_internal_links(text, active_href=active_href)
        text = _inject_social_meta(text, active_href=active_href)
        text = text.replace('<body class="">', "<body>", 1)
        # Markus renders a Markdown table's `---:` column alignment as an inline
        # style; production's MDX pipeline emits none (cells stay left-aligned).
        text = _CELL_ALIGN_RE.sub(r"<\1>", text)
        if "twitter-tweet" in text and "platform.twitter.com/widgets.js" not in text:
            # Production's /about/ embeds a tweet and loads Twitter's widget
            # script from its head; without it the blockquote never renders.
            text = text.replace(
                "</head>",
                '<script src="https://platform.twitter.com/widgets.js"></script>\n</head>',
                1,
            )
        dom.assert_no_markus_classes(text, active_href)
        page.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# Canonical output shape
# --------------------------------------------------------------------------

#: Papyrus's collection discovery filter. A staged file it rejects is a page
#: that silently never renders, so link resolution has to apply the same test.
_PAPYRUS_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")
_RENDERED_DIRS = ("articles", "platform")


def staged_page_hrefs() -> set[str]:
    """Predict the Papyrus hrefs this build renders.

    `build_markus_site` walks `articles/` plus the `platform` section and
    accepts only `_PAGE_SLUG`-shaped filenames; everything in `GENERATED` is
    written by `write_generated`. Predicting the set here lets every internal
    link be resolved against real pages during rendering, and `main` then
    asserts the prediction against what was actually written -- which is how a
    staged page that Papyrus quietly skipped would fail the build instead of
    becoming a 404 behind a successful deploy.
    """
    hrefs = set(GENERATED)
    for directory in _RENDERED_DIRS:
        for path in sorted((STAGING / directory).glob("*.md")):
            if _PAPYRUS_SLUG_RE.match(path.name):
                hrefs.add(f"{directory}/{path.stem}.html")
    return hrefs


def relocate_pages(result) -> int:
    """Move Papyrus's rendered pages to their canonical output locations.

    Papyrus writes `articles/<slug>.html`; the canonical URL is
    `/articles/<slug>/`, so the file belongs at `articles/<slug>/index.html`.
    Every reference on the page was already rewritten to a site-absolute
    canonical URL by `_rewrite_internal_links`, so moving the file cannot break
    a stylesheet, a script, or a link. `result.pages` is updated in place so the
    sitemap describes where the pages actually are.
    """
    moved = 0
    for index, page in enumerate(result.pages):
        href = page.relative_to(result.out_dir).as_posix()
        target = result.out_dir / urls.page_output(href)
        if target == page:
            continue
        if target.exists():
            raise RuntimeError(f"canonical output collision: {href} -> {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        page.replace(target)
        result.pages[index] = target
        moved += 1
    return moved


# --------------------------------------------------------------------------
# Legacy URL redirects
# --------------------------------------------------------------------------

#: Where the generated Amplify rules are written. Not part of the deployed
#: artifact: `customRules` is Amplify *app* configuration, not a repo file, so
#: `bin/apply_custom_rules.py` reads this and calls `amplify update-app`.
CUSTOM_RULES = _BUILD_DIR / "custom-rules.json"


def write_custom_rules(site_urls: urls.SiteUrls) -> urls.RuleSet:
    """Generate the Amplify `customRules` that 301 every legacy URL shape.

    Replaces the ~120 meta-refresh HTML stubs this build used to emit under
    `/blog/`. A meta refresh is a 200 carrying a client-side hop: search
    engines treat it as a weak signal at best, it does not consolidate link
    equity the way a 301 does, and it costs a full page load. These are real
    301s, served by Amplify before it touches the filesystem.
    """
    ruleset = urls.legacy_rules(site_urls)
    CUSTOM_RULES.write_text(
        json.dumps(ruleset.rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return ruleset


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> int:
    site_env.announce(ENV)
    if not (CONTENT_SUBMODULE / "README.md").is_file():
        sys.exit(
            f"Content submodule missing at {CONTENT_SUBMODULE}. "
            "Run: git submodule update --init --recursive"
        )

    print("Discovering content from the anthus-site-content submodule…")
    nodes = discover(CONTENT_SUBMODULE)
    collections = Collections.from_nodes(nodes)
    print(
        f"  {len(nodes)} MDX nodes: {len(collections.blog)} blog "
        f"({len(collections.articles)} articles, {len(collections.posts)} posts, "
        f"{len(collections.solutions)} solutions), "
        f"{len(collections.platform)} platform, {len(collections.tags)} tags"
    )

    images = ImageIndex.build(CONTENT_SUBMODULE, SITE_ASSETS)
    dom.set_asset_roots(
        {"/assets/content/": CONTENT_SUBMODULE, "/assets/site/": SITE_ASSETS}
    )

    print("Staging Markus Markdown…")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    report = stage(collections, images)
    image_count, citation_count, citations_list_count = audit_staging(STAGING)
    print(
        f"  staged markup: {image_count} ::image{{}}, {citation_count} [@key], "
        f"{citations_list_count} ::citations{{}}, 0 leftover MDX components"
    )

    # Link rewriting needs the full URL map before any page renders: the
    # canonical page set, plus every name the live Gatsby site answers to.
    global _SITE_URLS
    _SITE_URLS = urls.SiteUrls.from_collections(
        collections, pages=staged_page_hrefs(), posts_per_page=POSTS_PER_PAGE
    )
    sample = next(iter(sorted(_SITE_URLS.pages - {"index.html"})), "index.html")
    print(f"  canonical URL style: {urls.URL_STYLE} (e.g. {urls.page_url(sample)})")

    print("Rendering through Papyrus's Markus renderer…")
    result = build_markus_site(
        content_dir=STAGING,
        out_dir=DIST,
        theme=None,
        site_css=POD_ROOT / "css" / "anthus-theme.css",
        chrome=ANTHUS_CHROME,
        sections=("platform",),
        images=IMAGES,
        citations=CITATIONS,
        transform=ANTHUS_TRANSFORM,
        vendor_css=False,
    )
    write_generated(result)

    rendered = {page.relative_to(result.out_dir).as_posix() for page in result.pages}
    if rendered != _SITE_URLS.pages:
        missing = sorted(_SITE_URLS.pages - rendered)
        extra = sorted(rendered - _SITE_URLS.pages)
        raise RuntimeError(
            "staged pages and rendered pages disagree; internal links were "
            f"resolved against the wrong set. staged-but-not-rendered={missing} "
            f"rendered-but-not-staged={extra}"
        )

    finish_pages(result)
    moved = relocate_pages(result)
    ruleset = write_custom_rules(_SITE_URLS)
    redirects = len(ruleset.rules)

    site_env.write_site_files(
        ENV,
        result.out_dir,
        (
            _canonical_url(page.relative_to(result.out_dir).as_posix())
            for page in result.pages
            if page.relative_to(result.out_dir).as_posix() != "404.html"
        ),
    )
    guarded_pages = site_env.assert_dist(ENV, result.out_dir)
    print(f"  {ENV.mode} guard assertions passed over {guarded_pages} HTML pages")

    print(f"\nBuilt Anth.us via Papyrus renderer: {result.out_dir}")
    print(f"  {len(result.pages)} pages, {redirects} redirect rules")
    print(f"  {moved} page(s) relocated to canonical {urls.URL_STYLE}-style paths")
    print(f"\nLegacy URL redirects (Amplify customRules -> {CUSTOM_RULES}):")
    for group, count in sorted(ruleset.counts.items(), key=lambda kv: -kv[1]):
        print(f"    {count:5d}  {group}")
    print(f"    {1:5d}  catch-all 404-200 (real 404 with custom page, kept last)")
    if ruleset.skipped:
        print(
            f"  {len(ruleset.skipped)} legacy URL(s) need no rule of their own; "
            "a pattern or a canonical page already covers them."
        )
    print("\nContent conversion report (parity accounting):")
    print(f"  responsive ::image{{}} directives     {image_count}")
    print(f"  plain :::figure (site chrome)       {report.static_figures}")
    print(f"  inline [@key] citation markers      {citation_count}")
    print(f"  ::citations{{}} bibliographies        {citations_list_count}")
    print(f"  legacy <Citation> converted         {report.citations}")
    print(f"  legacy <BlogImage> converted        {report.images}")
    print(f"  HTML tables -> GFM tables           {report.tables}")
    print(f"  <mark> preserved                     {report.marks}")
    print(f"  inline <svg> preserved               {report.svgs}")
    print(f"  colspan/rowspan tables preserved     {report.span_tables}")
    print(f"  JSX blockDiagram trees preserved     {report.diagrams}")
    if _UNRESOLVED_LINKS:
        total = sum(_UNRESOLVED_LINKS.values())
        print(
            f"\n{total} site-absolute link(s) to {len(_UNRESOLVED_LINKS)} path(s) "
            "with no page in this build (these are broken on production too):"
        )
        for path, count in sorted(_UNRESOLVED_LINKS.items(), key=lambda kv: -kv[1]):
            print(f"    {count:5d}  {path}")
    if report.dropped_html:
        buckets: dict[str, int] = {}
        for item in report.dropped_html:
            buckets[item] = buckets.get(item, 0) + 1
        print("  other dropped/approximated constructs:")
        for item, count in sorted(buckets.items(), key=lambda kv: -kv[1])[:20]:
            print(f"    {count:5d}  {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
