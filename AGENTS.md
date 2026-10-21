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
> **Engagement intake posts to Prospectus; the Google Form is retired.**
> `web/inquiry-config.json` is the only configuration (it is bundled with `web/`
> into the S3 projector Lambda; `GATSBY_PROSPECTUS_INTAKE_URL` and Next build
> variables do not configure that runtime). The engage form renders only when
> `endpoint` (the `EvaluationIntakeUrl` stack output, https), `notice_version`
> (exactly `contact-v1`), `privacy_notice` and `notice_approved: true` are all set;
> otherwise the page says the form is unavailable and shows `fallback_email` if
> set. Prospectus accepts `https://anth.us` and `https://www.anth.us` origins in
> real-contacts mode. Track kanbus-e28f and kanbus-0d24 in the historical Gatsby
> site-operations board; Prospectus tracks kanbus-47dc15 and kanbus-67ae2d.

# AGENTS.md — Anth.us-web

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
  see [Environment switch](#environment-switch). A guarded build ships
  `noindex`; never hand-edit a guard out to "go live". The live projection runs
  as production (the origin is `site.productionUrl`) and a guarded environment
  never loads analytics.

## Read-only boundaries

| Path | Rule |
| --- | --- |
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

There is no build. The CMS app's publish mutation projects the published items
into the S3 site bucket, and a merge to `main` re-projects every page inside AWS
(`deploy-render`). Locally:

```bash
PAPYRUS_ROOT=/path/to/Papyrus PAPYRUS_SITE_BUCKET=<site bucket> \
  python3 bin/project_export_locally.py EXPORT OUT --redirects-json R.json
python3 bin/dev-server.py OUT --port 8080
PYTHONPATH=$PAPYRUS_ROOT/src:$PAPYRUS_ROOT python3 -m pytest tests
```

On this machine Papyrus is at `/Users/home/Projects/Papyrus`. Papyrus's own
skills reference `/Users/ryan/Projects/Papyrus/...` — that path is stale;
translate, do not follow literally.

### Architecture, in one paragraph

The site is **Papyrus's standard Markus front end configured by
`web/projection.json`**, plus named hooks (`web/hooks.py`). The front end is
**the production Anth.us stylesheet and DOM**, not Markus's design language
(`web/css/site-theme.css`, `web/DESIGN.md`, `web/DESIGN-PARITY.md`). An article
or platform item goes through the `source` hook (the production `.heading`
block, the closing call to action, clean-up of editor leftovers), Markus, the
`item_transform` hook (Markus classes to the Anthus vocabulary, block
passthrough for the heading, `<svg>` and `<mark>`), and the page envelope of the
`page_body` hook (header, container, footer). The other pages are **page files**
(`web/pages/*.md`: Markus with `::raw` HTML and `::include{...}` for the parts
generated from content) or listing pages the hooks compose from Papyrus's view
of a collection. Collections (`articles`, `posts`, `reading`, `research`) are
**defined by tag** in `projection.json`; pagination is core's (featured 4, then
pages of 8). A last pass (`page_finish`) rewrites internal links to the
canonical URLs (`web/links.py`, `web/anthus_urls.py`). Redirects are the
`redirects` hook plus `redirects.patterns` in `projection.json`.

### Page files and includes

`web/pages/<id>.md` is the body of the page named in `projection.json`
`pages[].source` (`notFound.source` for the 404 page). It starts with
`::band{size="bare"}` and is a sequence of `::raw` ... `::endraw` regions (HTML
exactly as written; allowed only in page files, never in CMS items) and
`::include{kind=...}` lines. Includes that name content are the page's declared
dependencies, so publishing or editing an item rewrites exactly the pages whose
includes show it:

* `kind="listing"` with `collection=` or `sections= tags= allTags= notTags=`,
  `sort`, `ties`, `skip`, `count`, `card="text:code=0,grid"` (the `card` hook
  variants are in `web/cards.py`: `text`, `mini`, `line`, `chip`), `layout="bare"`
  and `tag="ul" class="..."` for the wrapper element.
* `kind="block" name=... depends=...` calls `site_blocks.render` (pictograms,
  the solution grids, further reading, the platform list, the engage form).
  `depends` names the sections the block reads.

Copy rules (DESIGN.md section 8) apply to the copy in these files. Anth.us
copy and design rules do not change with the machinery: the arcade redesign,
the four featured solutions (Cyclotron, Chatticus, Papyrus, Auritus, with the
Auritus logo), the Primus credibility section ("Built and run for years", "free
and open source"), the proof strip and claims honesty are pinned by tests.

### Images and citations

Images in article bodies are `::image{src= layout= alt=}`, citations `[@key]` +
a front-matter `citations:` block + `::citations{}`; the authoring contract is
Papyrus `docs/markus-content-markup.md`. The renditions are made at upload and
read by the projector (`images` in `projection.json`); the `image_pipeline` hook
only sets the wrapper (`anthus_dom.anthus_image_wrap`, gatsby-plugin-image's
DOM) and the layout sizes.

## S3 projection (PPY-f1df00)

The CMS backend (`papyrus.config.ts`, `backend.publication`) projects published content into an S3 site
bucket served by CloudFront: `web/projector.py` renders pages from the stored items, `web/projection.json`
sets the image renditions made at upload (`assets/responsive/**`, the 1600 px copies under `assets/content/**`).
The whole `web/` directory is bundled into the content-actions function as `site_static/`.

* The projector keeps no list of images: it reads the rendition records (`assets/responsive/**/*.meta.json`) of
  the site store through Papyrus's `RenditionCatalog`, so `PAPYRUS_SITE_BUCKET` must name the store.
* `web/legacy-redirect-rules.json` is the redirect list the previous host (Amplify) served, frozen. The exact
  rules become key-value store entries; the pattern rules are `redirects.patterns` in `web/projection.json`, the
  static-hosting behaviour (trailing slash, `.html`, the 404 page) is `urls.style: directory`; Papyrus compiles
  both into the viewer-request function (`papyrus-infra compile-edge-function --static-dir web`). The header
  rewriting is `infra/edge/viewer-response.js`. Both are tested with `node --test tests/edge/*.test.mjs`.
* Parity gate: `bin/project_export_locally.py EXPORT OUT` writes what `papyrus ops content project --all`
  writes; `tests/test_projector_incremental.py` proves that incremental projection after random publish, edit and
  unpublish equals a fresh `project --all` (on the fixture corpus, or on a real export with `ANTHUS_PROJECTOR_EXPORT`).
* **CMS staging preview.** The `staging` branch of the CMS app exports the drafts and projects them through the same
  standard projector (`cms.stagingPreview.buildCommand` in `infra/site.json`: `papyrus ops content project --all
  --from-dir content-export --static-dir web`, guarded). It reads image renditions from the site bucket, so the branch
  needs `PAPYRUS_SITE_BUCKET` and read access to that bucket; the build fails loudly without it.

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
  404 page are Papyrus's viewer-request function compiled from `web/projection.json`
  (no function of our own); header rewriting is in `infra/edge/viewer-response.js`.
  Test with `node --test tests/edge/*.test.mjs`.
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
* `customHttp.yml` is from the Amplify reader and does not affect the live site.

### Environment switch

Papyrus core owns the guard, the head tags, the sitemap and `robots.txt`
(`resolve_environment`, `HeadBuilder`, `sitemap_files`, `robots_text`; settings in
the `site`, `seo` and `sitemap` blocks of `web/projection.json`). The projector is
**production** when its origin (`PAPYRUS_SITE_PUBLIC_URL`, default `site.productionUrl`)
is `https://anth.us`; `PAPYRUS_SITE_ENV=guarded` (or `production`) overrides the
guess, and any other origin is guarded. The live Lambda sets neither, so it is production.

| | guarded | production |
| --- | --- | --- |
| origin (canonical, og:url, sitemaps) | `PAPYRUS_SITE_PUBLIC_URL` | `https://anth.us` |
| `<meta name="robots" content="noindex, nofollow">` | every page | none |
| footer staging note | yes | no |
| `robots.txt` | `Disallow: /` | `Allow: /` + `Sitemap: https://anth.us/sitemap-index.xml` |
| analytics | off | GA4 `G-31SC26SDGX` with owner opt-out (`chrome` in `projection.json`) |

Both modes publish `/sitemap-index.xml` (a sitemapindex) and `/sitemap-0.xml`
(the urlset of canonical 200 pages, no 404) -- the same URLs live anth.us
serves -- plus `<link rel="sitemap" href="/sitemap-index.xml">` on every page.
There is no `/sitemap.xml`.

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
CloudFront distribution for the public site (see the top of this file).

### Canonical URLs

The origin comes from the [environment switch](#environment-switch): production is always `https://anth.us`. A local or
review projection ships the origin you give it, so set `PAPYRUS_SITE_PUBLIC_URL=https://<review-host>` (and
`PAPYRUS_SITE_ENV=guarded`) when projecting for review; otherwise it is production and its canonical links say `anth.us`.

## Things that will bite you

* **Leaf vs container directives.** `:::metric{…}` is wrong — `metric` is a
  leaf, so it is `::metric{…}` with no closing fence. Writing three colons
  makes the parser see an unterminated container and the whole page fails to
  convert.
* **The title and the heading.** The page `<title>` and the head tags come from the
  `page_head` hook. Markus's own `<header>` is removed by
  `FragmentTransform(strip_header=True)` and the production `.heading` (h1, date,
  authors, `.draft-overlay`) is prepended as a block sentinel by the `source` hook
  (`anthus_dom.article_heading`). A body `# Heading` would give the page two `<h1>`s.
* **Image wrappers ride in the layout name.** `<div className="center-full-image">`
  / `<figure>` / floated `<div style=...>` around an `::image{}` is DOM the
  stylesheet targets, and `::image{}` has no wrapper attribute, so the content
  encodes it as `layout="full@figure-cfi"` and `anthus_dom.anthus_image_wrap`
  decodes it. `anthus_layout_sizes` registers every combination.
* **The site stylesheet is hand-written.** `web/css/site-theme.css` is the design
  system (`web/DESIGN.md`) and the pictogram sprites in one file: edit it directly.
  Papyrus publishes it as `css/site-theme.css`.
* **Do not strip tag-shaped prose.** `<N>`, `<arm>`, `<QUERY>` appear in
  sentences as placeholders; Markus escapes them, which is what the author meant
  the reader to see.
* **`upgrade_plain_images=False` is load-bearing.** Cards and chrome use plain
  `<img>` with site-ABSOLUTE hrefs, which the image pipeline rejects by design.
  The `image_pipeline` hook sets it.
* **Renditions are made at upload, not at projection.** An image that has no
  rendition record in the site store cannot be placed; the projection fails loudly.
* **Pillow must be >=11.3** (it bundles libavif; the renditions Lambda needs it).
* **Main images start at `opacity:0`** (gatsby-plugin-image's behaviour).
  `view.finish` appends Papyrus's `FADE_IN_SCRIPT` to every page that has a
  `data-main-image`; without it the images stay invisible.
* **Page files are trusted HTML.** `::raw` is allowed only in `web/pages/*.md`
  (Papyrus rejects it in a CMS item). Whitespace between inline elements is
  visible, so break lines only between block elements.
* **A new page is a `pages` entry in `projection.json` and a file.** Keep its
  URL out of `legacy-redirect-rules.json` (a redirect would shadow it).

### Parity gate for site changes (PPY-e329c3)

Anth.us is production: a change to how the site is rendered or served is gated on every published URL before and
after it, not on spot checks.

1. Export the published content (`papyrus content export-published --out EXPORT`, IAM, `PAPYRUS_GRAPHQL_AUTH=iam`) and
   project it with the old code and with the new code (`bin/project_export_locally.py EXPORT OUT --redirects-json R`;
   `PAPYRUS_SITE_BUCKET` names the site store, whose image rendition records the projector reads).
2. `python3 bin/parity.py dir:OLD,OLD_R.json dir:NEW,NEW_R.json report.json [--allow allow.json]` compares every URL
   of either side through a simulated edge: status, redirect target, content type, cache control, normalised body
   DOM, head metadata (parsed JSON-LD included), sitemap URL set, robots.txt. Anything that differs and is not in
   the allow-list (each entry has a written reason) is blocking. It needs `lxml` and Papyrus on `PYTHONPATH`.
3. Deploy (merge; the Amplify job reprojects; an edge change goes by CloudFormation change set, read before it is
   executed). `bin/poll.py LOG` requests the key pages every 3 s through the change. Afterwards
   `bin/crawl.py https://anth.us DIR --extra paths.txt` and `python3 bin/parity.py live:BEFORE live:AFTER ...`, then
   `node bin/shoot.cjs` (Puppeteer) for home, an article, a listing, about and engage at 1440 and 390 and
   `bin/compare.py`. `node bin/edge-diff.mjs OLD.js NEW.js REDIRECTS.json URIS.txt` compares two viewer-request
   functions over a list of URIs.
