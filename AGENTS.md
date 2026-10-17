> **Production ownership verified 2026-10-17:** use this repository’s `main`
> for current anth.us website changes. The GitHub default `develop` branch
> contains older staging-era instructions; those are superseded by this notice.
> Public delivery is S3 projection via CloudFront `DISTRIBUTION_ID`.
> Merge-driven CMS/backend deployment: Amplify `AMPLIFY_APP_ID` (`anth-us-cms`),
> AWS profile `papyrus-production`, account `000000000000`, region `us-east-1`.
> `AnthusAI/Anth.us` (Gatsby) is superseded. Never send website fixes there.
> Do not promote unrelated historical develop changes as part of a website fix.
> Use AWS CLI/API only; no AWS console browser.
>
> **Engagement intake is pending upstream approval.** `web/inquiry-config.json`
> ships disabled, retaining the Google Form. Once Prospectus real-contact intake
> is approved, a scoped PR must supply its HTTPS endpoint, approved notice text
> and notice version together. This file is bundled with `web/` into the S3
> projector Lambda; `GATSBY_PROSPECTUS_INTAKE_URL` and Next build variables do
> not configure that runtime. No Prospectus settings, privacy, retention or grants
> are activated by this work. Track kanbus-e28f and kanbus-0d24 in the historical
> Gatsby site-operations board until the intake handoff is complete.

# AGENTS.md — Anth.us-Papyrus

## Read this first: how anth.us is served now

This repo is the source of the live **anth.us** site. Since 2026-10-13
(01:20:19 UTC) `anth.us` and `www.anth.us` are served from an **S3 projection**:
the pages are static files in a versioned S3 site bucket, behind our own
CloudFront distribution (edge stack `papyrus-edge-anth-us`, distribution
`DISTRIBUTION_ID`, in the papyrus-production AWS account). There is no
Amplify reader app in the publish path. Editors save in the newsroom (the
CMS Amplify app) and the page is live within seconds; see `S3 projection`
below and `Papyrus/docs/site-hosting.md`.

* **The old Gatsby site** `AnthusAI/Anth.us` and its Amplify apps
  (`AMPLIFY_APP_ID`, `AMPLIFY_APP_ID`) are not part of this repo. **Never
  pass those app ids to a mutating AWS command.**
* **The retired Amplify reader** `d15dpu9buefmq0` (production account) is kept,
  untouched, only as the rollback origin until it is deleted by Ryan. Do not
  build, deploy to or edit it. The legacy-account app `AMPLIFY_APP_ID`
  (`anthus-papyrus-staging`) no longer serves anth.us.
* **Domains and DNS** are owned by the edge stack (aliases, ACM certificate)
  and Route 53. Never create or change an Amplify domain association, a hosted
  zone or a record from this repo. A change to the edge is a CloudFormation
  change set that Ryan approves.
* **Guarded (staging-style) builds** still exist for local and review builds:
  see [Environment switch](#environment-switch-site_env). A guarded build ships
  `noindex`; never hand-edit a guard out to "go live". The projection is built
  with `SITE_ENV=production` semantics and the build fails if any guard
  survives.

## Read-only boundaries

| Path | Rule |
| --- | --- |
| `content/anthus-site-content/` | **Read only.** Same repo the live Gatsby site renders from. A commit here can break production Anth.us. The submodule is pinned to branch `content/markus-native-markup` (native Papyrus markup); **that branch must never be merged to `main`** while anth.us builds from `main`. Converting another branch is a run of `web/mdx_codemod.py` against a fresh clone, never against this checkout. |
| `../Papyrus` | **Read only** from this repo. Papyrus owns the renderer and `publications/anth_us/` (the `SiteBrand`). Changes there are Papyrus PRs on the `PPY` board. |
| `../Anth.us` | **Read only.** Reference for chrome, copy, and design tokens. |
| `../Pilobol.us` | **Read only.** The architectural template. |

If a renderer change is needed, do not fork or patch Papyrus from here. Fix it
in Papyrus and bump the `@anthusai/papyrus` version (`package.json`, `infra/site.json`).

## Git workflow

GitFlow. `main` is the release branch, `develop` is integration. Implementation
lands on `develop` via pull request from a `feature/` branch. Never force-push.
Never commit `web/staging/` or `web/dist-papyrus/` — both are generated and
gitignored.

## Build

```bash
git submodule update --init --recursive
pip install "git+https://github.com/AnthusAI/Markus@v0.5.1" "Pillow>=10,<12" "PyYAML>=6"
PAPYRUS_ROOT=/path/to/Papyrus python3 web/build_via_papyrus.py
python3 bin/dev-server.py --port 8080
```

On this machine Papyrus is at `/Users/home/Projects/Papyrus`. Papyrus's own
skills reference `/Users/ryan/Projects/Papyrus/...` — that path is stale;
translate, do not follow literally.

The build ends with a **parity accounting** report. Treat a growth in the
"dropped/approximated" counts as a regression and explain it.

### Architecture, in one paragraph

The front end is **the production Anth.us stylesheet and DOM**, not Markus's
design language (see `web/DESIGN-PARITY.md`). `anthus_content.discover()` reads
the MDX submodule and classifies nodes the way `Anth.us/gatsby-node.js` does.
Article and platform-product **bodies** go `anthus_mdx.normalize_body()` ->
`web/staging/*.md` -> Papyrus `build_markus_site(transform=ANTHUS_TRANSFORM,
vendor_css=False, ...)`. `markus convert` runs **without** `--allow-html` (a
Papyrus security invariant), so HTML the build itself generates -- the
production `.heading` block, `<mark>`, inline `<svg>`, JSX diagram trees,
colspan tables -- crosses it as Papyrus sentinels (`inline_sentinel`,
`block_sentinel`) and is re-emitted by `FragmentTransform`. Every other page
(home, listings, posts, tags, platform index, about, ai-solutions, ryan, 404,
engage, reading, research, decision-models) is **generated HTML** from
`anthus_pages` (arcade design language, see `web/DESIGN.md`) and rendered by calling
`markus_shell.render_page` directly, bypassing Markus. The page envelope is
`SiteChrome` hooks (`render_masthead`, `render_body`, `head_html`,
`stylesheets`, `asset_root`), with no monkeypatching. A post-pass over
`result.pages` (`finish_pages`) rewrites links, injects social meta and the
`noindex` guard, and gates on `markus-`/`papyrus-` classes before
`relocate_pages` moves files to canonical directory URLs.

### Images and citations: Papyrus content markup

Both constructs Markus cannot express are now Papyrus capabilities, opted into
in `build_via_papyrus.py` via `build_markus_site(images=IMAGES,
citations=CITATIONS)`. The authoring contract is Papyrus
`docs/markus-content-markup.md`; read it before changing either.

* `::image{src= layout= alt=}` — responsive images, 232 uses. Emitted by
  `anthus_mdx.render_image_directive()`.
* `[@key]` + a front-matter `citations:` block of CSL-JSON + `::citations{}` —
  201 markers over 197 entries, 25 bibliographies. Emitted by
  `render_citation_marker()` / `render_citations_directive()`, with the block
  re-emitted by `staged_markdown()`.
* `:::figure{}` — `render_static_figure()`, for the three site-chrome images
  that are vendored in **this** repo and so have no path under the pipeline's
  source root (which is the content submodule). Not responsive, by design.

`markus convert` fails a whole page on an unregistered directive, so the
Papyrus version this site depends on must include PR #83 (it does, along with the
shell hooks and fragment transforms this build needs); keep it that way when bumping.

The content is authored in this markup directly, so the MDX conversion in
`anthus_mdx` is a pass-through for the pinned content branch. It is kept
working — and `mdx_codemod` is shared by both paths — because the content repo
has two dozen un-migrated feature branches. Verified by building the submodule
at `main` and at `content/markus-native-markup` and diffing
`web/dist-papyrus`: byte-identical HTML.

The build raises if a `<BlogImage>`/`<Citation>`/`<CitationsList>` survives
into `web/staging/` (`audit_staging`). Leave that check in: without it a
leftover component would be escaped into visible angle brackets rather than
failing anything.

## S3 projection (PPY-f1df00)

The CMS backend (`papyrus.config.ts`, `backend.publication`) projects published content into an S3 site
bucket served by CloudFront: `web/projector.py` renders pages from the stored items, `web/projection.json`
sets the image renditions made at upload (`assets/responsive/**`, the 1600 px copies under `assets/content/**`).
The whole `web/` directory is bundled into the content-actions function as `site_static/`.

* `web/site-state.json` (committed) holds the dimensions of every image; rewrite it with
  `bin/make_site_state.py EXPORT CONTENT_ROOT web/site-state.json` when the set of images changes.
* `web/legacy-redirect-rules.json` is the redirect list the previous host (Amplify) served, frozen. The exact
  rules become key-value store entries; the pattern rules and the static-hosting behaviour (trailing slash,
  `.html`, the 404 page) live in `infra/edge/viewer-request.js`, the header rewriting in
  `infra/edge/viewer-response.js`. Both are tested with `node --test tests/edge/*.test.mjs`.
* Parity gate: `bin/project_export_locally.py EXPORT OUT` writes what `papyrus ops content project --all`
  writes; `tests/test_projector_incremental.py` (with `ANTHUS_PROJECTOR_EXPORT` and
  `ANTHUS_PROJECTOR_REFERENCE`) compares it byte for byte with a reference build.

## Hosting

Production is the S3 projection described above. Facts for agents:

* **Backend and deploys.** The CMS app builds from `main` (Amplify app
  `<siteId>-cms`, template `Papyrus/infra/amplify-app-shell`, config in
  `infra/site.json` and `papyrus.config.ts`). Merging to `main` is the deploy:
  the branch builds automatically, the backend deploy bundles `web/` into the
  `content-actions` Lambda, and `publication.reprojectOnDeploy: true` makes the
  deploy render every page inside AWS (`deploy-render` task, synchronous) and
  run a dry-run drift check. A render that fails fails the build; drift (orphan
  or stale pages) is reported in the Lambda log and the `Papyrus/Projection`
  `DeployRenderDrift` alarm, and nothing is deleted. Nobody runs `project --all`
  or a header script by hand (`Papyrus/docs/site-hosting.md`, "Merge is
  deploy").
* **Redirects, 404 and headers** live at the edge, not in Amplify app config:
  the exact redirects are CloudFront key-value-store entries written by
  `project --all`; the pattern rules, the `/x/` and `.html` behaviour and the
  404 page are in `infra/edge/viewer-request.js`; header rewriting is in
  `infra/edge/viewer-response.js`. Test with `node --test tests/edge/*.test.mjs`.
  The edge template is `infra/edge/anth-us-s3.template.yaml`
  (`bin/render_edge_template.py`).
* **Missing pages** return HTTP 404 with the `404.html` body (CloudFront maps S3
  403 and 404 to `/404.html` with status 404). The page writer stores
  `404.html` as `text/html` with no `Cache-Control`, so no follow-up step is
  needed. `bin/check-404.py <base-url>` verifies it. A path without a trailing slash or ending in `.html` first gets
  a 301 to the directory-style URL.
* **Rollback.** Content: restore the previous item version in the newsroom and
  save. Site code: revert the PR on `main` (the deploy re-renders the site). Edge:
  update the edge stack with the previous template.
* `customHttp.yml` and `bin/deploy-amplify.sh`, `bin/apply_custom_rules.py` are
  from the Amplify reader and do not affect the live site.

### Environment switch (`SITE_ENV`)

`web/site_env.py` reads `SITE_ENV` once (hooks in `build_via_papyrus.py` and
`anthus_dom.py` only call into it). The build prints the resolved mode and
origin first.

| Condition | Mode |
| --- | --- |
| `SITE_ENV=production` and `AWS_BRANCH` unset or `main` | **production** |
| `SITE_ENV=production`, `AWS_BRANCH` is another branch | guarded + loud warning |
| `SITE_ENV` unset / `staging` / `local` / ... | guarded |
| any other `SITE_ENV` value (typos, `Production`) | guarded + warning |

| | guarded (default) | production |
| --- | --- | --- |
| origin (canonical, og:url, sitemaps) | `https://<AWS_BRANCH>.<AWS_APP_ID>.amplifyapp.com`, else `ANTHUS_SITE_ORIGIN`, else `http://localhost:8080` | `https://anth.us` (fixed) |
| `<meta name="robots" content="noindex, nofollow">` | every page | none |
| footer staging note | yes | no |
| `robots.txt` | `Disallow: /` | `Allow: /` + `Sitemap: https://anth.us/sitemap-index.xml` (matches live) |
| analytics (`analytics_enabled`) | off | GA4 `G-31SC26SDGX` with owner opt-out, via `SiteChrome.ga_measurement_id` / `ga_owner_opt_out` (Papyrus #86) |

Both modes publish `/sitemap-index.xml` (a sitemapindex) and `/sitemap-0.xml`
(the urlset of canonical 200 pages, no 404) -- the same URLs live anth.us
serves -- plus `<link rel="sitemap" href="/sitemap-index.xml">` on every page.
There is no `/sitemap.xml`.

**Build-time assertions** (end of the build, over every written HTML page; the
build fails with a list of offenders): production -- origin is
`https://anth.us`, no robots noindex, no staging note, canonical/og:url on
`https://anth.us`; guarded -- every page has noindex and the staging note, no
analytics, canonical on the guarded origin; both -- `robots.txt` matches the
mode, sitemaps are valid XML and every `<loc>` is a file in the output.
Tests: `python3 tests/test_site_env.py`.

**Verify a deployed host** (read-only GETs):

```bash
python3 bin/check-guards.py https://<review-host> --expect guarded
python3 bin/check-guards.py https://anth.us --expect production
```

Guarded expects the noindex meta and staging note, with no `X-Robots-Tag`
requirement; production expects no noindex and **no** `X-Robots-Tag` header.
Exits non-zero on any mismatch. `--no-sitemap` skips the sitemap checks
for a host still serving a pre-sitemap-index build.

**Topology.** One CMS Amplify app for editing, one S3 site bucket and one
CloudFront distribution for the public site (see the top of this file). The
production build uses `SITE_ENV=production`; `check-guards.py --expect
production` is the check for a deployed host. The retired reader app's two
branches (`main`, `staging`) no longer matter.

### Canonical URLs

The origin comes from the [environment switch](#environment-switch-site_env):
production is always `https://anth.us`; guarded builds derive it from
`AWS_APP_ID`/`AWS_BRANCH` (injected by an Amplify CI build, which this site no longer runs; set `ANTHUS_SITE_ORIGIN` for review builds). A **local** build has
neither, so it falls back to `http://localhost:8080`, which would ship in
`<link rel="canonical">` and `og:url`. For a review build, build with:

```bash
ANTHUS_SITE_ORIGIN=https://<review-host> \
  PAPYRUS_ROOT=/Users/home/Projects/Papyrus python3 web/build_via_papyrus.py
```

(Do **not** set `SITE_ENV=production` for a review build.)

## Things that will bite you

* **Leaf vs container directives.** `:::metric{…}` is wrong — `metric` is a
  leaf, so it is `::metric{…}` with no closing fence. Writing three colons
  makes the parser see an unterminated container and the whole page fails to
  convert.
* **Front-matter `title` is kept for Papyrus's `<title>` only.** Markus's own
  `<header>` is removed by `FragmentTransform(strip_header=True)` and the
  production `.heading` (h1, date, authors, `.draft-overlay`) is prepended as a
  block sentinel by `anthus_content._article_header`. A body `# Heading` would
  give the page two `<h1>`s.
* **Image wrappers ride in the layout name.** `<div className="center-full-image">`
  / `<figure>` / floated `<div style=...>` around an `::image{}` is DOM the
  stylesheet targets, and `::image{}` has no wrapper attribute, so
  `anthus_mdx._convert_image_wrappers` encodes it as `layout="full@figure-cfi"`
  and `anthus_dom.anthus_image_wrap` decodes it. `anthus_layout_sizes` registers
  every combination.
* **The site stylesheet is hand-written.** `web/css/arcade.css` (the design
  system, `web/DESIGN.md`) and `web/css/arcade-pictograms.css` (pictogram
  sprites) are the source of truth: edit them directly. `web/site_css.py`
  concatenates them; the build stages the result and Papyrus copies it to
  `dist/css/site-theme.css`, and the projector ships the same bytes.
  `web/css/anthus-theme.css` (generated from the old Gatsby repo; its generator
  has been removed) is no longer shipped; do not edit it, and do not
  expect its hashed CSS-module classes to be styled by the new sheet.
* **Do not strip tag-shaped prose.** `<N>`, `<arm>`, `<QUERY>` appear in
  sentences as placeholders. `anthus_mdx` only strips names in
  `_KNOWN_HTML_TAGS`; everything else is left for Markus to escape, which is
  what the author meant the reader to see.
* **Only referenced images are staged.** The content repo holds ~313 MB of
  images, most unreferenced. Copying the tree wholesale would bloat the
  artifact and serve multi-megabyte PNGs at thumbnail size. Article images no
  longer go through that path at all — `ImagePipeline` reads them straight out
  of the submodule and writes its own renditions.
* **`upgrade_plain_images=False` is load-bearing.** `anthus_pages` emits
  listing thumbnails and chrome as plain Markdown images with site-ABSOLUTE
  hrefs, and `images.assert_safe_asset_src` rejects absolute paths by design.
  Turning the upgrade on fails the build on the homepage.
* **`web/.image-cache/` must stay outside `web/staging/` and
  `web/dist-papyrus/`.** The build wipes both. Without the cache every build
  re-encodes every source at every breakpoint in AVIF and WebP
  (`gatsby_parity`, AVIF up to 4096px), which is slow. The live site does not
  encode images in a build at all: renditions are made at upload by the
  `renditions` Lambda (`web/projection.json`); this cache matters only for local
  and parity builds.
* **Pillow must be >=11.3** (it bundles libavif; the Lambdas and local builds need it). Check locally with
  `python3 -c "from PIL import features; print(features.check('avif'))"`.
* **Main images start at `opacity:0`** (gatsby-plugin-image's behaviour).
  `_render_body` appends Papyrus's `FADE_IN_SCRIPT` to every page that has a
  `data-main-image`; without it the images stay invisible.
