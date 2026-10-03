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
* Keep the staging notice in `README.md`, the staging banner in
  `web/css/anthus-theme.css` (`body.markus-site::before`), the footer note in
  `build_via_papyrus.py`, and the `noindex` headers in `customHttp.yml`. They
  exist so nobody mistakes this for production. Do not quietly remove them.

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

`anthus_content.discover()` reads the MDX submodule and classifies nodes the
way `Anth.us/gatsby-node.js` does. `anthus_mdx.normalize_body()` rewrites MDX
imports, JSX components, and raw HTML into Markus-safe Markdown — necessary
because static Markus builds run `markus convert` **without** `--allow-html`
(a security invariant Papyrus enforces in
`markus_renderer/security.py`), so raw HTML would otherwise be escaped into
visible angle brackets. `anthus_pages` generates the bespoke pages and
listings. All of that lands in `web/staging/`. Then Papyrus's
`build_markus_site()` renders it with Anthus `SiteChrome`, and
`build_via_papyrus.py` adds standalone pages, link rewriting, social meta,
redirect stubs, `robots.txt` and `sitemap.xml`.

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

`markus convert` fails a whole page on an unregistered directive, so **the
Papyrus pin in `amplify.yml` must include PR #83 before this branch deploys.**
The pin committed on this branch does not. That is called out in `amplify.yml`
itself; do not deploy until it is bumped.

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

Repository connection is **not** wired through the CLI. Amplify Hosting's
supported GitHub integration is a GitHub App installation that requires the
console OAuth handshake, which a non-interactive session cannot perform, and
the legacy access-token path is deprecated for new apps. So this app deploys by
**manual deployment**: build locally, zip `web/dist-papyrus`, and upload.

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

### Manual deployment caveat: customHttp.yml does not apply

`customHttp.yml` is only read by Amplify during a **repo-connected CI build**.
A manual deployment ships only the artifact, so the file is never seen. The
same headers are therefore also set on the app itself
(`aws amplify update-app --custom-headers …`) and `X-Robots-Tag: noindex` is
verified live. If the repo is later connected, `customHttp.yml` takes over —
keep the two in sync, and keep `noindex` in both.

Each page also carries `<meta name="robots" content="noindex, nofollow">` and
`robots.txt` is `Disallow: /`, so indexing is blocked three independent ways.

### Known quirk: the 404 rule

The app's custom rule (`/<*>` -> `/404.html`, status `404`) is implemented by
Amplify as a 301 to `/404.html`, which then returns 200 — not a true 404
status. Acceptable for a staging review site; revisit before any promotion.

### Canonical URLs

`build_via_papyrus.py` derives `SITE_ORIGIN` from `AWS_APP_ID`/`AWS_BRANCH`,
which Amplify injects during a CI build. A **local** build has neither, so it
falls back to `http://localhost:8080` — which is what then ships in
`<link rel="canonical">` and `og:url`. When deploying manually, build with:

```bash
ANTHUS_SITE_ORIGIN=https://staging.d2hbn1ig6nqyhy.amplifyapp.com \
  PAPYRUS_ROOT=/Users/home/Projects/Papyrus python3 web/build_via_papyrus.py
```

`amplify.yml` is committed and correct, so connecting the repository in the
console (Amplify → this app → Hosting → Connect repository, pick
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
* **Front-matter `title` already emits the `<h1>`** and `description` emits
  the lede. A body `# Heading` on top of that gives the page two `<h1>`s.
* **Markus escapes the front-matter byline**, so Markdown links in
  `authors[].author` do not render there. The build emits its own byline
  paragraph instead.
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
  re-encodes ~230 sources at four widths in two formats, about five minutes.
* **Widths are capped at 1366 on purpose.** Every layout's `sizes` tops out at
  48rem, and the source format is always emitted as the `<picture>` fallback —
  this corpus is mostly photographic PNG, so the fallbacks are 193 MB against
  27 MB of WebP. Raising the cap grows the artifact fast.
