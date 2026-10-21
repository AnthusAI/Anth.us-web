"""The URL map of the site: canonical links, and the redirects of every URL the previous sites answered to."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from html import escape, unescape

import anthus_urls as urls
import site_support as support
from anthus_content import POSTS_PER_PAGE, Collections
from cards import _preview
from papyrus_content.projection.writers import request_paths_for_key

REDIRECTS_DIRECTORY = support.WEB / "content-redirects"
LEGACY_OG_IMAGES = support.WEB / "legacy-og-images.json"
LEGACY_REDIRECT_RULES = support.WEB / "legacy-redirect-rules.json"
DEFAULT_COVER = "/assets/site/share-card.png"

_REF_RE = re.compile(r'\b(?P<attr>href|src)="(?P<url>[^"]*)"')
_SRCSET_RE = re.compile(r'\bsrcset="(?P<value>[^"]*)"')
_SKIP_PREFIXES = ("//", "#", "?", "data:", "mailto:", "tel:", "http://", "https://")


def _generated_hrefs(collections: Collections) -> set[str]:
    """The Papyrus hrefs of the generated pages: home, collections, tags, the authored pages."""
    hrefs = {f"{name}.html" for name in urls.STANDALONE_PAGES}
    hrefs.add("platform/index.html")
    for directory, count in (("articles", len(collections.articles)), ("posts", len(collections.posts))):
        for number in range(1, urls.collection_page_count(count) + 1):
            hrefs.add(urls.collection_href(directory, number))
    hrefs |= {f"tags/{urls.tag_slug(tag)}.html" for tag in collections.tags}
    hrefs.add("tags/index.html")
    return hrefs


class UrlMap:
    """Every name the previous site answered to, mapped onto this site's pages."""

    def __init__(self, site) -> None:
        self.site = site
        collections = support.collections(site)
        pages = _generated_hrefs(collections)
        pages |= {f"articles/{node_slug}.html" for node_slug in (node.slug for node in collections.blog)}
        pages |= {f"platform/{node.slug}.html" for node in collections.platform}
        self.pages = pages
        self.urls = urls.SiteUrls.from_collections(collections, pages=pages, posts_per_page=POSTS_PER_PAGE)
        self.urls.add_content_redirect_stubs(REDIRECTS_DIRECTORY)
        self.unresolved: dict[str, int] = {}

    def fingerprint(self) -> str:
        fields = {name: (sorted(value) if isinstance(value, set) else value) for name, value in vars(self.urls).items()}
        return hashlib.sha256(json.dumps(fields, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]

    def absolutize(self, url: str, *, base_dir: str) -> str:
        """One reference of one page, canonicalised; ``base_dir`` is the page's directory when Papyrus rendered it."""
        if not url or url.startswith(_SKIP_PREFIXES):
            return url
        path, sep, tail = url.partition("#")
        if not sep:
            path, sep, tail = url.partition("?")
        if not path:
            return url
        absolute = path if path.startswith("/") else "/" + posixpath.normpath(posixpath.join(base_dir, path))
        if urls.is_non_page(absolute):
            return absolute + sep + tail
        folded = self.urls.folded_for(absolute)
        if folded is not None:
            return folded + sep + tail
        external = self.urls.external_for(absolute)
        if external is not None:
            return external + "/"
        href = self.urls.resolve(absolute)
        if href is not None:
            return urls.page_url(href) + sep + tail
        if absolute != "/":
            self.unresolved[path] = self.unresolved.get(path, 0) + 1
        return url

    def rewrite(self, html: str, *, base_dir: str) -> str:

        def one(match: re.Match[str]) -> str:
            resolved = self.absolutize(unescape(match.group("url")), base_dir=base_dir)
            return f'{match.group("attr")}="{escape(resolved, quote=True)}"'

        def many(match: re.Match[str]) -> str:
            out = []
            for candidate in unescape(match.group("value")).split(","):
                parts = candidate.strip().split(None, 1)
                if parts:
                    out.append(" ".join([self.absolutize(parts[0], base_dir=base_dir)] + parts[1:]))
            return f'srcset="{escape(", ".join(out), quote=True)}"'

        return _SRCSET_RE.sub(many, _REF_RE.sub(one, html))


def url_map(site) -> UrlMap:
    return site.memo("url_map", lambda: UrlMap(site))


# ------------------------------------------------------------------ redirects


def _placeholder_matcher(source: str):
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
            patterns.append(_placeholder_matcher(source))
            continue
        if source in exact or source in page_request_paths:
            continue
        if any(pattern.match(source) for pattern in patterns):
            continue
        exact[source] = target
    return exact


def page_images(site) -> dict[str, str]:
    """Papyrus href -> the share image of the page (the previous og:image URLs redirect to it)."""
    collections = support.collections(site)
    index = support.images(site)
    images: dict[str, str] = {}
    for node in collections.blog:
        images[f"articles/{node.slug}.html"] = _preview(node, index) or pictogram_og(node) or DEFAULT_COVER
    for node in collections.platform:
        images[f"platform/{node.slug}.html"] = _preview(node, index) or DEFAULT_COVER
    for href in _generated_hrefs(collections):  # every generated page but the home page and the tag pages has the default cover
        if href != "index.html" and not href.startswith("tags/"):
            images.setdefault(href, DEFAULT_COVER)
    return images


def pictogram_og(node) -> str | None:
    """og:image fallback for an item with ``pictogram:`` and no preview image (the PNGs are committed by bin/render-pictogram-pngs.py)."""
    import anthus_dom as dom

    name = dom.node_pictogram(node)
    if name and (support.SITE_ASSETS / "pictograms" / f"{name}.png").is_file():
        return f"/assets/site/pictograms/{name}.png"
    return None


def legacy_redirects(site) -> dict[str, str]:
    mapping = url_map(site)

    def build() -> dict[str, str]:
        ruleset = urls.legacy_rules(
            mapping.urls,
            og_images=json.loads(LEGACY_OG_IMAGES.read_text(encoding="utf-8")),
            page_images={href: image for href, image in page_images(site).items()},
            dist=None,
        )
        legacy_rules = json.loads(LEGACY_REDIRECT_RULES.read_text(encoding="utf-8"))
        generated_sources = {rule["source"] for rule in ruleset.rules}
        ordered = [*ruleset.rules, *(rule for rule in legacy_rules if rule["source"] not in generated_sources)]
        page_request_paths = {request_path for href in mapping.pages for request_path in request_paths_for_key(urls.page_output(href))}
        return effective_exact_redirects(ordered, page_request_paths)

    return site.memo("redirects", build)
