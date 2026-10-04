"""Canonical URL shape for the Anth.us port, and the legacy-URL redirect map.

Two halves of one decision live here.

``URL_STYLE`` — the single configuration point
----------------------------------------------
Papyrus's Markus renderer writes a page for ``articles/<slug>.md`` to
``articles/<slug>.html``. Production anth.us serves directory-style URLs
(``/articles/<slug>/``, ``/about/``), and Amplify Hosting itself prefers that
shape: it 301s ``/foo`` to ``/foo/`` and ``/foo.html`` to ``/foo/`` on its own
whenever the directory exists. So this build keeps Papyrus's *authoring* layout
and translates on the way out:

* :func:`page_url`    — the canonical, site-absolute URL of a page.
* :func:`page_output` — where that page's HTML is written inside ``dist``.

Every URL the build emits goes through one of those two functions. Nothing
concatenates ``".html"`` onto a slug by hand, so flipping ``ANTHUS_URL_STYLE``
to ``html`` restores the previous extension-style site in one place.

``legacy_rules`` — the redirect map
-----------------------------------
The live Gatsby site publishes **four** distinct URL shapes for the same
corpus, which is more than the ``/blog/<slug>/`` one that is obvious from
``gatsby-node.js``:

1. ``/blog/<frontmatter-slug>/`` — ``gatsby-node.js`` ``createPage``.
2. ``/blog/<tag>/``              — ``gatsby-node.js`` tag collections, sharing
   the ``/blog/`` namespace with (1). Where a tag and an article slug collide
   the **article** is what production serves (verified live on
   ``/blog/plexus/``, ``/blog/sqlbot/``, ``/blog/call-criteria/``).
3. ``/<file-stem>/`` and ``/solutions/<File-Stem>/`` —
   ``gatsby-plugin-page-creator`` is pointed at the content directory in
   ``gatsby-config.mjs``, so **every** MDX file also gets a URL derived from
   its path, with the authored capitalization and spaces intact. These are in
   production's sitemap, so they are published, not incidental.
4. ``/blog/`` + ``/blog/page/<n>/`` and ``/posts/`` + ``/posts/<n>/`` +
   ``/posts/page/<n>/`` — the listing and its pagination.

Amplify rule semantics, measured against the staging app rather than assumed:

* A ``301`` rule is matched **before** the filesystem, so a rule source must
  never equal a canonical URL. :func:`legacy_rules` asserts that.
* Trailing slashes are **not** normalized for matching: a request for
  ``/blog/x/`` only matches the source ``/blog/x/``. A request for ``/blog/x``
  is first 301'd to ``/blog/x/`` by Amplify and then matches. Every published
  legacy URL carries the trailing slash (production's sitemap uses it
  throughout), so sources are written with it and the bare form costs one extra
  hop rather than a second rule per article.
* A source segment containing a space must be written **percent-encoded**
  (``/blog/AI%20commodification/``); a literal space does not match.
* Live also answers ``/blog/x/index.html`` (S3 index document); a rule source
  matches the literal path, so each directory-style legacy rule has an
  ``index.html`` twin to the same target (``index_twin``).
* ``<name>`` placeholders match one segment and substitute into the target,
  including mid-segment (``/posts/page/<n>/`` -> ``/posts/page-<n>/``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import quote, unquote

#: ``directory`` emits ``/articles/<slug>/``; ``html`` emits
#: ``/articles/<slug>.html``. This is the only place the shape is decided.
URL_STYLE = (os.environ.get("ANTHUS_URL_STYLE") or "directory").strip().lower()
if URL_STYLE not in ("directory", "html"):
    raise SystemExit(f"ANTHUS_URL_STYLE must be 'directory' or 'html', got {URL_STYLE!r}")

#: Pages that keep their literal filename whatever the style. Amplify's error
#: document is configured by name, and a request that lands on it must not be
#: bounced again.
FIXED_HREFS = frozenset({"404.html"})

#: Top-level names the canonical site owns. A content file whose page-creator
#: URL would collide with one of these would have its canonical page shadowed
#: by its own legacy redirect, so the build refuses to emit that rule.
RESERVED_SEGMENTS = frozenset(
    {
        "404",
        "404.html",
        "about",
        "ai-solutions",
        "articles",
        "assets",
        "benchmarks",
        "biased-decisions",
        "blog",
        "css",
        "decision-models",
        "engage",
        "favicon.ico",
        "index",
        "index.html",
        "platform",
        "posts",
        "reading",
        "research",
        "robots.txt",
        "ryan",
        "sitemap.xml",
        "solutions",
        "tags",
    }
)

#: `collection.jsx`: 4 featured items then a grid of 8 on page 1, 8 per later page.
FEATURED_COUNT = 4
GRID_SIZE = 8


def collection_page_count(count: int) -> int:
    return 1 + -(-max(0, count - (FEATURED_COUNT + GRID_SIZE)) // GRID_SIZE)


def collection_href(directory: str, number: int) -> str:
    """Papyrus href of page ``number`` of the ``directory`` collection."""
    if number == 1:
        return f"{directory}/index.html"
    return f"{directory}/page/{number}/index.html"


#: Top-level generated pages, one Papyrus href each (``<name>.html``).
STANDALONE_PAGES = (
    "about",
    "ai-solutions",
    "ryan",
    "404",
    "index",
    "engage",
    "reading",
    "research",
    "decision-models",
    "benchmarks",
)

# `/icons/`, `/favicon-32x32.png` and `/manifest.webmanifest` come from web/static-root/.
_NON_PAGE_PREFIXES = ("/assets/", "/css/", "/icons/")
_NON_PAGE_FILES = frozenset(
    {"/robots.txt", "/sitemap.xml", "/favicon.ico", "/favicon-32x32.png", "/manifest.webmanifest"}
)


# --------------------------------------------------------------------------
# The shape
# --------------------------------------------------------------------------


def page_url(href: str) -> str:
    """Canonical site-absolute URL for the page Papyrus renders at ``href``.

    ``href`` is always a Papyrus-style relative output path, e.g.
    ``"articles/can-you-fix-it.html"`` or ``"index.html"``.
    """
    href = (href or "index.html").lstrip("/") or "index.html"
    if href in FIXED_HREFS or URL_STYLE == "html":
        return "/" + href
    if href == "index.html":
        return "/"
    if href.endswith("/index.html"):
        return "/" + href[: -len("index.html")]
    if href.endswith(".html"):
        return "/" + href[: -len(".html")] + "/"
    return "/" + href


def page_output(href: str) -> str:
    """Path inside ``dist`` for the page Papyrus renders at ``href``."""
    href = (href or "index.html").lstrip("/") or "index.html"
    if href in FIXED_HREFS or URL_STYLE == "html":
        return href
    url = page_url(href)
    return (url.lstrip("/") or "") + "index.html"


def is_non_page(path: str) -> bool:
    """True for a site-absolute path that is an asset, not a page."""
    return path.startswith(_NON_PAGE_PREFIXES) or path in _NON_PAGE_FILES


# --------------------------------------------------------------------------
# Resolving an authored path onto a page of this build
# --------------------------------------------------------------------------


def slugify(value: str) -> str:
    """Same normalization ``anthus_content`` applies to a front-matter slug."""
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-").lower()
    return value or "untitled"


def tag_slug(tag: str) -> str:
    """Same normalization ``anthus_pages.tag_pages`` applies to a tag name."""
    return (tag or "").strip().lower().replace(" ", "-")


@dataclass
class SiteUrls:
    """Every name the live site answers to, mapped onto this build's pages.

    Built once from the discovered corpus so the link rewriter and the redirect
    generator cannot disagree about what a legacy URL means.
    """

    #: Papyrus hrefs this build actually renders, e.g. ``articles/b0rd.html``.
    pages: set[str] = field(default_factory=set)
    #: lowercased ``/blog/<name>/`` segment -> canonical article slug. Used to
    #: *resolve* an authored link, where case folding is a feature.
    article_by_name: dict[str, str] = field(default_factory=dict)
    #: ``/blog/<name>/`` segment in its **authored** spelling -> canonical
    #: article slug. Used to *generate* rules, where case folding is not: an
    #: Amplify rule source matches case-sensitively, so ``/blog/Paytronix/``
    #: needs the capital P.
    blog_names: dict[str, str] = field(default_factory=dict)
    #: authored tag spelling -> merged tag page slug, in corpus order.
    tag_names: dict[str, str] = field(default_factory=dict)
    #: ``gatsby-plugin-page-creator`` path (``solutions/SQLBot``,
    #: ``people-skills``) -> canonical article slug, authored case preserved.
    article_by_path: dict[str, str] = field(default_factory=dict)
    #: lowercased ``/platform/<name>/`` segment -> canonical platform slug.
    platform_by_name: dict[str, str] = field(default_factory=dict)
    #: ``gatsby-plugin-page-creator`` path -> canonical platform slug.
    platform_by_path: dict[str, str] = field(default_factory=dict)
    #: authored tag, lowercased -> merged tag page slug.
    tag_by_name: dict[str, str] = field(default_factory=dict)
    #: number of ``/posts/`` pages, so ``/posts/7/`` is not invented.
    posts_pages: int = 1

    # -- construction ----------------------------------------------------

    @classmethod
    def from_collections(cls, collections, *, pages: set[str], posts_per_page: int) -> "SiteUrls":
        urls = cls(pages=set(pages))
        for node in collections.blog:
            urls._add_article(node)
        for node in collections.platform:
            urls._add_platform(node)
        for tag in collections.tags:
            urls.tag_by_name.setdefault(tag.strip().lower(), tag_slug(tag))
            urls.tag_names.setdefault(tag.strip(), tag_slug(tag))
        urls.posts_pages = collection_page_count(len(collections.posts))
        return urls

    def _add_article(self, node) -> None:
        legacy = node.front_matter.get("redirect_from") or []
        if isinstance(legacy, str):
            legacy = [legacy]
        names = [node.slug, node.authored_slug, slugify(node.authored_slug)]
        names += [str(old).strip() for old in legacy]
        if not node.front_matter.get("slug"):
            # `gatsby-node.js` builds `/blog/${frontmatter.slug}/`, and a post
            # without a `slug` therefore publishes at `/blog/null/`. Production
            # serves it (it is in its sitemap), so it redirects here too.
            names.append("null")
        for name in names:
            if not name:
                continue
            self.article_by_name.setdefault(name.lower(), node.slug)
            self.blog_names.setdefault(name, node.slug)
        path = _creator_path(node)
        if path is not None:
            self.article_by_path[path] = node.slug

    def add_content_redirect_stubs(self, redirect_stubs_directory) -> None:
        """The content repository keeps retired article names as meta-refresh
        stubs at ``redirects/<name>/index.html`` pointing at ``/blog/<target>/``.
        Each stub's name becomes one more name for the article it points at."""
        if not redirect_stubs_directory.is_dir():
            return
        for stub_page in sorted(redirect_stubs_directory.glob("*/index.html")):
            refresh_target = re.search(
                r"url=/blog/([^/\"']+)/", stub_page.read_text(encoding="utf-8")
            )
            if not refresh_target:
                continue
            target_slug = self.article_by_name.get(refresh_target.group(1).lower())
            if target_slug is None:
                continue
            retired_name = stub_page.parent.name
            self.article_by_name.setdefault(retired_name.lower(), target_slug)
            self.blog_names.setdefault(retired_name, target_slug)

    def _add_platform(self, node) -> None:
        for name in (node.slug, node.authored_slug, slugify(node.authored_slug)):
            if name:
                self.platform_by_name.setdefault(name.lower(), node.slug)
        path = _creator_path(node)
        if path is not None:
            self.platform_by_path[path] = node.slug

    # -- resolution ------------------------------------------------------

    def resolve(self, path: str) -> str | None:
        """Map a site-absolute authored path onto a Papyrus href, or ``None``.

        Accepts every shape the content and the generated page copy use: live
        Gatsby routes (``/blog/x/``, ``/solutions/SQLBot/``, bare ``/x/``),
        paths already in this build's own output shape (``/articles/x.html``,
        ``/articles/x/``), and percent-encoded segments.
        """
        href = self._candidate(path)
        if href is not None and href in self.pages:
            return href
        return None

    def _candidate(self, path: str) -> str | None:
        raw = unquote(path or "")
        segments = [s for s in raw.strip("/").split("/") if s]
        if not segments:
            return "index.html"

        # Paths already in this build's output shape, from the generated page
        # copy in anthus_pages and from Papyrus's own relative chrome links.
        if segments[-1].endswith(".html"):
            direct = "/".join(segments)
            if direct in self.pages:
                return direct
            lowered = "/".join(segments[:-1] + [segments[-1].lower()])
            if lowered in self.pages:
                return lowered
            segments = segments[:-1] + [segments[-1][: -len(".html")]]
            if segments[-1] == "index":
                segments = segments[:-1] or ["index"]

        head = segments[0].lower()
        rest = segments[1:]

        if head == "blog":
            if not rest:
                return "articles/index.html"
            if len(rest) == 2 and rest[0].lower() == "page" and rest[1].isdigit():
                return collection_href("articles", int(rest[1]))
            if len(rest) == 1:
                name = rest[0].lower()
                # Article before tag: that is what production serves where a
                # tag name and an article slug collide.
                if name in self.article_by_name:
                    return f"articles/{self.article_by_name[name]}.html"
                if name in self.tag_by_name:
                    return f"tags/{self.tag_by_name[name]}.html"
            return None

        if head == "articles":
            if not rest:
                return "articles/index.html"
            if len(rest) == 2 and rest[0].lower() == "page" and rest[1].isdigit():
                return collection_href("articles", int(rest[1]))
            if len(rest) == 1:
                name = rest[0].lower()
                return f"articles/{self.article_by_name.get(name, name)}.html"
            return None

        if head == "platform":
            if not rest:
                return "platform/index.html"
            if len(rest) == 1:
                name = rest[0].lower()
                return f"platform/{self.platform_by_name.get(name, name)}.html"
            return None

        if head == "posts":
            if not rest:
                return "posts/index.html"
            number = None
            if len(rest) == 1 and rest[0].isdigit():
                number = int(rest[0])
            elif len(rest) == 2 and rest[0].lower() == "page" and rest[1].isdigit():
                number = int(rest[1])
            elif len(rest) == 1 and rest[0].lower().startswith("page-"):
                tail = rest[0][len("page-") :]
                number = int(tail) if tail.isdigit() else None
            return collection_href("posts", number) if number else None

        if head in ("research", "reading") and len(rest) == 2 and rest[0].lower() == "page":
            return collection_href(head, int(rest[1])) if rest[1].isdigit() else None

        if head == "tags":
            if not rest:
                return "tags/index.html"
            if len(rest) == 1:
                return f"tags/{tag_slug(rest[0])}.html"
            return None

        if not rest and head in STANDALONE_PAGES:
            return f"{head}.html"

        # gatsby-plugin-page-creator paths: the authored file path, at any
        # depth, with its authored capitalization. Matched case-SENSITIVELY,
        # the way S3 and production match: `/solutions/SQLBot/` is a page and
        # `/solutions/sqlbot/` is a 404 on anth.us today. Folding case here
        # would quietly repair a broken content link instead of reporting it.
        joined = "/".join(segments)
        for table, directory in (
            (self.article_by_path, "articles"),
            (self.platform_by_path, "platform"),
        ):
            if joined in table:
                return f"{directory}/{table[joined]}.html"

        # A bare `/<slug>` naming an article by its front-matter slug rather
        # than by its file path. Several articles cross-link each other that
        # way; production 404s on those, this build resolves them.
        if len(segments) == 1:
            name = segments[0].lower()
            if name in self.article_by_name:
                return f"articles/{self.article_by_name[name]}.html"
            if name in self.platform_by_name:
                return f"platform/{self.platform_by_name[name]}.html"
        return None


def _creator_path(node) -> str | None:
    """The URL ``gatsby-plugin-page-creator`` derives from a node's file path.

    ``gatsby-config.mjs`` ignores ``**/posts/**`` for the page creator, so a
    short post has no path-derived URL — only its ``/blog/<slug>/`` one.
    """
    stem = node.source.stem
    if node.rel_dir == "posts":
        return None
    return f"{node.rel_dir}/{stem}" if node.rel_dir else stem


# --------------------------------------------------------------------------
# Amplify customRules
# --------------------------------------------------------------------------

#: Kept last; every generated rule has to come before it or an unmatched legacy
#: URL 404s instead of redirecting. Status MUST be "404-200": measured on
#: Amplify (PPY-fdb5e9), "404-200" serves 404.html AT the requested URL with
#: HTTP 404, while plain "404" answers 302 -> /404.html (200), and having no
#: catch-all at all gives a real 404 with an EMPTY body.
CATCH_ALL_RULE = {"source": "/<*>", "target": "/404.html", "status": "404-200"}


def _encode(segment: str) -> str:
    """Percent-encode one path segment for an Amplify rule source.

    Measured: ``/blog/AI commodification/`` written with a literal space never
    matches; ``/blog/AI%20commodification/`` does.
    """
    return quote(segment, safe="")


def _source(*segments: str) -> str:
    return "/" + "/".join(_encode(s) for s in segments) + "/"


@dataclass
class RuleSet:
    """Generated rules plus the accounting the build prints."""

    rules: list[dict] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    def add(self, group: str, source: str, target: str, *, index_twin: bool = False) -> None:
        self.rules.append({"source": source, "target": target, "status": "301"})
        self.counts[group] = self.counts.get(group, 0) + 1
        if index_twin:
            # Live is S3 + an index document, so `/blog/x/index.html` answers
            # 200 as well as `/blog/x/`. Amplify matches the literal path, so
            # the same source plus `index.html` needs its own rule, to the same
            # target. Emitted right after the rule it mirrors, so it keeps that
            # rule's position (specific before pattern).
            assert source.endswith("/"), source
            self.rules.append({"source": source + "index.html", "target": target, "status": "301"})
            self.counts[group + " (index.html)"] = self.counts.get(group + " (index.html)", 0) + 1


def legacy_rules(
    urls: SiteUrls,
    *,
    og_images: dict[str, list[str]] | None = None,
    page_images: dict[str, str] | None = None,
    dist=None,
) -> RuleSet:
    """301 rules from every published Gatsby URL shape onto its canonical form.

    Order is load-bearing: Amplify takes the first matching rule, and the
    generic ``/blog/<slug>/`` pattern would otherwise swallow the tag and
    pagination URLs that share that namespace.
    """
    out = RuleSet()
    articles_url = page_url("articles/index.html")

    def canonical(href: str) -> str:
        return page_url(href)

    # 1. Listings and pagination. Specific, so they precede the patterns.
    #    Production now serves /blog/page/<n>/ and /posts/page/<n>/ (and
    #    /posts/<n>/ as a meta-refresh stub); the canonical namespace here is
    #    /articles/page/<n>/ and /posts/page/<n>/.
    out.add("blog index", "/blog/", articles_url, index_twin=True)
    out.add("blog pagination", "/blog/page/1/", articles_url, index_twin=True)
    out.add("blog pagination", "/blog/page/<n>/", "/articles/page/<n>/", index_twin=True)
    posts_index = page_url("posts/index.html")
    out.add("posts pagination", "/posts/1/", posts_index, index_twin=True)
    out.add("posts pagination", "/posts/page/1/", posts_index, index_twin=True)
    # `/posts/<n>/` has to be enumerated: as a pattern, `<n>` would also match
    # the literal `/posts/page/`, and a 301 rule beats the filesystem.
    for number in range(2, urls.posts_pages + 1):
        out.add(
            "posts pagination",
            f"/posts/{number}/",
            canonical(collection_href("posts", number)),
            index_twin=True,
        )
    # Shapes this staging site published before the canonical form moved:
    # `/posts/page-<n>/`. Two segments, so it cannot collide with `/posts/page/<n>/`.
    out.add("posts pagination", "/posts/page-<n>/", "/posts/page/<n>/")

    # 2. Everything else in the shared /blog/ namespace, resolved to one
    #    target per authored spelling. Articles are inserted first and win any
    #    collision with a tag of the same name, which is what production
    #    serves. These must precede the generic pattern in (3).
    blog_targets: dict[str, str] = {}
    for name, slug in urls.blog_names.items():
        blog_targets.setdefault(name, f"articles/{slug}.html")
    for tag, slug in urls.tag_names.items():
        shadowing = urls.article_by_name.get(tag.lower())
        blog_targets.setdefault(
            tag, f"articles/{shadowing}.html" if shadowing else f"tags/{slug}.html"
        )
    for name, href in sorted(blog_targets.items()):
        if href == f"articles/{name}.html":
            # The pattern in (3) already maps this exactly; a rule would be
            # 120-odd lines of noise saying the same thing.
            out.skipped.append(f"/blog/{name}/ -> covered by the /blog/<slug>/ pattern")
            continue
        group = "blog tag" if href.startswith("tags/") else "blog alias"
        out.add(group, _source("blog", name), canonical(href), index_twin=True)

    # 3. The generic article rule. One pattern for the whole corpus, so a new
    #    article needs no new rule as long as its slug is already normalized.
    out.add(
        "blog article pattern",
        "/blog/<slug>/",
        canonical("articles/<slug>.html"),
        index_twin=True,
    )

    # 4. gatsby-plugin-page-creator paths. The authored capitalization and the
    #    spaces rule out a pattern, so these are one rule per file.
    for table, directory in (
        (urls.article_by_path, "articles"),
        (urls.platform_by_path, "platform"),
    ):
        for path, slug in sorted(table.items()):
            segments = path.split("/")
            if len(segments) == 1 and segments[0].lower() in RESERVED_SEGMENTS:
                out.skipped.append(
                    f"/{path}/ -> reserved by a canonical page; no rule emitted"
                )
                continue
            source = _source(*segments)
            target = canonical(f"{directory}/{slug}.html")
            if source == target:
                continue  # already canonical; a rule here would be a loop
            out.add(f"{directory} path", source, target, index_twin=True)

    # 5. Shared link previews (PPY-5a64a2). Every link already shared on social
    #    media embeds the old Gatsby og:image URL (`/static/<hash>/<hash>/<file>`),
    #    which 404s after cutover. `og_images` maps each live page path to the
    #    URLs read from the live build (web/legacy-og-images.json); the target is
    #    the image this port gives the same page (`page_images`, by Papyrus href).
    #    Only the og:image/twitter:image URLs, not every /static/ rendition.
    for live_path, old_urls in sorted((og_images or {}).items()):
        href = urls.resolve(live_path)
        image = (page_images or {}).get(href) if href else None
        if not image:
            out.skipped.append(f"{live_path} og:image -> page not in this build")
            continue
        for old in old_urls:
            source = _static_source(old)
            existing = next((r for r in out.rules if r["source"] == source), None)
            if existing is not None:
                if existing["target"] != image:
                    raise RuntimeError(
                        f"{old} is the og:image of pages that map to different "
                        f"images here: {existing['target']} vs {image}"
                    )
                continue
            out.add("og:image", source, image)

    out.rules.append(dict(CATCH_ALL_RULE))

    _assert_no_shadowed_pages(out.rules, urls)
    _assert_index_twins(out.rules, dist)
    _assert_og_rules(out.rules, dist)
    return out


def _static_source(path: str) -> str:
    """An old `/static/...` path as an Amplify rule source (percent-encoded)."""
    return "/" + "/".join(_encode(unquote(seg)) for seg in path.strip("/").split("/"))


def _assert_og_rules(rules: list[dict], dist) -> None:
    """og:image rules: no chains, and (when the output exists) real targets."""
    sources = {r["source"] for r in rules}
    for rule in rules:
        if rule["status"] != "301" or not unquote(rule["source"]).startswith("/static/"):
            continue
        if rule["target"] in sources:
            raise RuntimeError(f"og:image rule {rule['source']} chains into {rule['target']}")
        if dist is not None:
            if not (dist / unquote(rule["target"]).lstrip("/")).is_file():
                raise RuntimeError(f"og:image rule {rule['source']}: target {rule['target']} is not in dist")
            if (dist / unquote(rule["source"]).lstrip("/")).exists():
                raise RuntimeError(f"og:image rule {rule['source']} would shadow a file in dist")


def _assert_index_twins(rules: list[dict], dist) -> None:
    """`.../index.html` rules: no chains, and (when the output exists) they
    shadow no file and point at a real page."""
    sources = {r["source"] for r in rules}
    for rule in rules:
        if rule["status"] != "301" or not rule["source"].endswith("/index.html"):
            continue
        if rule["target"] in sources or rule["target"] == rule["source"]:
            raise RuntimeError(f"index.html rule {rule['source']} chains into {rule['target']}")
        if dist is None or "<" in rule["source"]:
            continue
        if (dist / unquote(rule["source"]).lstrip("/")).exists():
            raise RuntimeError(f"index.html rule {rule['source']} would shadow a file in dist")
        if "<" not in rule["target"] and not (
            dist / unquote(rule["target"]).lstrip("/") / "index.html"
        ).is_file():
            raise RuntimeError(f"index.html rule {rule['source']}: target {rule['target']} is not in dist")


def _assert_no_shadowed_pages(rules: list[dict], urls: SiteUrls) -> None:
    """A 301 rule beats the filesystem, so no rule may shadow a real page."""
    canonical_urls = {page_url(href) for href in urls.pages}
    for rule in rules:
        if rule["status"] != "301":
            continue
        source = unquote(rule["source"])
        if "<" in source:
            continue
        if source in canonical_urls:
            raise RuntimeError(
                f"redirect rule {rule['source']} would shadow the canonical page "
                f"it should serve ({source})"
            )
        if source == rule["target"]:
            raise RuntimeError(f"redirect rule {rule['source']} points at itself")
