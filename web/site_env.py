"""Anth.us SEO, sitemap, robots.txt and the staging guard: Papyrus core does the work.

The settings are the ``site``, ``seo``, ``sitemap`` and ``feeds`` blocks of ``projection.json``. Core's
``resolve_environment`` decides production versus guarded (a guarded site emits ``noindex``, ``Disallow: /``
and its own origin), ``HeadBuilder`` writes the description, canonical, Open Graph, Twitter, JSON-LD, sitemap
link and robots tags, and ``sitemap_files`` / ``robots_text`` write the site files.

What is left here is the bridge from the Amplify staging build's variables (``SITE_ENV``, ``AWS_BRANCH``,
``AWS_APP_ID``) to core's ``PAPYRUS_SITE_PUBLIC_URL``, and the staging note in the footer.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

from papyrus_content.projection.standard.config import standard_settings_from_mapping
from papyrus_content.projection.standard.environment import PUBLIC_URL_ENV, SITE_ENV_ENV, SiteEnvironment, resolve_environment
from papyrus_content.projection.standard.head import HeadBuilder, PageHead
from papyrus_content.projection.standard.sitemap import INDEXED_KEY, INDEX_KEY, SitemapUrl, robots_text, sitemap_files

PRODUCTION_BRANCH = "main"
LOCAL_FALLBACK_ORIGIN = "http://localhost:8080"
SETTINGS_PATH = Path(os.environ.get("PAPYRUS_SITE_STATIC_DIR") or Path(__file__).resolve().parent) / "projection.json"
SETTINGS = standard_settings_from_mapping(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
PRODUCTION_ORIGIN = SETTINGS.identity.production_url.rstrip("/")

#: SITE_ENV values that are quietly "guarded" (no warning).
_KNOWN_GUARDED = frozenset({"", "guarded", "staging", "local", "development", "dev", "test"})

#: Text that identifies the footer staging note.
STAGING_NOTE_MARKER = "Staging preview of the Papyrus/Markus port of anth.us."
STAGING_NOTE_HTML = (
    '<div style="max-width:1120px;margin:1.25rem auto 0 auto;padding:0 1rem">'
    '<p style="margin:0;font-size:0.78rem;line-height:1.5;font-weight:300;'
    f'color:#cbbfef">{STAGING_NOTE_MARKER} '
    "Not the production site.</p></div>"
)


@dataclass(frozen=True)
class SiteEnv:
    environment: SiteEnvironment
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def production(self) -> bool:
        return self.environment.production

    @property
    def guarded(self) -> bool:
        return self.environment.guarded

    @property
    def origin(self) -> str:
        return self.environment.origin or LOCAL_FALLBACK_ORIGIN

    @property
    def mode(self) -> str:
        return "production" if self.production else "guarded"

    @property
    def analytics_enabled(self) -> bool:
        """True only in production. Passed to Papyrus's analytics capability."""
        return self.production


def resolve(environ: Mapping[str, str] | None = None) -> SiteEnv:
    """Production iff ``SITE_ENV=production`` on ``main`` (or no branch); everything else is guarded, fail-safe."""
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
                f"SITE_ENV=production but AWS_BRANCH={branch!r} (not {PRODUCTION_BRANCH!r}): building GUARDED "
                "(noindex, staging note). Fix the Amplify environment variable if this branch really is production."
            )
        else:
            production = True
    elif site_env not in _KNOWN_GUARDED:
        hint = " (the value is case-sensitive: exactly 'production')" if site_env.lower() == "production" else ""
        warnings.append(f"unknown SITE_ENV={site_env!r}: building GUARDED{hint}.")
    if production:
        if override and override != PRODUCTION_ORIGIN:
            warnings.append(f"ANTHUS_SITE_ORIGIN={override!r} ignored: production origin is fixed.")
        core = {}
    else:
        origin = f"https://{branch}.{app_id}.amplifyapp.com" if app_id and branch else override or LOCAL_FALLBACK_ORIGIN
        core = {PUBLIC_URL_ENV: origin, SITE_ENV_ENV: "guarded"}
    return SiteEnv(resolve_environment(SETTINGS, core), tuple(warnings))


#: Resolved once at import.
ENV = resolve()


def announce(env: SiteEnv = ENV) -> None:
    print(f"SITE_ENV resolved: mode={env.mode.upper()} origin={env.origin}")
    print(f"  analytics={'on' if env.analytics_enabled else 'off'}  noindex={'off' if env.production else 'on'}  staging-note={'off' if env.production else 'on'}")
    for warning in env.warnings:
        line = f"!!! WARNING: {warning}"
        print(line)
        print(line, file=sys.stderr)


def footer_note(env: SiteEnv = ENV) -> str:
    return "" if env.production else STAGING_NOTE_HTML


# ---------------------------------------------------------------- core's head, sitemap and robots


def head_tags(
    env: SiteEnv,
    *,
    title: str,
    path: str,
    description: str,
    image: str | None,
    article: dict | None = None,
    noindex: bool = False,
) -> str:
    """The description, canonical, Open Graph, Twitter, sitemap-link, robots and JSON-LD tags of one page."""
    page = PageHead(
        title=title,
        path=path,
        description=description,
        image=image,
        noindex=noindex,
        **(
            {}
            if article is None
            else dict(
                og_type="article",
                json_ld_type="Article",
                headline=article["headline"],
                published=article["published"],
                authors=tuple(article["authors"]),
            )
        ),
    )
    return HeadBuilder(SETTINGS, env.environment).build(page).lstrip("\n") + "\n"


def robots_txt(env: SiteEnv = ENV) -> str:
    return robots_text("index", env.environment, SETTINGS.robots_extra)


def sitemap_index_xml(env: SiteEnv = ENV) -> str:
    return sitemap_files("index", env.environment, [], lastmod=False)[INDEX_KEY].decode("utf-8")


def sitemap_0_xml(paths: Iterable[str], env: SiteEnv = ENV) -> str:
    urls = [SitemapUrl(path) for path in paths]
    return sitemap_files("index", env.environment, urls, lastmod=False)[INDEXED_KEY].decode("utf-8")
