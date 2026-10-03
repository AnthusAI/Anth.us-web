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

import os
import re
import shutil
import sys
from html import escape
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

# Gatsby-absolute paths as authored across the content and the page copy.
_LINK_MAP = (
    (re.compile(r"^/blog/?$"), "/articles/index.html"),
    (re.compile(r"^/blog/([A-Za-z0-9._-]+)/?$"), r"/articles/\1.html"),
    (re.compile(r"^/platform/?$"), "/platform/index.html"),
    (re.compile(r"^/platform/([A-Za-z0-9._-]+)/?$"), r"/platform/\1.html"),
    (re.compile(r"^/posts/?$"), "/posts/index.html"),
    (re.compile(r"^/posts/(\d+)/?$"), r"/posts/page-\1.html"),
    (re.compile(r"^/ai-solutions/?$"), "/ai-solutions.html"),
    (re.compile(r"^/about/?$"), "/about.html"),
    (re.compile(r"^/ryan/?$"), "/ryan.html"),
    (re.compile(r"^/$"), "/index.html"),
)

_HREF_RE = re.compile(r'(?P<attr>\bhref=")(?P<url>/[^"]*)(?P<close>")')

# Populated from the discovered corpus before rendering. Lets a bare `/<slug>`
# (several articles cross-link each other without the `/blog/` prefix — broken
# on production too) and a capitalized `/blog/<Slug>` resolve to a real page.
_KNOWN_SLUGS: dict[str, str] = {}
_UNRESOLVED_LINKS: dict[str, int] = {}


def _map_path(path: str) -> str:
    # Already a built path. Without this guard `/platform/index.html` matched
    # the `/platform/<slug>` rule and became `/platform/index.html.html` —
    # 185 broken links across the site.
    if path.endswith(".html"):
        return path
    for pattern, replacement in _LINK_MAP:
        match = pattern.match(path)
        if not match:
            continue
        mapped = pattern.sub(replacement, path)
        # Slugs are normalized to lowercase at discovery (Papyrus only renders
        # lowercase collection slugs), so a link written against the authored
        # capitalization — e.g. /blog/Paytronix — has to be folded too.
        folded = re.sub(
            r"^/(articles|platform)/([^/]+)\.html$",
            lambda m: f"/{m.group(1)}/{m.group(2).lower()}.html",
            mapped,
        )
        return folded
    # A bare `/<slug>` that names a real article.
    bare = path.strip("/").lower()
    if bare and "/" not in bare and bare in _KNOWN_SLUGS:
        return f"/articles/{_KNOWN_SLUGS[bare]}.html"
    if path != "/":
        _UNRESOLVED_LINKS[path] = _UNRESOLVED_LINKS.get(path, 0) + 1
    return path


def _rewrite_internal_links(html: str) -> str:
    """Rewrite site-absolute Gatsby routes to this build's static paths.

    Done on rendered HTML rather than on Markdown so it also catches links
    that came out of front matter (``authors: <a href="/ryan">…</a>``) and out
    of the generated page copy, in one place.
    """

    def repl(match: re.Match[str]) -> str:
        url = match.group("url")
        if url.startswith("//") or url.startswith("/assets/"):
            return match.group(0)
        path, sep, tail = url.partition("#")
        if not sep:
            path, sep, tail = url.partition("?")
        mapped = _map_path(path)
        return f'{match.group("attr")}{mapped}{sep}{tail}{match.group("close")}'

    return _HREF_RE.sub(repl, html)


# --------------------------------------------------------------------------
# Social metadata
# --------------------------------------------------------------------------

_DEFAULT_COVER = "/assets/site/serverless-ai-software-solutions.png"
_PAGE_META: dict[str, tuple[str, str]] = {}  # active_href -> (description, image)


def _canonical_url(active_href: str) -> str:
    href = (active_href or "index.html").lstrip("/")
    if href in ("", "index.html"):
        return f"{SITE_ORIGIN}/"
    return f"{SITE_ORIGIN}/{href}"


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
    html = _rewrite_internal_links(html)
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


_REDIRECT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved</title>
<link rel="canonical" href="{canonical}">
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="refresh" content="0;url={target}">
</head>
<body>
<p>This page moved to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


def write_redirects(out_dir: Path, collections: Collections) -> int:
    """Emit meta-refresh stubs for the live site's URL shapes.

    Two sources:

    * ``/blog/<slug>`` — every article's production path. The canonical path
      here is ``/articles/<slug>.html`` (see anthus_content), so inbound links
      and bookmarks need a landing page.
    * ``redirect_from:`` front matter — the legacy slugs ``gatsby-node.js``
      turns into ``createRedirect`` calls.

    A meta refresh is the static equivalent of an Amplify redirect rule.
    Amplify ``customRules`` would be better (301 rather than 200 + refresh) but
    they are app configuration, not a repo file, and this build does not edit
    the Amplify app's rules.
    """
    count = 0
    blog_dir = out_dir / "blog"
    blog_dir.mkdir(parents=True, exist_ok=True)
    for node in collections.blog:
        target = f"/articles/{node.slug}.html"
        # Both the normalized slug and the authored one, which may differ in
        # case (`Paytronix`). Gatsby serves the authored spelling.
        for name in {node.slug, re.sub(r"[^A-Za-z0-9._-]", "", node.authored_slug)}:
            if not name:
                continue
            (blog_dir / f"{name}.html").write_text(
                _REDIRECT_TEMPLATE.format(canonical=_absolute(target), target=target),
                encoding="utf-8",
            )
            count += 1
        legacy = node.front_matter.get("redirect_from") or []
        if isinstance(legacy, str):
            legacy = [legacy]
        for slug in legacy:
            safe = re.sub(r"[^A-Za-z0-9._-]", "", str(slug))
            if not safe or safe == node.slug:
                continue
            (blog_dir / f"{safe}.html").write_text(
                _REDIRECT_TEMPLATE.format(canonical=_absolute(target), target=target),
                encoding="utf-8",
            )
            count += 1
    (blog_dir / "index.html").write_text(
        _REDIRECT_TEMPLATE.format(
            canonical=_absolute("/articles/index.html"), target="/articles/index.html"
        ),
        encoding="utf-8",
    )
    return count + 1


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

    # Link rewriting needs the slug set before any page renders.
    _KNOWN_SLUGS.update({node.slug: node.slug for node in collections.blog})
    for node in collections.blog:
        legacy = node.front_matter.get("redirect_from") or []
        if isinstance(legacy, str):
            legacy = [legacy]
        for old in legacy:
            _KNOWN_SLUGS.setdefault(str(old).strip().lower(), node.slug)

    images = ImageIndex.build(CONTENT_SUBMODULE, SITE_ASSETS)

    print("Staging Markus Markdown…")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    report = stage(collections, images)

    print("Rendering through Papyrus's Markus renderer…")
    result = build_markus_site(
        content_dir=STAGING,
        out_dir=DIST,
        theme=None,
        site_css=POD_ROOT / "css" / "anthus-theme.css",
        chrome=ANTHUS_CHROME,
        sections=("platform", "posts", "tags"),
    )
    for href in ("about.html", "ai-solutions.html", "ryan.html", "404.html"):
        build_standalone(result, STAGING / href.replace(".html", ".md"), href)

    redirects = write_redirects(result.out_dir, collections)

    (result.out_dir / "robots.txt").write_text(
        # Staging: refuse every crawler. Flip this when, and only when, the
        # port is promoted to a production domain.
        "User-agent: *\nDisallow: /\n",
        encoding="utf-8",
    )
    urls = sorted(
        {
            _canonical_url(page.relative_to(result.out_dir).as_posix())
            for page in result.pages
        }
    )
    body = "\n".join(f"  <url><loc>{escape(url, quote=True)}</loc></url>" for url in urls)
    (result.out_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n",
        encoding="utf-8",
    )

    print(f"\nBuilt Anth.us via Papyrus renderer: {result.out_dir}")
    print(f"  {len(result.pages)} pages, {redirects} redirect stubs")
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
