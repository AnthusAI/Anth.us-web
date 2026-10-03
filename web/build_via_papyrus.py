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
from papyrus_content.markus_renderer.shell import NavItem, SiteChrome  # noqa: E402

import anthus_pages as pages  # noqa: E402
import anthus_urls as urls  # noqa: E402
from anthus_content import (  # noqa: E402
    POSTS_PER_PAGE,
    Collections,
    ConversionReport,
    ImageIndex,
    discover,
    stage_nodes,
)
from anthus_mdx import normalize_body, split_front_matter, staged_markdown, write_if_changed  # noqa: E402

CONTENT_SUBMODULE = REPO_ROOT / "content" / "anthus-site-content"
SITE_ASSETS = POD_ROOT / "assets" / "site"
STAGING = POD_ROOT / "staging"
DIST = POD_ROOT / "dist-papyrus"

# Staging deployment. Deliberately NOT https://anth.us — canonical URLs and
# og:url must not claim to be the production site while this is under review,
# or a crawler that reaches the staging host will attribute the content to
# production (or worse, vice versa). Amplify injects AWS_APP_ID /
# AWS_BRANCH at build time; fall back to a relative-only build locally.
_APP_ID = os.environ.get("AWS_APP_ID", "")
_BRANCH = os.environ.get("AWS_BRANCH", "")
if _APP_ID and _BRANCH:
    SITE_ORIGIN = f"https://{_BRANCH}.{_APP_ID}.amplifyapp.com"
else:
    SITE_ORIGIN = os.environ.get("ANTHUS_SITE_ORIGIN", "http://localhost:8080")


# --------------------------------------------------------------------------
# Chrome
# --------------------------------------------------------------------------

_FOOTER_ANTHUS_LINKS = (
    ("AI Solutions", "/ai-solutions.html"),
    ("Anthus Platform", "/platform/index.html"),
    ("Articles", "/articles/index.html"),
    ("About", "/about.html"),
    ("Posts", "/posts/index.html"),
)

# anthus-footer `getPlatformLinks()` — the live platform properties. The real
# footer is a React component from a separate GitHub package
# (github:AnthusAI/anthus-footer); a static build cannot mount it, so the same
# canonical link set is reproduced here as markup.
_FOOTER_PLATFORM_LINKS = (
    ("Plexus", "https://plexus.anth.us/", "MLOps platform for agent evaluation and iteration."),
    ("Tactus", "https://tactus.anth.us/", "Durable runtime for agent procedures."),
    ("Korporus", "https://korpor.us/", "Agent operating system and federated shell."),
    ("Biblicus", "https://github.com/AnthusAI/Biblicus", "Corpus analysis for extraction and retrieval."),
    ("Babulus", "https://babul.us/", "Marketing automation built around VideoML."),
    ("Kanbus", "https://kanb.us/", "Durable multi-agent task management."),
    ("Caducus", "https://caduc.us/", "Monitoring, alerts, and operator support."),
)

# anthus-footer `defaultCommunityLinks`.
_FOOTER_COMMUNITY_LINKS = (
    ("Contact us", pages.CONTACT_URL),
    ("GitHub", "https://github.com/AnthusAI"),
    ("LinkedIn", "https://www.linkedin.com/in/ryanalynporter/"),
    ("Discord", "https://discord.gg/uStyWraJ2M"),
)


def _footer_html() -> str:
    def column(title: str, items) -> str:
        links = "".join(
            f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>'
            for label, href, *_rest in items
        )
        return f'<div class="anthus-footer-col"><h2>{escape(title)}</h2><ul>{links}</ul></div>'

    return (
        '<div class="anthus-footer">'
        '<p class="anthus-footer-blurb">Anthus builds AI-native systems with durable '
        "procedures, operational guardrails, and reusable platform components.</p>"
        '<div class="anthus-footer-cols">'
        + column("Anthus", _FOOTER_ANTHUS_LINKS)
        + column("Platform", _FOOTER_PLATFORM_LINKS)
        + column("Community", _FOOTER_COMMUNITY_LINKS)
        + "</div>"
        '<p class="anthus-footer-staging">Staging preview of the Papyrus/Markus port. '
        "Not the production anth.us site.</p>"
        "</div>"
    )


ANTHUS_CHROME = SiteChrome(
    site_name=pages.SITE_TITLE,
    tagline=None,
    footer_html=_footer_html(),
    scripts=("assets/site-nav.js",),
)

# gatsby-config.mjs siteMetadata.menuLinks is the nav contract, not one link
# per article (Papyrus's default would flood the header with 130 entries).
markus_build._build_nav_items = lambda articles: [
    NavItem(label, href) for label, href in pages.MENU
]


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


def _canonical_url(active_href: str) -> str:
    return f"{SITE_ORIGIN}{urls.page_url(active_href)}"


def _absolute(src: str) -> str:
    if src.startswith(("http://", "https://")):
        return src
    return f"{SITE_ORIGIN}/{src.lstrip('/')}"


def _inject_social_meta(html: str, *, title: str, active_href: str) -> str:
    description, image = _PAGE_META.get(
        active_href, (pages.SITE_DESCRIPTION, _DEFAULT_COVER)
    )
    if not description:
        description = pages.SITE_DESCRIPTION
    if not image:
        image = _DEFAULT_COVER
    page_title = (title or "").strip() or pages.SITE_TITLE
    is_home = active_href in ("", "index.html")
    url = _canonical_url(active_href)

    def q(value: str) -> str:
        return escape(value, quote=True)

    meta = (
        f'<meta name="description" content="{q(description)}">\n'
        f'<link rel="canonical" href="{q(url)}">\n'
        f'<meta property="og:site_name" content="{q(pages.SITE_TITLE)}">\n'
        f'<meta property="og:type" content="{"website" if is_home else "article"}">\n'
        f'<meta property="og:title" content="{q(page_title)}">\n'
        f'<meta property="og:description" content="{q(description)}">\n'
        f'<meta property="og:url" content="{q(url)}">\n'
        f'<meta property="og:image" content="{q(_absolute(image))}">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:creator" content="@RyanAlynPorter">\n'
        f'<meta name="twitter:title" content="{q(page_title)}">\n'
        f'<meta name="twitter:description" content="{q(description)}">\n'
        f'<meta name="twitter:image" content="{q(_absolute(image))}">\n'
        # Staging must never be indexed. This is the single guard that keeps a
        # full copy of the marketing site out of search results while the port
        # is under review; robots.txt alone does not stop an already-known URL.
        '<meta name="robots" content="noindex, nofollow">\n'
    )
    if 'property="og:title"' in html:
        return html
    html2, count = re.subn(r"(</title>\s*)", r"\1" + meta, html, count=1)
    if count != 1:
        raise RuntimeError(f"social meta inject failed for {active_href!r}")
    return html2


_orig_render_page = markus_shell.render_page


def render_page_anthus(**kwargs):
    """Anthus chrome pass over Papyrus's rendered page."""
    html = _orig_render_page(**kwargs)
    active_href = kwargs.get("active_href") or "index.html"
    html = _rewrite_internal_links(html, active_href=active_href)
    html = _inject_social_meta(
        html, title=kwargs.get("title") or "", active_href=active_href
    )
    return html


markus_shell.render_page = render_page_anthus
markus_build.render_page = render_page_anthus


# --------------------------------------------------------------------------
# Staging
# --------------------------------------------------------------------------


def _register_meta(href: str, description: str, image: str | None) -> None:
    _PAGE_META[href] = (description, image or _DEFAULT_COVER)


def stage(collections: Collections, images: ImageIndex) -> ConversionReport:
    STAGING.mkdir(parents=True, exist_ok=True)
    report = ConversionReport()

    # The blog corpus. `build_markus_site` hard-requires `articles/`, which is
    # why the canonical reader path is /articles/<slug>.html; see
    # anthus_content's module docstring.
    report.merge(
        stage_nodes(collections.blog, staging=STAGING, directory="articles", images=images)
    )

    # Platform products carry the platform-product.jsx chrome around the body.
    platform_dir = STAGING / "platform"
    platform_dir.mkdir(parents=True, exist_ok=True)
    for node in collections.platform:
        _, body = split_front_matter(node.source.read_text(encoding="utf-8"))
        text, node_report = normalize_body(
            body,
            resolve_image_name=images.resolve_name,
            resolve_image_path=lambda src, n=node: images.resolve_path(
                src, relative_to=n.source
            ),
        )
        report.merge(node_report)
        document = (
            pages.platform_product_head(node)
            + text
            + pages.platform_product_tail(node)
        )
        write_if_changed(
            platform_dir / f"{node.slug}.md",
            staged_markdown({"title": node.title, "date": node.display_date}, document),
        )
        _register_meta(
            f"platform/{node.slug}.html",
            node.excerpt_text,
            pages._preview(node, images),
        )

    for node in collections.blog:
        _register_meta(
            f"articles/{node.slug}.html", node.excerpt_text, pages._preview(node, images)
        )

    # Listings and bespoke pages.
    write_if_changed(
        STAGING / "index.md",
        pages.homepage(
            articles=collections.articles, posts=collections.posts, images=images
        ),
    )
    write_if_changed(
        STAGING / "articles" / "index.md",
        pages.articles_index(collections.articles, images),
    )
    write_if_changed(STAGING / "platform" / "index.md", pages.platform_index(collections.platform))
    write_if_changed(STAGING / "about.md", pages.about_page())
    write_if_changed(
        STAGING / "ai-solutions.md",
        pages.ai_solutions_page(collections.solutions, images),
    )
    write_if_changed(STAGING / "ryan.md", pages.ryan_page(collections.solutions, images))
    write_if_changed(STAGING / "404.md", pages.not_found_page())

    posts_dir = STAGING / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    for name, text in pages.posts_pages(collections.posts, images, POSTS_PER_PAGE).items():
        write_if_changed(posts_dir / name, text)

    tags_dir = STAGING / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)
    for name, text in pages.tag_pages(collections.tags).items():
        write_if_changed(tags_dir / name, text)

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
    # The generated page copy in anthus_pages hard-codes `/assets/site/…`
    # paths (the hero, the four capability tiles, the lifecycle diagram), so
    # those files are never "resolved" and never land in `used_site` — relying
    # on the index left every one of them a 404 while the build reported
    # success.
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
    if (POD_ROOT / "assets" / "site-nav.js").is_file():
        shutil.copy2(POD_ROOT / "assets" / "site-nav.js", staging_assets / "site-nav.js")

    # Fail loudly on a chrome image the generated pages reference but that is
    # not committed — a silently broken hero is worse than a failed build.
    referenced = {
        match
        for text in (
            (STAGING / "index.md").read_text(encoding="utf-8"),
            (STAGING / "about.md").read_text(encoding="utf-8"),
            (STAGING / "ai-solutions.md").read_text(encoding="utf-8"),
        )
        # Filenames contain spaces ("Anthus AI Application Lifecycle.png"),
        # so stop only at the closing quote or paren, never at whitespace.
        for match in re.findall(r"/assets/site/([^\"')]+)", text)
    }
    absent = sorted(name for name in referenced if not (staging_assets / "site" / name).is_file())
    if absent:
        raise RuntimeError(
            "Generated pages reference site assets that are not committed in "
            f"web/assets/site/: {', '.join(absent)}"
        )
    return report


# --------------------------------------------------------------------------
# Standalone pages and redirects
# --------------------------------------------------------------------------


def build_standalone(result, source: Path, href: str) -> None:
    """Render one depth-0 page that is not part of a discovered collection.

    ``build_markus_site`` only walks ``articles/`` plus the named ``sections``,
    so the bespoke pages (``about``, ``ai-solutions``, ``ryan``, ``404``) need
    their own write. Same pattern as Pilobol.us's ``_build_standalone_page``.
    """
    if not source.is_file():
        raise RuntimeError(f"Standalone page source not found: {source}")
    css_version = markus_build._css_version(result.out_dir / "css", result.out_dir / "assets")
    fragment = markus_build.convert_fragment(source, theme=None)
    title = markus_build._read_title(source, href)
    page_path = result.out_dir / href
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        markus_build.render_page(
            title=title,
            fragment=fragment,
            active_href=href,
            nav_items=markus_build._build_nav_items([]),
            depth=0,
            chrome=ANTHUS_CHROME,
            css_version=css_version,
        ),
        encoding="utf-8",
    )
    result.pages.append(page_path)


# --------------------------------------------------------------------------
# Canonical output shape
# --------------------------------------------------------------------------

#: Papyrus's collection discovery filter. A staged file it rejects is a page
#: that silently never renders, so link resolution has to apply the same test.
_PAPYRUS_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")
_STANDALONE_HREFS = ("about.html", "ai-solutions.html", "ryan.html", "404.html")
_RENDERED_DIRS = ("articles", "platform", "posts", "tags")


def staged_page_hrefs() -> set[str]:
    """Predict the Papyrus hrefs this build renders, from the staged tree.

    `build_markus_site` walks `articles/` plus the named sections and accepts
    only `_PAGE_SLUG`-shaped filenames; `build_standalone` adds the four
    depth-0 pages. Predicting the set here lets every internal link be
    resolved against real pages during rendering, and `main` then asserts the
    prediction against what was actually written -- which is how a staged page
    that Papyrus quietly skipped would now fail the build instead of becoming
    a 404 behind a successful deploy.
    """
    hrefs = {"index.html", *_STANDALONE_HREFS}
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
CUSTOM_RULES = POD_ROOT / "custom-rules.json"


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

    print("Staging Markus Markdown…")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    report = stage(collections, images)

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
        sections=("platform", "posts", "tags"),
    )
    for href in _STANDALONE_HREFS:
        build_standalone(result, STAGING / href.replace(".html", ".md"), href)

    rendered = {page.relative_to(result.out_dir).as_posix() for page in result.pages}
    if rendered != _SITE_URLS.pages:
        missing = sorted(_SITE_URLS.pages - rendered)
        extra = sorted(rendered - _SITE_URLS.pages)
        raise RuntimeError(
            "staged pages and rendered pages disagree; internal links were "
            f"resolved against the wrong set. staged-but-not-rendered={missing} "
            f"rendered-but-not-staged={extra}"
        )

    moved = relocate_pages(result)
    ruleset = write_custom_rules(_SITE_URLS)
    redirects = len(ruleset.rules)

    (result.out_dir / "robots.txt").write_text(
        # Staging: refuse every crawler. Flip this when, and only when, the
        # port is promoted to a production domain.
        "User-agent: *\nDisallow: /\n",
        encoding="utf-8",
    )
    sitemap_urls = sorted(
        {
            _canonical_url(page.relative_to(result.out_dir).as_posix())
            for page in result.pages
        }
    )
    body = "\n".join(
        f"  <url><loc>{escape(url, quote=True)}</loc></url>" for url in sitemap_urls
    )
    (result.out_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n",
        encoding="utf-8",
    )

    print(f"\nBuilt Anth.us via Papyrus renderer: {result.out_dir}")
    print(f"  {len(result.pages)} pages, {redirects} redirect rules")
    print(f"  {moved} page(s) relocated to canonical {urls.URL_STYLE}-style paths")
    print(f"\nLegacy URL redirects (Amplify customRules -> {CUSTOM_RULES}):")
    for group, count in sorted(ruleset.counts.items(), key=lambda kv: -kv[1]):
        print(f"    {count:5d}  {group}")
    print(f"    {1:5d}  catch-all 404 (pre-existing, kept last)")
    if ruleset.skipped:
        print(
            f"  {len(ruleset.skipped)} legacy URL(s) need no rule of their own; "
            "a pattern or a canonical page already covers them."
        )
    print("\nContent conversion report (parity accounting):")
    print(f"  images converted to :::figure      {report.images}")
    print(f"  <Citation> -> numbered reference    {report.citations}")
    print(f"  <CitationsList> -> ## References    {report.citation_lists}")
    print(f"  HTML tables -> GFM tables           {report.tables}")
    print(f"  <mark> -> bold (styling lost)        {report.marks}")
    print(f"  inline <svg> dropped                 {report.dropped_svg}")
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
