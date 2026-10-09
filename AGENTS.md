# AGENTS.md — Anth.us-Papyrus

## Read this first: STAGING, not production

This repo builds a **review copy** of anth.us as a Papyrus/Markus static
reader site. It is not the live marketing site.

* **Production Anth.us** is `AnthusAI/Anth.us` (Gatsby 5) on Amplify app
  **`d1ffh6ny5rvtl`**. There is also an older `anthus-site` app,
  **`d23d9f23lg9obr`**. **Never pass either app id to a mutating AWS
  command.** The live marketing site runs on one of them; a stray change is a
  production outage.
* **This project's app id is recorded in [Deploy](#deploy) below.** Scope every
  write to that id, and use `aws amplify get-app --app-id <id>` to confirm you
  are on the right one before any mutation.
* **No custom domain. No DNS. Ever, from this repo.** Do not create or modify
  an Amplify domain association, a Route 53 hosted zone, or any record for
  `anth.us`. Review happens on the default `*.amplifyapp.com` hostname.
  Promotion to a domain is an explicit decision Ryan makes after reviewing the
  port — not an agent's call.
* The staging guards are **automatic and fail-safe**; see
  [Environment switch](#environment-switch-site_env). Never hand-edit a guard
  out to "go live" -- set `SITE_ENV=production` on the production build and
  the build removes them itself (and fails if any survive). Keep the staging
  notice in `README.md` and the staging banner in `web/css/anthus-theme.css`
  (`body.markus-site::before`).

## Read-only boundaries

| Path | Rule |
| --- | --- |
| `content/anthus-site-content/` | **Read only.** Same repo the live Gatsby site renders from. A commit here can break production Anth.us. The submodule is pinned to branch `content/markus-native-markup` (native Papyrus markup); **that branch must never be merged to `main`** while anth.us builds from `main`. Converting another branch is a run of `web/mdx_codemod.py` against a fresh clone, never against this checkout. |
| `../Papyrus` | **Read only** from this repo. Papyrus owns the renderer and `publications/anth_us/` (the `SiteBrand`). Changes there are Papyrus PRs on the `PPY` board. |
| `../Anth.us` | **Read only.** Reference for chrome, copy, and design tokens. |
| `../Pilobol.us` | **Read only.** The architectural template. |

If a renderer change is needed, do not fork or patch Papyrus from here. Fix it
in Papyrus and bump `PAPYRUS_PIN` in `amplify.yml`.

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
`anthus_pages` / `anthus_page_html` and rendered by calling
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
Papyrus pin in `amplify.yml` must include PR #83. It does (pinned at develop
`3fdd6fd`, which also has the shell hooks and fragment transforms this build
needs); keep it that way when bumping.

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

## Hosting

Platform **`WEB`**, its own Amplify app, template
`Papyrus/docs/hosting/amplify-static.yml.example`, runbook
`Papyrus/docs/site-hosting.md`. This is the `amplify-static` + `markus`
pairing. Papyrus's root `amplify.yml` is SSR/`WEB_COMPUTE` for p.apyr.us only —
**do not cargo-cult it here.**

### AWS preflight

Papyrus `AGENTS.md` tells agents to read `Papyrus/AGENTS.local.md` before any
AWS command. **That file does not exist on this machine** (2026-10-03) — do not
burn time looking for it. The equivalent facts, confirmed from
`Auritus/AGENTS.local.md` and `Chattic.us/AGENTS.local.md`:

* Anthus AWS account: **`335163751677`**, region **`us-east-1`**. It is the
  `legacy` account in the newer multi-account organization.
* Use **`AWS_PROFILE=legacy`** (SSO, `AdministratorAccess`, via the `Endymion`
  SSO session). Verify with `aws sts get-caller-identity --profile legacy`.
* The `anthus` and `default` profiles are legacy non-SSO root and are usually
  expired. Do **not** use them, and do not attempt `aws login` — that is
  interactive and only Ryan can complete it.
* The `Endymion` / `management` profiles are account `830955873957`, the
  **wrong** account. Nothing for this project goes there.
* `AdministratorAccess` means there is no guardrail but care. Orient with
  read-only calls (`list-apps`, `get-app`); scope every write to this
  project's app id.

### Deploy

Amplify app for this project:

| Field | Value |
| --- | --- |
| App name | `anthus-papyrus-staging` |
| App id | `d2hbn1ig6nqyhy` |
| Platform | `WEB` |
| Region | `us-east-1` |
| Branch | `staging` |
| Review URL | <https://staging.d2hbn1ig6nqyhy.amplifyapp.com> |
| Custom domain | **none, by design** |

The app is currently in **manual-deployment** mode; the procedure below is the
fallback and today's method. The intended path is Amplify's own git-connected
build (`amplify.yml`; branch env var `SITE_ENV=production` on `main`, none on
`staging`). Not GitHub Actions: this repository is private and private
repositories do not deploy through Actions. `bin/deploy-amplify.sh` automates
the manual steps (create-deployment, upload, start-deployment, poll).

#### Connecting the repository (owner, console)

The CLI cannot do this: `update-app --repository` needs a GitHub access token
(never create or store one), and Amplify rejects it while a manually deployed
branch exists ("delete all branches and try again"). The Amplify GitHub App
(`aws-amplify-us-east-1`) is already installed on AnthusAI for all repositories.

Deleting this app's `main` would drop the `anth.us`/`www.anth.us` domain
mappings, so prefer a cutover with a new app:

1. Amplify console -> Create new app -> GitHub -> authorize -> repository
   `AnthusAI/Anth.us-Papyrus`, branch `main`, auto-build on. Use the repo's
   `amplify.yml`. Add branch env var `SITE_ENV=production` on `main`.
2. Also add branch `staging` (no `SITE_ENV`) if wanted.
3. Apply the redirects to the new app (adapt the app id in
   `bin/apply_custom_rules.py`) and set the app-level headers.
4. Verify `bin/check-guards.py <new main url> --expect production`, then move
   the `anth.us` domain from `d2hbn1ig6nqyhy` to the new app.

Alternative: delete branches `main` and `staging` from `d2hbn1ig6nqyhy`, then
Hosting -> Connect repository on that app (accepts downtime on anth.us).

```bash
export AWS_PROFILE=legacy AWS_REGION=us-east-1
APP=d2hbn1ig6nqyhy          # never d1ffh6ny5rvtl, never d23d9f23lg9obr
aws amplify get-app --app-id "$APP" --query 'app.name'   # confirm first

PAPYRUS_ROOT=/Users/home/Projects/Papyrus python3 web/build_via_papyrus.py
( cd web/dist-papyrus && zip -qr ../../dist.zip . )

read -r JOB URL <<<"$(aws amplify create-deployment --app-id "$APP" \
  --branch-name staging --query '[jobId,zipUploadUrl]' --output text)"
curl -s -H 'Content-Type: application/zip' --upload-file dist.zip "$URL"
aws amplify start-deployment --app-id "$APP" --branch-name staging --job-id "$JOB"
aws amplify get-job --app-id "$APP" --branch-name staging --job-id "$JOB" \
  --query 'job.summary.status'
```

### Deploy step two: the redirect rules

The legacy-URL 301s are Amplify `customRules` — **app configuration, not part
of the artifact**. Deploying the zip does not update them, so a build that
changes the redirect map needs a second step:

```bash
AWS_PROFILE=legacy python3 bin/apply_custom_rules.py          # dry run, prints the diff
AWS_PROFILE=legacy python3 bin/apply_custom_rules.py --apply
```

The rules themselves are generated by the build into `web/custom-rules.json`
from the discovered corpus, so they cannot drift from the content; see
`web/anthus_urls.py`. That script refuses to run against anything but
`d2hbn1ig6nqyhy`/`anthus-papyrus-staging`.

Two things to know about Amplify's rule semantics, both measured rather than
assumed:

* A `301` rule is matched **before the filesystem**, so a rule whose source
  equals a canonical URL would make that page redirect instead of render.
  `anthus_urls._assert_no_shadowed_pages` fails the build on that.
* Trailing slashes are **not** normalized for matching. Sources are written
  with the trailing slash, because that is the shape production publishes; a
  request without it is first 301'd to add the slash, then matches, so the bare
  form resolves in two hops rather than needing a second rule per article.

### Manual deployment caveat: customHttp.yml does not apply

`customHttp.yml` is only read by Amplify during a **repo-connected CI build**.
A manual deployment ships only the artifact, so the file is never seen.
`customHttp.yml` is **app-wide** (every branch of the connected app), so it
carries **only cache headers and never `X-Robots-Tag`**: a noindex header there
would ship on `main` (production) too.

Staging is guarded by the per-page `noindex` meta and `robots.txt` only. There
is **no `X-Robots-Tag` header and no basic auth** on staging (decision recorded
on PPY-f1f0a8).

**Before `main` goes live:** the staging app currently carries an app-level
`X-Robots-Tag: noindex, nofollow` custom header (set earlier with
`aws amplify update-app --custom-headers`). The app is shared by both branches,
so that header would apply to production too. **It must be removed from the app
(console or CLI) before `main` is served on anth.us.**
`bin/check-guards.py --expect production` fails if the header is present.

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
python3 bin/check-guards.py https://staging.d2hbn1ig6nqyhy.amplifyapp.com --expect guarded
python3 bin/check-guards.py https://<production-host> --expect production
```

Guarded expects the noindex meta and staging note, with no `X-Robots-Tag`
requirement; production expects no noindex and **no** `X-Robots-Tag` header.
Exits non-zero on any mismatch. `--no-sitemap` skips the sitemap checks
for a host still serving a pre-sitemap-index build.

**Topology (decided, PPY-f1f0a8):** ONE Amplify app, `d2hbn1ig6nqyhy`, two
branches. `main` is production: branch environment variable
`SITE_ENV=production`, and the `anth.us` domain is attached at cutover.
`staging` is guarded (no `SITE_ENV`). Ryan connects the repository in the
Amplify console (Hosting -> Connect repository, `AnthusAI/Anth.us-Papyrus`) and
adds the branch variable; agents do not wire the repo, the domain or DNS. Run
`bin/check-guards.py --expect production` against the `main` branch URL before
attaching the domain, and remove the app-level `X-Robots-Tag` header first (see
above).

### The 404 rule (real 404s)

The catch-all must be `/<*>` -> `/404.html` with status **`404-200`**, last
after the 301s. Despite its name, Amplify answers that with the custom
`404.html` body at the requested URL and HTTP **404**, no redirect. Measured
2026-10-03 on the staging app:

| catch-all | missing page |
|---|---|
| status `404` | 302 -> `/404.html` (200): crawlers see a live page |
| none | 404 with an empty body (no custom page) |
| status `404-200` | 404 with the custom page body (correct) |

`bin/check-404.py <base-url>` verifies this. Note `/missing.html` or
`/missing` without a slash first take Amplify's own 301 to `/missing/`, then 404.

### Canonical URLs

The origin comes from the [environment switch](#environment-switch-site_env):
production is always `https://anth.us`; guarded builds derive it from
`AWS_APP_ID`/`AWS_BRANCH` (injected by Amplify CI). A **local** build has
neither, so it falls back to `http://localhost:8080`, which would ship in
`<link rel="canonical">` and `og:url`. When deploying manually to staging,
build with:

```bash
ANTHUS_SITE_ORIGIN=https://staging.d2hbn1ig6nqyhy.amplifyapp.com \
  PAPYRUS_ROOT=/Users/home/Projects/Papyrus python3 web/build_via_papyrus.py
```

(Do **not** set `SITE_ENV=production` for a manual staging build.)

`amplify.yml` is committed and correct, so connecting the repository in the
console (Amplify -> this app -> Hosting -> Connect repository, pick
`AnthusAI/Anth.us-Papyrus`, branch `staging`) switches it to CI builds with no
code change. That is a one-click step for a human.

When connecting the repo, note that `amplify.yml`'s `preBuild` runs
`git submodule update --init --recursive` — Amplify's default clone is shallow
and skips submodules, and without that step the build has no content at all.

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
* **`web/css/anthus-theme.css` is generated** (`bin/build-theme-css.py`); do not
  edit it by hand. Papyrus copies it to `dist/css/site-theme.css`.
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
  (`gatsby_parity`, AVIF up to 4096px), which is slow. `amplify.yml` already
  lists `web/.image-cache/**/*` under `cache.paths`; once the repo is connected
  in the console, confirm Amplify's build cache is on, or every CI build is cold.
* **Pillow must be >=11.3** (it bundles libavif); `amplify.yml` pins
  `Pillow>=11.3,<12`. Check locally with
  `python3 -c "from PIL import features; print(features.check('avif'))"`.
* **Main images start at `opacity:0`** (gatsby-plugin-image's behaviour).
  `_render_body` appends Papyrus's `FADE_IN_SCRIPT` to every page that has a
  `data-main-image`; without it the images stay invisible.
