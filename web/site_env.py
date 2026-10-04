"""Environment resolution and the staging/production guards (PPY-f1f0a8).

One switch, read once: ``SITE_ENV``.

* **production**  iff ``SITE_ENV == "production"`` AND (``AWS_BRANCH`` is unset
  OR ``AWS_BRANCH == "main"``).
* **guarded**     everything else: unset, local, any other branch, any
  unknown value. Fail-safe: a mistake yields an unindexed site, never an
  indexed staging copy.

Everything the guards control lives here so that ``build_via_papyrus.py`` and
``anthus_dom.py`` only carry one-line hooks:

* the origin used for canonical / og:url / sitemaps,
* the ``<meta name="robots">`` tag, the footer staging note,
* ``robots.txt`` and the sitemap files (``/sitemap-index.xml`` + ``/sitemap-0.xml``,
  the same URLs live anth.us publishes),
* the ``analytics_enabled`` decision (true only in production),
* :func:`assert_dist`, the end-of-build gate over every written HTML page.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable, Mapping

PRODUCTION_ORIGIN = "https://anth.us"
PRODUCTION_BRANCH = "main"
LOCAL_FALLBACK_ORIGIN = "http://localhost:8080"

#: SITE_ENV values that are quietly "guarded" (no warning).
_KNOWN_GUARDED = frozenset({"", "guarded", "staging", "local", "development", "dev", "test"})

NOINDEX_META = '<meta name="robots" content="noindex, nofollow">'
SITEMAP_LINK = '<link rel="sitemap" type="application/xml" href="/sitemap-index.xml">'

#: Text that identifies the footer staging note. Kept in sync with the markup below.
STAGING_NOTE_MARKER = "Staging preview of the Papyrus/Markus port of anth.us."
STAGING_NOTE_HTML = (
    '<div style="max-width:1120px;margin:1.25rem auto 0 auto;padding:0 1rem">'
    '<p style="margin:0;font-size:0.78rem;line-height:1.5;font-weight:300;'
    f'color:#cbbfef">{STAGING_NOTE_MARKER} '
    "Not the production site.</p></div>"
)

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
# The urlset namespaces gatsby-plugin-sitemap declares on live anth.us.
_URLSET_OPEN = (
    f'<urlset xmlns="{SITEMAP_NS}" '
    'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" '
    'xmlns:xhtml="http://www.w3.org/1999/xhtml" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" '
    'xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">'
)


class GuardError(RuntimeError):
    """A guard assertion failed; the build must not ship."""


@dataclass(frozen=True)
class SiteEnv:
    production: bool
    origin: str
    site_env: str = ""
    aws_branch: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def mode(self) -> str:
        return "production" if self.production else "guarded"

    @property
    def guarded(self) -> bool:
        return not self.production

    @property
    def analytics_enabled(self) -> bool:
        """True only in production. Passed to Papyrus's analytics capability."""
        return self.production


def resolve(environ: Mapping[str, str] | None = None) -> SiteEnv:
    env = os.environ if environ is None else environ
    site_env = env.get("SITE_ENV", "").strip()
    branch = env.get("AWS_BRANCH", "").strip()
    app_id = env.get("AWS_APP_ID", "").strip()
    override = env.get("ANTHUS_SITE_ORIGIN", "").strip().rstrip("/")
    warnings: list[str] = []

    production = False
    if site_env == "production":
        if branch and branch != PRODUCTION_BRANCH:
            warnings.append(
                f"SITE_ENV=production but AWS_BRANCH={branch!r} (not "
                f"{PRODUCTION_BRANCH!r}): building GUARDED (noindex, staging note). "
                "Fix the Amplify environment variable if this branch really is production."
            )
        else:
            production = True
    elif site_env not in _KNOWN_GUARDED:
        hint = " (the value is case-sensitive: exactly 'production')" if site_env.lower() == "production" else ""
        warnings.append(
            f"unknown SITE_ENV={site_env!r}: building GUARDED{hint}."
        )

    if production:
        origin = PRODUCTION_ORIGIN
        if override and override != PRODUCTION_ORIGIN:
            warnings.append(
                f"ANTHUS_SITE_ORIGIN={override!r} ignored: production origin is fixed."
            )
    else:
        if app_id and branch:
            origin = f"https://{branch}.{app_id}.amplifyapp.com"
        else:
            origin = override or LOCAL_FALLBACK_ORIGIN
    return SiteEnv(production, origin, site_env, branch, tuple(warnings))


#: Resolved once at import; ``anthus_dom`` needs it before ``main`` runs.
ENV = resolve()


def announce(env: SiteEnv = ENV) -> None:
    banner = f"SITE_ENV resolved: mode={env.mode.upper()} origin={env.origin}"
    print(banner)
    print(
        f"  analytics={'on' if env.analytics_enabled else 'off'}  "
        f"noindex={'off' if env.production else 'on'}  "
        f"staging-note={'off' if env.production else 'on'}"
    )
    for warning in env.warnings:
        line = f"!!! WARNING: {warning}"
        print(line)
        print(line, file=sys.stderr)


# ---------------------------------------------------------------- per-page markup


def footer_note(env: SiteEnv = ENV) -> str:
    return "" if env.production else STAGING_NOTE_HTML


def head_extras(env: SiteEnv = ENV) -> str:
    """Head tags appended after the social meta: noindex (guarded) + sitemap link."""
    return ("" if env.production else NOINDEX_META + "\n") + SITEMAP_LINK + "\n"


# ---------------------------------------------------------------- site files


def robots_txt(env: SiteEnv = ENV) -> str:
    if env.production:
        return f"User-agent: *\nAllow: /\nSitemap: {env.origin}/sitemap-index.xml\n"
    return "User-agent: *\nDisallow: /\n"


def sitemap_index_xml(env: SiteEnv = ENV) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<sitemapindex xmlns="{SITEMAP_NS}"><sitemap>'
        f"<loc>{escape(env.origin + '/sitemap-0.xml', quote=True)}</loc>"
        "</sitemap></sitemapindex>\n"
    )


def sitemap_0_xml(urls: Iterable[str]) -> str:
    body = "".join(f"<url><loc>{escape(u, quote=True)}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>{_URLSET_OPEN}{body}</urlset>\n'


def write_site_files(env: SiteEnv, out_dir: Path, page_urls: Iterable[str]) -> None:
    """robots.txt, /sitemap-index.xml, /sitemap-0.xml. Never /sitemap.xml."""
    (out_dir / "robots.txt").write_text(robots_txt(env), encoding="utf-8")
    (out_dir / "sitemap-index.xml").write_text(sitemap_index_xml(env), encoding="utf-8")
    urls = sorted(set(page_urls))
    (out_dir / "sitemap-0.xml").write_text(sitemap_0_xml(urls), encoding="utf-8")
    stale = out_dir / "sitemap.xml"
    if stale.exists():
        stale.unlink()


# ---------------------------------------------------------------- assertions

_META_ROBOTS_RE = re.compile(r"<meta\b[^>]*\bname=[\"']robots[\"'][^>]*>", re.I)
_CANONICAL_RE = re.compile(r"<link\b[^>]*\brel=[\"']canonical[\"'][^>]*>", re.I)
_OG_URL_RE = re.compile(r"<meta\b[^>]*\bproperty=[\"']og:url[\"'][^>]*>", re.I)
_HREF_RE = re.compile(r"\bhref=[\"']([^\"']*)[\"']", re.I)
_CONTENT_RE = re.compile(r"\bcontent=[\"']([^\"']*)[\"']", re.I)


def _on_origin(url: str, origin: str) -> bool:
    return url == origin or url.startswith(origin + "/")


def _check_page(env: SiteEnv, rel: str, text: str) -> list[str]:
    problems: list[str] = []
    robots = _META_ROBOTS_RE.findall(text)
    has_noindex = any("noindex" in tag.lower() for tag in robots)
    has_note = STAGING_NOTE_MARKER in text
    if env.production:
        if has_noindex:
            problems.append("noindex robots meta present in a production build")
        if has_note:
            problems.append("staging note present in a production build")
    else:
        if NOINDEX_META not in text:
            problems.append("noindex robots meta missing in a guarded build")
        if not has_note:
            problems.append("staging note missing in a guarded build")
        if "googletagmanager.com" in text:
            problems.append("analytics present in a guarded build")
    canon = _CANONICAL_RE.findall(text)
    if len(canon) != 1:
        problems.append(f"expected exactly 1 canonical link, found {len(canon)}")
    for tag in canon:
        m = _HREF_RE.search(tag)
        href = m.group(1) if m else ""
        if not _on_origin(href, env.origin):
            problems.append(f"canonical {href!r} is not on {env.origin}")
    for tag in _OG_URL_RE.findall(text):
        m = _CONTENT_RE.search(tag)
        url = m.group(1) if m else ""
        if not _on_origin(url, env.origin):
            problems.append(f"og:url {url!r} is not on {env.origin}")
    if SITEMAP_LINK not in text:
        problems.append("sitemap <link> missing from head")
    return problems


def _loc_to_file(loc: str, origin: str) -> str:
    path = loc[len(origin):]
    if path.endswith("/"):
        path += "index.html"
    return path.lstrip("/")


def _check_sitemaps(env: SiteEnv, out_dir: Path) -> list[str]:
    problems: list[str] = []
    if (out_dir / "sitemap.xml").exists():
        problems.append("/sitemap.xml must not be emitted (production serves sitemap-index.xml)")
    ns = {"s": SITEMAP_NS}
    try:
        index = ET.parse(out_dir / "sitemap-index.xml").getroot()
        zero = ET.parse(out_dir / "sitemap-0.xml").getroot()
    except (ET.ParseError, FileNotFoundError) as exc:
        return problems + [f"sitemap files missing or not valid XML: {exc}"]
    index_locs = [e.text or "" for e in index.findall("s:sitemap/s:loc", ns)]
    if index_locs != [f"{env.origin}/sitemap-0.xml"]:
        problems.append(f"sitemap-index.xml locs {index_locs} != [{env.origin}/sitemap-0.xml]")
    locs = [e.text or "" for e in zero.findall("s:url/s:loc", ns)]
    if not locs:
        problems.append("sitemap-0.xml lists no URLs")
    if len(locs) != len(set(locs)):
        problems.append("sitemap-0.xml has duplicate URLs")
    for loc in locs:
        if not _on_origin(loc, env.origin):
            problems.append(f"sitemap loc {loc} is not on {env.origin}")
            continue
        rel = _loc_to_file(loc, env.origin)
        if rel == "404.html":
            problems.append("sitemap lists the 404 page")
        elif not (out_dir / rel).is_file():
            problems.append(f"sitemap loc {loc} has no file {rel} in dist")
    return problems


def _check_robots(env: SiteEnv, out_dir: Path) -> list[str]:
    path = out_dir / "robots.txt"
    if not path.is_file():
        return ["robots.txt missing"]
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    if env.production:
        want = f"Sitemap: {env.origin}/sitemap-index.xml"
        out = []
        if "Allow: /" not in lines:
            out.append("production robots.txt lacks 'Allow: /'")
        if "Disallow: /" in lines:
            out.append("production robots.txt disallows /")
        if want not in lines:
            out.append(f"production robots.txt lacks {want!r}")
        return out
    return [] if "Disallow: /" in lines and "Allow: /" not in lines else [
        "guarded robots.txt must contain 'Disallow: /' and no 'Allow: /'"
    ]


def assert_dist(env: SiteEnv, out_dir: Path) -> int:
    """Gate over every written HTML page. Raises GuardError; returns page count."""
    problems: list[str] = []
    if env.production and env.origin != PRODUCTION_ORIGIN:
        problems.append(f"production origin is {env.origin}, expected {PRODUCTION_ORIGIN}")
    if env.guarded and env.origin == PRODUCTION_ORIGIN:
        problems.append(f"guarded build must not use the production origin {PRODUCTION_ORIGIN}")
    pages = sorted(out_dir.rglob("*.html"))
    if not pages:
        problems.append(f"no HTML pages found under {out_dir}")
    for page in pages:
        rel = page.relative_to(out_dir).as_posix()
        for problem in _check_page(env, rel, page.read_text(encoding="utf-8")):
            problems.append(f"{rel}: {problem}")
    problems += _check_robots(env, out_dir)
    problems += _check_sitemaps(env, out_dir)
    if problems:
        shown = "\n  ".join(problems[:40])
        more = f"\n  ... and {len(problems) - 40} more" if len(problems) > 40 else ""
        raise GuardError(
            f"{env.mode.upper()} guard assertions FAILED ({len(problems)} problem(s)); "
            f"refusing to ship:\n  {shown}{more}"
        )
    return len(pages)
