# Anth.us-Papyrus

> ## ⚠️ THIS IS A STAGING SITE
>
> This repository builds a **review copy** of [anth.us](https://anth.us),
> rebuilt as a [Papyrus](https://github.com/AnthusAI/Papyrus)/Markus static
> reader site. It is **not** the production website.
>
> * Production Anth.us is still the Gatsby site in `AnthusAI/Anth.us`,
>   served by a **different** Amplify app (`AMPLIFY_APP_ID`).
> * This project has its **own** Amplify app
>   (`anthus-papyrus-staging` / `AMPLIFY_APP_ID`) and is reviewed only on its
>   default hostname: <https://staging.AMPLIFY_APP_ID.amplifyapp.com>
> * **No custom domain is attached, and none should be.** Do not point
>   `anth.us`, `www.anth.us`, or any subdomain at this app. Do not create or
>   modify Route 53 records. Domain cutover is a separate decision Ryan makes
>   after reviewing the port.
> * Every staging page ships `<meta name="robots" content="noindex, nofollow">`
>   and `robots.txt` is `Disallow: /` (see AGENTS.md, "Environment switch"). A full second copy of the marketing site must not
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
  mdx_codemod.py                Gatsby MDX -> Papyrus markup. Also the one-shot
                                content codemod CLI (see below)
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

### The submodule tracks a converted branch, not `main`

The submodule is pinned to `anthus-site-content` branch
**`content/markus-native-markup`**, which is `main` with the three Gatsby MDX
components rewritten as native Papyrus markup — `::image{}`, `[@key]` plus a
front-matter `citations:` block, and `::citations{}`. See
[Papyrus `docs/markus-content-markup.md`][markup] for the authoring contract.

That branch is **not** renderable by Gatsby's component set and must never be
merged to `main` while anth.us builds from it. The reader build still converts
Gatsby MDX on the fly (`anthus_mdx` + `mdx_codemod`), so pointing the submodule
at `main` or at any of the repo's un-migrated feature branches produces
byte-identical HTML — verified by diffing both builds.

To migrate another content branch:

```bash
git clone git@github.com:AnthusAI/anthus-site-content.git /tmp/content
cd /tmp/content && git checkout -b my-branch-markus origin/my-branch
python3 /path/to/Anth.us-Papyrus/web/mdx_codemod.py --check /tmp/content   # dry run
python3 /path/to/Anth.us-Papyrus/web/mdx_codemod.py /tmp/content
```

It refuses to run on `main`.

[markup]: https://github.com/AnthusAI/Papyrus/blob/develop/docs/markus-content-markup.md

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

It also needs a Papyrus that has the content-markup capabilities
(`ImagePipeline`, `CitationRendering`). Those landed in Papyrus PR #83; a
Papyrus without them fails every page with `Unknown directive 'image'`, which
is deliberate — see the note in `amplify.yml` about the pin.

Image renditions are cached in `web/.image-cache/` (gitignored), **outside**
both generated trees because the build wipes those. A cold build encodes ~230
sources at four widths in two formats and takes about five minutes; a warm one
is seconds. Put that directory on the CI cache path.

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

## Deployment

Target design: Amplify Hosting builds from git. Once the Amplify app
`AMPLIFY_APP_ID` is connected to `AnthusAI/Anth.us-Papyrus`, a push to `main`
or `staging` runs `amplify.yml` on AWS (no GitHub Actions; this repository is
private and private repositories do not deploy through Actions).

* `amplify.yml` initializes the content submodule, clones Papyrus at the pinned
  commit, installs the Python dependencies, runs `web/build_via_papyrus.py`,
  and publishes `web/dist-papyrus`.
* The branch decides the mode through Amplify **branch environment variables**:
  `main` has `SITE_ENV=production` (already set); `staging` has none (guarded).
* Redirects are app configuration, not part of the build: after changing
  `web/custom-rules.json`, run `bin/apply_custom_rules.py --apply`.

**Status: not yet connected.** The app is in manual-deployment mode, and
Amplify refuses to connect a repository while a manually deployed branch
exists ("delete all branches and try again"). Deleting `main` would drop the
`anth.us` and `www.anth.us` domain mappings, so this is a deliberate cutover
step for the owner, not something to do in passing. Console steps: see
[AGENTS.md](AGENTS.md) ("Connecting the repository").

### Fallback: manual deploy (current method)

```bash
export AWS_PROFILE=legacy AWS_REGION=us-east-1
PAPYRUS_ROOT=../Papyrus SITE_ENV=production python3 web/build_via_papyrus.py
AMPLIFY_APP_ID=AMPLIFY_APP_ID AMPLIFY_BRANCH=main bash bin/deploy-amplify.sh web/dist-papyrus
```

`bin/deploy-amplify.sh` does create-deployment, upload, start-deployment and
polls the job, failing on FAILED. Details in AGENTS.md ("Deploy").

## Hosting

Platform **`WEB`**, its own Amplify app, built from
`Papyrus/docs/hosting/amplify-static.yml.example`. This is the
`amplify-static` + `markus` pairing from `Papyrus/docs/site-hosting.md`. It is
**not** the SSR/`WEB_COMPUTE` shape of Papyrus's own root `amplify.yml`; do not
cargo-cult that one here.

See [AGENTS.md](AGENTS.md) for the deploy runbook and the AWS profile to use.

## Known parity gaps

Tracked honestly rather than quietly.

| Gap | Status |
| --- | --- |
| **Citation popovers.** `gatsby-citation-manager` wired each marker to a hover/click popover showing the formatted entry. The numbered marker, the link and the bibliography are all reproduced; the popover is not — it was runtime JavaScript. | Acceptable static equivalent. A reader can follow the link. |
| **Citation formatting is not citeproc.** `format_apa` in Papyrus is an APA-7-*shaped* hand-rolled formatter. It formats all 197 entries without error but is not byte-identical to `citation-js` + `@citation-js/plugin-csl`, which the Gatsby site ran in the browser. Nothing has diffed the two renderings. | `CitationRendering(formatters={"apa": …})` accepts a real processor if exact fidelity is wanted. |
| **PNG `<picture>` fallbacks dominate the artifact.** The pipeline always emits the source format as the `<img>` fallback, and most of this corpus is photographic AI art saved as PNG: 193 MB of PNG renditions against 27 MB of WebP for the same images. Widths are capped at 1366 (`sizes` tops out at 48rem) to hold that down. | A Papyrus-side improvement: let a publication choose a JPEG fallback for photographic sources. |
| **Listing thumbnails and site chrome are not responsive.** `anthus_pages` emits them as plain Markdown images with site-absolute hrefs, which the pipeline rejects by design, so `upgrade_plain_images` is off and they keep the old 1600-px downscale path. They are already sized for their slot. | Needs a second source root, or relative hrefs in the generated pages. |
| **`<mark>` brand highlight.** 204 uses. The pink gradient wash behind a phrase has no Markus target (no inline-span directive, no `==highlight==` plugin). Rendered as bold. | Needs a Markus inline-highlight feature. |
| **Hero overlay.** The homepage hero is an absolutely-positioned text overlay on a full-bleed image. Rendered as headline + subhead above the image. | Needs a Markus hero/overlay primitive, or accept the static form. |
| **`priority-plus` nav.** The production header measures itself and moves overflow into a dropdown. Replaced with a breakpoint hamburger (`web/assets/site-nav.js`). | Acceptable static equivalent. |
| **Inline SVG diagrams.** 2 dropped — Markus runs without `--allow-html` by design, so raw SVG cannot pass through. | Needs the diagrams re-authored as image files. |
| **`sqlbot-screen.gif`** (11 MB) not vendored; one `<img>` reference unresolved. | Deliberate: too large to commit without a derivative pipeline. |
| **Two RAG sequence diagrams** (`ai-agent-RAG-sequence-diagram.png`, `ai-agent-RAG-with-no-RAG.png`) have no matching file in the content repo; `how-ai-agents-know-things` renders "No image found for:" on the live site today. The codemod removed the two dead references rather than carry them over. | Pre-existing content bug. Fixed by restoring the two files and re-adding two `::image{}` lines. |
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
