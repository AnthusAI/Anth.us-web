# Anth.us-Papyrus

> ## ⚠️ THIS IS A STAGING SITE
>
> This repository builds a **review copy** of [anth.us](https://anth.us),
> rebuilt as a [Papyrus](https://github.com/AnthusAI/Papyrus)/Markus static
> reader site. It is **not** the production website.
>
> * Production Anth.us is still the Gatsby site in `AnthusAI/Anth.us`,
>   served by a **different** Amplify app (`d1ffh6ny5rvtl`).
> * This project has its **own** Amplify app
>   (`anthus-papyrus-staging` / `d2hbn1ig6nqyhy`) and is reviewed only on its
>   default hostname: <https://staging.d2hbn1ig6nqyhy.amplifyapp.com>
> * **No custom domain is attached, and none should be.** Do not point
>   `anth.us`, `www.anth.us`, or any subdomain at this app. Do not create or
>   modify Route 53 records. Domain cutover is a separate decision Ryan makes
>   after reviewing the port.
> * Every page ships `<meta name="robots" content="noindex, nofollow">`,
>   `robots.txt` is `Disallow: /`, and `customHttp.yml` sets
>   `X-Robots-Tag: noindex`. A full second copy of the marketing site must not
>   enter a search index.

The point of the project is dogfooding: Anthus publishes with Papyrus, so the
Anthus website should be *rendered by* Papyrus rather than by a bespoke
pipeline. Architecturally this is the same shape as
[Pilobol.us](https://github.com/AnthusAI/Pilobol.us) — a content pod plus a
thin publication-specific build that supplies identity and lets Papyrus's
`markus_renderer` do the rendering.

## Layout

```text
amplify.yml                     Amplify Hosting spec, platform WEB (static Markus pod)
customHttp.yml                  Cache + noindex headers
bin/dev-server.py               Local preview server for web/dist-papyrus
content/anthus-site-content/    git submodule: AnthusAI/anthus-site-content (READ ONLY)
web/
  build_via_papyrus.py          The build. Chrome, link rewriting, social meta, redirects
  anthus_content.py             Discovery, classification, image index, staging
  anthus_mdx.py                 MDX/JSX/raw-HTML -> Markus-safe Markdown
  anthus_pages.py               Markus equivalents of the bespoke pages and templates
  css/anthus-theme.css          Anthus brand theme over Papyrus's vendored Markus CSS
  assets/site/                  Site-chrome imagery (committed; see note below)
  assets/site-nav.js            Masthead nav collapse (progressive enhancement)
  staging/                      GENERATED Markdown tree (gitignored)
  dist-papyrus/                 GENERATED site (gitignored)
  BUILD-NOTES.md                Build details and troubleshooting
```

### One source of truth for content

The MDX, images, and diagrams are **not** copied into this repo. They are the
same `AnthusAI/anthus-site-content` repository the live Gatsby site mounts at
`Anth.us/src/site-content`, so both sites can render the same content in
parallel during the port. The submodule here is read-only: a stray commit to
it would hit production Anth.us.

```bash
git submodule update --init --recursive
```

Drafts under `Anth.us/src/drafts` are *not* in that repository, so this port
cannot and does not publish them.

### Why `web/assets/site/` is committed

Hero and capability imagery lives in the **Anth.us** repo (`src/images`,
`static/`), not in the content submodule, and the Amplify build has no access
to a sibling checkout. Those files are vendored here, downscaled to 1600 px
(the originals are 16–23 MB PNGs that Gatsby's sharp pipeline used to shrink).
They are interim stand-ins; see the parity notes below.

## Build

```bash
PAPYRUS_ROOT=/path/to/Papyrus python3 web/build_via_papyrus.py
python3 bin/dev-server.py --port 8080
```

Requires the `markus` CLI at the pinned version and `Pillow`, `PyYAML`:

```bash
pip install "git+https://github.com/AnthusAI/Markus@v0.5.1" "Pillow>=10,<12" "PyYAML>=6"
```

Output is `web/dist-papyrus/`. `PAPYRUS_ROOT` defaults to `../Papyrus`.

The build prints a **parity accounting** report at the end — how many images,
citations, tables and `<mark>` spans were converted, and what was dropped. Read
it. It is the honest record of what this port does not yet reproduce.

## Routing

`/articles/` is the canonical namespace, and URLs are **directory-style** to
match production anth.us. `web/anthus_urls.py` is the single configuration
point: `ANTHUS_URL_STYLE=html` switches the whole site back to
`/articles/<slug>.html` without touching anything else.

| Canonical here | Legacy Gatsby URLs that 301 onto it |
| --- | --- |
| `/` | — |
| `/articles/<slug>/` | `/blog/<slug>/`, `/<file-stem>/`, `/solutions/<File-Stem>/`, `/blog/<redirect_from>/` |
| `/articles/` | `/blog/`, `/blog/page/<n>/` |
| `/tags/<tag>/` | `/blog/<tag>/` |
| `/posts/`, `/posts/page-<n>/` | `/posts/<n>/`, `/posts/page/<n>/` |
| `/platform/`, `/platform/<slug>/` | already this shape on production |
| `/about/`, `/ai-solutions/`, `/ryan/` | already this shape on production |
| `/404.html` | kept literal; it is Amplify's error document |

The live Gatsby site publishes **four** shapes for the same corpus, not one.
`/blog/<slug>/` and `/blog/<tag>/` come from `gatsby-node.js` and share a
namespace — where a tag and an article slug collide, production serves the
article, and so does the redirect map. `/<file-stem>/` and
`/solutions/<File-Stem>/` come from `gatsby-plugin-page-creator`, which
`gatsby-config.mjs` points at the content directory: **every** MDX file also
gets a URL derived from its file path, with the authored capitalization and
spaces intact. All four are in production's sitemap, so all four are published.

Redirects are real **301**s, not meta-refresh HTML stubs: Amplify
`customRules`, generated into `web/custom-rules.json` by the build and pushed
with `bin/apply_custom_rules.py --apply`. They are app configuration rather
than a repo file, which is why that is a separate step from the deploy.

Every internal reference the build emits is normalized to the canonical URL in
one pass over the rendered HTML, so no internal link lands on a redirect. That
pass resolves *relative* references too, because the canonical shape moves each
page into its own directory; see the comment above `_absolutize`.

## Hosting

Platform **`WEB`**, its own Amplify app, built from
`Papyrus/docs/hosting/amplify-static.yml.example`. This is the
`amplify-static` + `markus` pairing from `Papyrus/docs/site-hosting.md`. It is
**not** the SSR/`WEB_COMPUTE` shape of Papyrus's own root `amplify.yml`; do not
cargo-cult that one here.

See [AGENTS.md](AGENTS.md) for the deploy runbook and the AWS profile to use.

## Known parity gaps

Tracked honestly rather than quietly. The first two are blocked on
Papyrus-side work already in flight.

| Gap | Status |
| --- | --- |
| **Responsive images.** Gatsby's `BlogImage`/`gatsby-plugin-sharp` emitted AVIF/WebP/fallback derivative sets with blurred placeholders. 235 images here render as a single `:::figure` `<img>`, downscaled to 1600 px at build time — no `srcset`, no `sizes`, no intrinsic dimensions (so layout shifts on load). | **Blocked** on the Papyrus responsive-image pipeline. Swap `anthus_mdx.render_image_directive()` when it lands. |
| **Inline citations.** `gatsby-citation-manager` rendered numbered inline markers with popovers plus an auto-numbered `<CitationsList>`. 201 citations here become plain `[n]` text plus a generated `## References` list; 25 `<CitationsList>` become that list. No popover — Markus has no inline-span directive. | **Blocked** on the Papyrus inline citation renderer. Swap `anthus_mdx.render_citation_marker()` / `render_references_block()`. |
| **`<mark>` brand highlight.** 204 uses. The pink gradient wash behind a phrase has no Markus target (no inline-span directive, no `==highlight==` plugin). Rendered as bold. | Needs a Markus inline-highlight feature. |
| **Hero overlay.** The homepage hero is an absolutely-positioned text overlay on a full-bleed image. Rendered as headline + subhead above the image. | Needs a Markus hero/overlay primitive, or accept the static form. |
| **`priority-plus` nav.** The production header measures itself and moves overflow into a dropdown. Replaced with a breakpoint hamburger (`web/assets/site-nav.js`). | Acceptable static equivalent. |
| **Inline SVG diagrams.** 2 dropped — Markus runs without `--allow-html` by design, so raw SVG cannot pass through. | Needs the diagrams re-authored as image files. |
| **`sqlbot-screen.gif`** (11 MB) not vendored; one `<img>` reference unresolved. | Deliberate: too large to commit without a derivative pipeline. |
| **Two `BlogImage` names** (`ai-agent-RAG-sequence-diagram.png`, `ai-agent-RAG-with-no-RAG.png`) have no matching file in the content repo. | Pre-existing content bug, not introduced here. |
| **HTML table spans.** `colspan`/`rowspan` have no GFM equivalent; those cells flatten into their first column. | Needs the tables re-authored, or a Markus table directive. |
| **Tag case collisions.** The corpus tags both `AI` and `ai`; Gatsby gives them separate pages, this build merges them (Papyrus only accepts lowercase collection slugs). | Intentional; arguably a content fix. |
| **Redirects are meta-refresh, not 301.** Amplify `customRules` would be better but are app configuration, not a repo file. | Set `customRules` on the app if the port is promoted. |
| **`anthus-footer`** is a React package (`github:AnthusAI/anthus-footer`) a static build cannot mount. Its canonical link set is reproduced as markup in `build_via_papyrus.py`. | Will drift if the package changes. |
| **No analytics.** The Gatsby site loads `gatsby-plugin-google-gtag` (`G-31SC26SDGX`). Deliberately omitted — a staging copy must not pollute production analytics. | Add on promotion, not before. |

## Related

* [`AnthusAI/Papyrus`](https://github.com/AnthusAI/Papyrus) — the renderer and
  `docs/site-hosting.md`
* [`AnthusAI/Markus`](https://github.com/AnthusAI/Markus) — the Markdown dialect
* [`AnthusAI/Pilobol.us`](https://github.com/AnthusAI/Pilobol.us) — the first
  Markus static reader pod, and this build's template
* [`AnthusAI/Anth.us`](https://github.com/AnthusAI/Anth.us) — the production
  Gatsby site this port replaces
* [`AnthusAI/anthus-site-content`](https://github.com/AnthusAI/anthus-site-content)
  — the shared content repo
