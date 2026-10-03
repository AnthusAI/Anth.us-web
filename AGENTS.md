# AGENTS.md — Anth.us-Papyrus

## Read this first: STAGING, not production

This repo builds a **review copy** of anth.us as a Papyrus/Markus static
reader site. It is not the live marketing site.

* **Production Anth.us** is `AnthusAI/Anth.us` (Gatsby 5) on Amplify app
  **`AMPLIFY_APP_ID`**. There is also an older `anthus-site` app,
  **`AMPLIFY_APP_ID`**. **Never pass either app id to a mutating AWS
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
| `content/anthus-site-content/` | **Read only.** Same repo the live Gatsby site renders from. A commit here can break production Anth.us. Content codemods are a separate, deliberate task in that repo. |
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

### The two pluggable seams

Papyrus work is in flight for the two constructs Markus cannot express. Both
are isolated behind single functions in `web/anthus_mdx.py` so the real
authoring syntax drops in without touching anything else:

* `render_image_directive()` — responsive images (235 uses)
* `render_citation_marker()` / `render_references_block()` — inline citations
  (201 + 25 uses)

**Do not pre-emptively emit a directive Markus does not register yet.**
`markus convert` fails the whole page on an unknown directive, so the build
would break until the Papyrus side lands. Swap these functions only once the
directive exists in the pinned Papyrus/Markus versions.

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

* Anthus AWS account: **`000000000000`**, region **`us-east-1`**. It is the
  `legacy` account in the newer multi-account organization.
* Use **`AWS_PROFILE=legacy`** (SSO, `AdministratorAccess`, via the `Endymion`
  SSO session). Verify with `aws sts get-caller-identity --profile legacy`.
* The `anthus` and `default` profiles are legacy non-SSO root and are usually
  expired. Do **not** use them, and do not attempt `aws login` — that is
  interactive and only Ryan can complete it.
* The `Endymion` / `management` profiles are account `000000000000`, the
  **wrong** account. Nothing for this project goes there.
* `AdministratorAccess` means there is no guardrail but care. Orient with
  read-only calls (`list-apps`, `get-app`); scope every write to this
  project's app id.

### Deploy

Amplify app for this project:

| Field | Value |
| --- | --- |
| App name | `anthus-papyrus-staging` |
| App id | `AMPLIFY_APP_ID` |
| Platform | `WEB` |
| Region | `us-east-1` |
| Branch | `staging` |
| Review URL | <https://staging.AMPLIFY_APP_ID.amplifyapp.com> |
| Custom domain | **none, by design** |

Repository connection is **not** wired through the CLI. Amplify Hosting's
supported GitHub integration is a GitHub App installation that requires the
console OAuth handshake, which a non-interactive session cannot perform, and
the legacy access-token path is deprecated for new apps. So this app deploys by
**manual deployment**: build locally, zip `web/dist-papyrus`, and upload.

```bash
export AWS_PROFILE=legacy AWS_REGION=us-east-1
APP=AMPLIFY_APP_ID          # never AMPLIFY_APP_ID, never AMPLIFY_APP_ID
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
  artifact and serve multi-megabyte PNGs at thumbnail size.
