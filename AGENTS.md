# AGENTS.md: Anth.us-web

Operating manual for agents in any tool. Start with [README.md](README.md) for what this is, where it runs and how a change
ships. This file is the map, the recipes and the rules. Paths starting `~/` are your own checkouts; a Papyrus link is to
`https://github.com/AnthusAI/Papyrus/blob/main/docs/<file>`.

## Orient in one minute

* This repository is the **anth.us** website plus the configuration of its **newsroom.anth.us** CMS. The engine is
  [Papyrus](https://github.com/AnthusAI/Papyrus); this repository has no renderer. `main` is production. `develop` is stale
  and holds only the Kanbus board.
* **Public site.** `anth.us` and `www.anth.us` are static pages in an S3 site bucket behind CloudFront
  `E3UMOOJRMY7FK7`. Saving in the newsroom projects the page within seconds. Merging to `main` re-renders every page inside
  AWS. Details: README, "How a change reaches production".
* **Account.** AWS profile `papyrus-production`, account `712236451410`, `us-east-1`. Amplify app `anth-us-cms`
  (`d7s858igkyct5`). Use the AWS CLI and API only; do not drive the AWS console for this app.
* **Never touch** the old Gatsby site (`AnthusAI/Anth.us`) or its Amplify apps. Never change DNS, an Amplify domain
  association, a hosted zone or the edge stack from this repository: an edge change is a CloudFormation change set that Ryan
  approves.
* **Read-only neighbours:** `~/Projects/Papyrus` (the engine; changes there are Papyrus pull requests on the `PPY` board),
  `~/Projects/Anth.us` (old site, reference only) and `~/Projects/Pilobol.us` (architectural template).

## Hard rules

1. **Never run `papyrus ops content project --reconcile` without the deployed plugin list, and never use
   `--allow-deletions`.** A reconcile deletes pages the projector owns and nothing expects; the plugin list is how it tells a
   plugin's pages from orphans. Run a dry run first (`--reconcile --dry-run`), fix the configuration if it reports deletions
   you did not intend, and ask Ryan before any deletion. See "Re-project safely".
2. **Projections take the projection lease.** Every write to the site bucket (`project`, `--reconcile`, the deploy-time
   render, a publish) holds a per-bucket lease in DynamoDB. Never write the bucket another way, and never clear a lease
   unless you have confirmed its holder is gone ([lease](https://github.com/AnthusAI/Papyrus/blob/main/docs/site-hosting.md#projection-lease-one-projection-at-a-time)).
3. **Secrets live in SSM SecureString**, never in the repository, a workflow, a build log or a chat. Keys are never read
   from config files; the measurement id `G-31SC26SDGX` and the AWS ids in these docs are public identifiers, not secrets.
4. **No real email addresses in the repository.** Allowlists and recipients live in AWS configuration; docs and specs use
   placeholders. The two addresses already published on the site (the engage form fallback in `web/inquiry-config.json` and the
   contact line of `web/pages/privacy.md`) are the only ones; do not add others and do not copy those elsewhere.
5. **Shared checkouts: never switch branches and never `git stash`.** Another session may be working in that tree. Use a
   worktree: `git -C ~/Projects/Anth.us-web worktree add /private/tmp/<name> -b <branch> origin/main`, and remove it when
   done. Stage files deliberately (never `git add -A` in a dirty tree). Never force-push, never amend a pushed commit.
6. **Every behaviour change gets a Gherkin spec.** The spec lives in the Kanbus story (Given/When/Then, observable behaviour
   only), and the executable check is a test in `tests/` that fails first. This repository has no `.feature` files today: its
   tests are Python `unittest`/pytest and `node --test`. No red tests.
7. **Kanbus conventions.** The board is the record: file or update the card before you code, log decisions as comments,
   close it after the change lands. Run `KANBUS_REALTIME_BROKER=off kbs ...`. Statuses move `open` (Discovery) to
   `in_progress` to `blocked` (and `blocked` back to `in_progress`), then `closed`. Never read or edit `project/` files
   directly. Board changes are merged through their own branch and pull request into `develop` (see "Board").
8. **Wording.** No "desk" (sections, not desks; the word is fine as a drawing variable in `web/arcade_pictograms.py`, not in
   copy). Attribution of machine-written work is "AI". Say "Account", never "Organization". Copy rules are in
   `web/DESIGN.md`, section 8; claims about outages, uptime and production are pinned by tests (do not weaken them).
9. **GA4 consent is the anth.us standard.** Standard Consent Mode stays on because Ryan plans to run Google Ads. Do not set
   `analytics_only`. See "GA4 and consent".
10. **Human review is a review request, never a story state.** Do not add a "needs review" state to an item or a Kanbus
    status. Review requests are planned work in Papyrus (see "Review requests"); until they ship, ask Ryan in chat.
11. **Never use the Amplify console's "Connect repository" reconnect on this app.** On 2026-10-19 it deleted the backend
    stack and all DynamoDB data. Record `get-app` and `list-branches` before and after any change to the app.
12. **Do not edit the CMS data store, the bucket or the router configuration by hand** to make a symptom go away. Fix the
    cause in code, merge, and let the deploy render.
13. **Never put generated or local state in git:** `amplify_outputs.json`, `.next/`, `cdk.out/`, `content-export/`,
    `web/dist-papyrus/`, and the route shims `npx papyrus-app sync` writes. That command also rewrites a block of
    `.gitignore`; run `git checkout .gitignore` before committing.

## Map of the parts

Each part is described for how it applies to anth.us; the engine docs are the authority and are linked, not copied.

| Part | On anth.us | Engine doc |
| --- | --- | --- |
| Standard projector (Markus static front end) | `web/projection.json` configures it; `web/hooks.py` and its modules are the named hooks; pages are `web/pages/*.md`. Output goes to the S3 site bucket | [building-a-papyrus-static-site](https://github.com/AnthusAI/Papyrus/blob/main/docs/building-a-papyrus-static-site.md), [site-hosting](https://github.com/AnthusAI/Papyrus/blob/main/docs/site-hosting.md) |
| CMS backend and console | Amplify Gen2 backend (`amplify/backend.ts`, `papyrus.config.ts`, `infra/site.json`), Google sign-in, the newsroom at `newsroom.anth.us`. The console home is planned to become the Notification Center (planned, not built) | [how-papyrus-works](https://github.com/AnthusAI/Papyrus/blob/main/docs/how-papyrus-works.md), [newsroom-operations](https://github.com/AnthusAI/Papyrus/blob/main/docs/newsroom-operations.md), [google-oauth-setup](https://github.com/AnthusAI/Papyrus/blob/main/docs/google-oauth-setup.md) |
| Plugins: reader-steering (votes, flags, Proposals), newsletter | **None enabled.** `papyrus.config.ts` lists no `plugins`, so the deployed plugin list is empty and the site has no reader or newsletter routes (`/newsletter/` answers 404). Enabling one is a deliberate change: add it in `backend.plugins`, see the docs, then re-check the reconcile rule | [plugins](https://github.com/AnthusAI/Papyrus/blob/main/docs/plugins.md), [reader-steering](https://github.com/AnthusAI/Papyrus/blob/main/docs/reader-steering.md), [newsletter](https://github.com/AnthusAI/Papyrus/blob/main/docs/newsletter.md) |
| Edge (404 page, `/api` pass-through) | A pure S3 distribution: 403 and 404 map to `/404.html` with status 404; redirects come from a CloudFront function and key-value store compiled from `web/projection.json`; headers from `infra/edge/viewer-response.js`. There is **no** `/api` pass-through and no Lambda@Edge `NotFoundPage` on this host (those exist only on distributions with CMS behaviors). The engage form posts straight to Prospectus | [site-hosting, "The 404 page and its headers"](https://github.com/AnthusAI/Papyrus/blob/main/docs/site-hosting.md#the-404-page-and-its-headers), [infra/edge README](https://github.com/AnthusAI/Papyrus/blob/main/infra/edge/README.md) |
| Monitoring and router | Shared stack `papyrus-monitoring`, owned by Papyrus, not by this site. anth.us is a router publication for Hacker News. See "Shared Hacker News relevance routing" | [monitoring-cloud](https://github.com/AnthusAI/Papyrus/blob/main/docs/monitoring-cloud.md), [sources-and-monitoring](https://github.com/AnthusAI/Papyrus/blob/main/docs/sources-and-monitoring.md) |
| Shared relevance Cyclotron | One standing Cyclotron decides include or exclude per publication; output `anth-us-relevance`. Doctrine in `corpora/papyrus-publication-doctrine.yml` mirrors the production records | [steering-and-relevance](https://github.com/AnthusAI/Papyrus/blob/main/docs/steering-and-relevance.md), [cyclotron-priming](https://github.com/AnthusAI/Papyrus/blob/main/docs/cyclotron-priming.md) |
| Procedure runner and Tactus procedures | The engine runs a site's published Tactus procedures in the cloud. **This repository registers none.** | [procedure-runner](https://github.com/AnthusAI/Papyrus/blob/main/docs/procedure-runner.md), [newsroom-procedures-runbook](https://github.com/AnthusAI/Papyrus/blob/main/docs/newsroom-procedures-runbook.md) |
| Knowledge run (cloud and local) | **Not configured for anth.us.** The corpus section list is `corpora/anth-us-newsroom-sections.yml` | [knowledge-workstation-run](https://github.com/AnthusAI/Papyrus/blob/main/docs/knowledge-workstation-run.md), [knowledge-cloud-run](https://github.com/AnthusAI/Papyrus/blob/main/docs/knowledge-cloud-run.md) |
| Automations | The `Automation` record model exists in every site's API; none are defined for anth.us. Papyrus 5.35.0 ships the `papyrus automations` command | [automations](https://github.com/AnthusAI/Papyrus/blob/main/docs/automations.md) |
| Review requests and the Notification Center | **Planned, not built.** Papyrus stories "Human review points" and "CMS console Notification Center" are open on its board | (no doc yet; Papyrus board) |
| GA4 and consent | Built and live. See "GA4 and consent" below | [site-hosting, "Analytics"](https://github.com/AnthusAI/Papyrus/blob/main/docs/site-hosting.md#analytics-google-analytics-4) |
| Engage form | `web/inquiry-config.json` is its only configuration: endpoint, notice version `contact-v1`, approved notice text, and a fallback address. It is bundled with `web/` into the projector Lambda; Next build variables do not configure it | [public-forms](https://github.com/AnthusAI/Papyrus/blob/main/docs/public-forms.md) |

## Common tasks

Run the test commands from README, "Quick start".

**Run tests.** CI's set: `python -m pytest -q tests --ignore=tests/test_projector_incremental.py`, `node --test
tests/*.test.mjs`, `npx tsc --noEmit`. Also `node --test tests/edge/*.test.mjs` (CI does not run it). The full Python suite
needs a Papyrus source tree at the pinned tag on `PYTHONPATH` (README).

**Change the site.** Edit `web/` (config, pages, hooks, `web/css/site-theme.css`), add or change a test in `tests/`, run the
suite, open a pull request into `main`. Content changes (articles, platform pages, images) are made in the newsroom, not here.

**Bump the Papyrus pin.** Edit the six places listed in README ("How a change reaches production"), run `npm install` in
the root and in `infra/`, `npx papyrus-app sync`, `npx tsc --noEmit`, the pytest suite against the new
`papyrus-newsroom[markus]==X`, then open a pull request titled `chore: bump Papyrus to X`. The merge deploys.
(Papyrus 5.29-5.32 changed `entry.authors` to structured objects; 5.33.0 restores plain names, with the structured form
in `entry.author_details`. Never pin 5.29-5.32.) Releases
come from Papyrus `feat:` and `fix:` commits on its `main`; `chore:` and `docs:` do not release.

**Deploy.** Merge to `main`. Watch it: `gh run list --workflow "CI and deploy"`, then
`AWS_PROFILE=papyrus-production aws amplify list-jobs --app-id d7s858igkyct5 --branch-name main --max-items 3 --region us-east-1`.
A render that fails fails the build; drift (orphan or stale pages) is reported in the Lambda log and the
`Papyrus/Projection` `DeployRenderDrift` alarm, and nothing is deleted. Do not start a manual RELEASE job right after a
merge: it hides the automatic one for the same commit. Do not run `ampx pipeline-deploy` locally.

**Verify a deploy.** `python3 bin/check-guards.py https://anth.us --expect production` and
`python3 bin/check-404.py https://anth.us` (both read-only, both pass today). For a wide change use the parity gate below.

**Re-project safely.** Normally you never need to: the deploy and every save project for you. If a projection failed (a
save answered `live: false`, or the `DeployRenderDrift` alarm fired):

1. Get the deployed backend's `amplify_outputs.json` and set `PAPYRUS_SITE_ROOT` (or `--amplify-outputs PATH`) to it, so the
   plugin list is the deployed one (anth.us's is empty). Without it a non-dry-run reconcile refuses.
2. `papyrus ops content project --reconcile --dry-run --static-dir web --bucket <site bucket>` (credentials for
   `papyrus-production`; exits 1 on drift, writes nothing, takes no lease).
3. Only if the report is what you expect, `papyrus ops content project --reconcile --static-dir web --bucket <site bucket>`
   from a clean, up-to-date checkout of `main`. A stale `web/` makes the projector look like it no longer places a section; the
   deletion guard then refuses and exits 2. Fix the checkout; do not pass `--allow-deletions`. (The guard and that flag are in the 5.35.0 pin; still dry-run first.)
4. `project --all` re-renders everything and deletes nothing; use it after a deploy that failed to render. Pages written
   by a run use the `web/` of the checkout that ran it.

Not run here: these need credentials and a real backend. The dry-run refusal without `amplify_outputs.json` was confirmed
locally (`Missing amplify_outputs.json`).

**Render locally without touching AWS state:** `papyrus ops content project --all --out DIR --static-dir web` (writes no
live data, takes no lease), or `bin/project_export_locally.py` (README).

**Register a site procedure** (none exist today). Put the Tactus file in a `procedures/` folder, then
`papyrus procedures register --file procedures/<name>.tac --key anth-us.<name>` with an editor session, and follow
[procedure-runner](https://github.com/AnthusAI/Papyrus/blob/main/docs/procedure-runner.md). The router starts procedures from
`procedureTriggers` in its configuration, which is Papyrus-owned.

**Create an automation.** Uses `papyrus automations` (in the 5.35.0 pin); the command
shape is in [automations](https://github.com/AnthusAI/Papyrus/blob/main/docs/automations.md). The record starts nothing by itself.

**Start a new Papyrus site.** Use this repository as the model: `infra/site.json`, `papyrus.config.ts`, `web/projection.json`,
`amplify.yml`, `.github/workflows/deploy.yml`. The steps are in
[site-hosting, "How a new publication opts in"](https://github.com/AnthusAI/Papyrus/blob/main/docs/site-hosting.md#how-a-new-publication-opts-in)
and [new-publication-from-corpus](https://github.com/AnthusAI/Papyrus/blob/main/docs/new-publication-from-corpus.md).
`npx papyrus-infra synth --site site.json` (in `infra/`) only prints; deploying a stack is a reviewed step.

**Rollback.** A bad edit: restore the previous item version in the newsroom and save. Bad site code: revert the pull request
on `main` (the deploy re-renders). A bad edge: update the edge stack with the previous template (Ryan approves the change set).

## GA4 and consent

Standard Google Consent Mode is the anth.us standard, on every anth.us page and meant for the product sites that link to its
privacy policy. It exists so Ryan can run Google Ads; `analytics_only` must stay off.

* **Where.** `web/projection.json`, `chrome`: `ga_measurement_id` is `G-31SC26SDGX` (public), `ga_owner_opt_out` is `true`, and
  `consent_mode` carries only wording and `privacy_policy_url: "/privacy/"`. There is no `analytics_only` key, so it takes
  Papyrus's default, `false`. The code is Papyrus's `markus_renderer/consent.py`; this repository only configures it.
* **Defaults and updates.** In the EEA, UK and Switzerland (`denied_by_default_regions`, gtag's own region detection) all four
  signals start denied. Everywhere else `analytics_storage` starts granted and `ad_storage`, `ad_user_data`,
  `ad_personalization` start denied. `wait_for_update` is 500 ms. "Accept all" and "Reject all" call
  `gtag('consent','update',...)` for all four signals. The choice is kept in localStorage under `anthus-consent` for 183 days;
  raising `policy_version` re-prompts everyone. `ads_data_redaction` is on and `url_passthrough` is off.
* **Reopen.** The footer "Cookie settings" link (`web/anthus_dom.py`) carries `data-papyrus-consent-reopen`.
* **Owner opt-out.** `?notrack=1` once per browser stops counting it (`ga-disable-G-31SC26SDGX`); `?notrack=0` undoes it.
* **Events.** `cta_click` comes only from Papyrus's shared listener (`markus_renderer/analytics_events.py`, 5.28+): it fires
  once for any link carrying `data-cta-location` (and for `anth.us/engage` links, using their `cta` value), with
  `cta_text`, `cta_location`, `link_url` (host and path) and `transport_type: beacon`. `web/assets/site-nav.js` sets
  `data-cta-location` on every engage link and every off-site `http(s)` link, so GitHub and LinkedIn links also report
  `cta_click`. **anth.us must not send its own `cta_click`**: the retired `web/assets/conversion-events.js` did, and the
  two sent every engage and product click twice. `web/static-root/engage-inquiry.js` sends `generate_lead` when the form
  endpoint answers 2xx. Address redaction is Papyrus's. Event table: Papyrus site-hosting, "Events and address redaction".
* **Privacy page.** `web/pages/privacy.md` (`/privacy/`) ships with the banner and describes the same behaviour. Change the
  banner wording, the policy and `policy_version` together.
* **Verify (all read-only; run 2026-10-23).**
  `curl -s https://anth.us/ | grep -o "gtag('consent'[^;]*;"` shows a region-scoped default with all four denied, then a
  default with `analytics_storage:'granted'`, then the `update` using the same value for all four signals;
  `curl -s https://anth.us/ | grep -c "G-31SC26SDGX"`; `python3 bin/check-guards.py https://anth.us --expect production`;
  `python -m pytest -q tests/test_privacy_page.py tests/test_conversion_events.py tests/test_site_env.py`; and
  `node --test tests/conversion-events.test.mjs` (`test_conversion_events.py` runs Papyrus's rendered script against
  `site-nav.js` and asserts one `cta_click` per click). Live data checks (GA4 DebugView, key events, custom dimensions, Google Ads
  conversions) are open board cards under the conversion-tracking epic.
* Guarded builds (local, review, the CMS `staging` branch) never load analytics.

## Shared Hacker News relevance routing

Hacker News items are collected once and routed to each participating publication by the shared relevance Cyclotron. anth.us
is one of the participating publications (with `p-apyr-us` and `threat-intelligence`, per Papyrus's monitoring doc on
`main`, 2026-10-23). The flow:

1. The **collector** Lambda (every 15 minutes) fetches the feed, dedupes and records discoveries in the
   `papyrus-monitoring` DynamoDB table. It writes nothing to any publication.
2. The **router** Lambda (minutes 7, 22, 37 and 52) asks the Cyclotron which collected items each configured publication
   wants, using output `<publicationId>-relevance` (`anth-us-relevance`), and delivers only `include` items as `pending`
   References with a provenance Message into that site's References queue. Editors accept or reject there; accepted and
   rejected decisions flow back to the Cyclotron as labels only when the router config has `feedback: true`.
3. Nothing is ever auto-accepted, and a human decision is never reset.

**To add a site** (a Papyrus-owned change: tell the Papyrus session first; it edits the shared stack and data):

1. The site's backend is deployed and its publication has exactly one canonical `KnowledgeCorpus`; its publication doctrine
   is in place (`/newsroom/administration/policies`), because the classifier criteria derive from it.
2. In the shared Cyclotron, bind the publication to the standing run with output `<publicationId>-relevance` (labels
   `include` and `exclude`). Until the output has criteria the router parks the binding (HTTP 409 "publication criteria
   are pending") and keeps serving the others. See the Cyclotron repository's `docs/hosted-publications.md`.
3. In the `papyrus-monitoring` stack (`infra/monitoring/papyrus-monitoring.yaml` in Papyrus) add the site's AppSync API to
   the router role: the inline policy holds three sites, so further sites go in a managed policy like
   `RouterDistinctiveIntakePolicy`, plus `RouterDecisionRelationPolicy` for decided sites. Deploy it with a CloudFormation
   change set, read first, **before** step 4.
4. Add the site to `publications` in the router config item (`CONFIG#router`):
   `{"publicationId": "<id>", "site": "<host>", "appsyncEndpoint": "https://<api>.appsync-api.us-east-1.amazonaws.com/graphql"}`
   (`corpusId` only if it is not `knowledge-corpus-<id>`). Write it with
   `AWS_PROFILE=papyrus-production python3 infra/monitoring/seed_router_config.py --table <table> --file router.json --replace`
   (the table name is the SSM parameter `/papyrus/monitoring/table-name`). The script validates the config and refuses
   non-AppSync endpoints. `mode` is router-wide: with the router live, the new site starts receiving items as soon as this
   is stored, so confirm steps 2 and 3 first.
5. Verify in the site's newsroom at Administration, Monitoring (`/newsroom/administration/monitoring`, read-only), and in
   References for pending items with a Cyclotron provenance Message.

Verified 2026-10-23 (router side, read-only): the deployed papyrus-monitoring stack's `AnthUsApiId` is the live
AppSync API tagged `amplify:app-id d7s858igkyct5` (this app), so the router's anth.us grants point at the post-rebuild
API, and the router has delivered to anth.us since 2026-10-21. Re-check this after any backend rebuild: a rebuild
recreates the AppSync API, and the stored `appsyncEndpoint` must match `data.url` in the deployed `amplify_outputs.json`.

## Review requests

Human review is a review request on an item, never a story state. Papyrus plans three modes (flag, soft review with a
deadline, hard gate) and a Notification Center in the console that lists them. Both are open stories on the Papyrus board
today and are **not built**. Do not invent a substitute state here.

## How `web/` works

* `web/projection.json` is the site: identity, URL policy, collections, pages, `notFound`, `chrome`, SEO, redirects, images.
  Collections (`articles`, `posts`, `reading`, `research`) are defined by tag; pagination is the engine's.
* `web/hooks.py` registers the named hooks Papyrus calls (source, item_transform, image_pipeline, page_head, page_body,
  page_finish, card, block, redirects, page_inputs, item_filter). The other Python modules in `web/` implement them: cards and
  listings, `site_blocks.py` (pictograms, solution grids, further reading, the engage form), `view.py`/`links.py` (page
  envelope, canonical links, legacy redirects), `solution_marks.py`, `arcade_pictograms.py`, `inquiry_form.py` and helpers.
* **Page files** `web/pages/<id>.md` are the body of the page named in `projection.json` `pages[].source`
  (`notFound.source` for the 404 page). They start with `::band{size="bare"}` and are `::raw` ... `::endraw` regions (trusted
  HTML; allowed only here, never in a CMS item) plus `::include{kind=...}` lines. `kind="listing"` takes `collection=` or
  `sections= tags= allTags= notTags=`, `sort`, `ties`, `skip`, `count`, `card=` (variants in `web/cards.py`: `text`, `mini`,
  `line`, `chip`), `layout`, `tag`, `class`. `kind="block" name=... depends=...` calls `site_blocks.render`. Includes that
  name content are the page's declared dependencies, so a publish rewrites exactly the pages that show the item.
* The stylesheet `web/css/site-theme.css` is hand-written (design system in `web/DESIGN.md`; `web/DESIGN-PARITY.md` is
  historical). Edit it directly.
* `web/legacy-redirect-rules.json` is the frozen redirect list of the previous host; keep a new page's URL out of it.
* The featured solutions, the Primus credibility section, the proof strip and the claims-honesty wording are pinned by tests
  (`tests/test_featured_solutions_auritus.py`, `tests/test_homepage_primus_proof.py`, and others). A copy change that breaks
  one is a design decision for Ryan, not a test to loosen.

Things that bite:

* `::metric{...}` is a leaf directive: no closing fence. Three colons make the parser see an unterminated container and the
  whole page fails to convert.
* The title comes from the `page_head` hook and the visible heading is prepended by the `source` hook; a body `# Heading`
  gives two `<h1>`s.
* Image wrappers ride in the layout name (`layout="full@figure-cfi"`); `anthus_dom.anthus_image_wrap` decodes them.
* `upgrade_plain_images=False` is load-bearing: cards and chrome use plain `<img>` with site-absolute paths.
* Renditions are made at upload, not at projection. An image with no rendition record in the site store cannot be placed, and
  the projection fails loudly. Pillow must be 11.3 or newer in the renditions Lambda.
* Main images start at `opacity:0` and need the fade-in script `view.finish` appends.
* Do not strip tag-shaped prose such as `<N>` or `<QUERY>`; the engine escapes it on purpose.
* Whitespace between inline elements is visible inside `::raw`; break lines only between block elements.

## Environment switch

The projector is **production** when its origin (`PAPYRUS_SITE_PUBLIC_URL`, default `site.productionUrl`) is
`https://anth.us`; `PAPYRUS_SITE_ENV=guarded` or `production` overrides the guess, and any other origin is guarded. The live
Lambda sets neither, so it is production. A guarded build is `noindex`, has a staging note in the footer, serves
`Disallow: /` in `robots.txt` and loads no analytics. Never hand-edit a guard out to go live. Local or review projections
should set `PAPYRUS_SITE_PUBLIC_URL=https://<review-host>` and `PAPYRUS_SITE_ENV=guarded`. Both modes publish
`/sitemap-index.xml` and `/sitemap-0.xml`; there is no `/sitemap.xml`. The CMS `staging` branch previews drafts through the
same projector (`cms.stagingPreview` in `infra/site.json`).

## Parity gate for site changes

A change to how the site is rendered or served is gated on every published URL before and after, not on spot checks.

1. Export the published content and project it with the old code and the new code (`bin/project_export_locally.py`).
2. `python3 bin/parity.py dir:OLD,OLD_R.json dir:NEW,NEW_R.json report.json [--allow allow.json]` compares every URL through
   a simulated edge. Anything that differs and is not allow-listed (each entry with a written reason) blocks. It needs `lxml`
   and Papyrus on `PYTHONPATH`.
3. After the merge, `bin/poll.py LOG` requests key pages every 3 s through the deploy, then
   `bin/crawl.py https://anth.us DIR --extra paths.txt`, `bin/parity.py live:BEFORE live:AFTER ...`, `node bin/shoot.cjs`
   (Puppeteer) at 1440 and 390, and `bin/compare.py`. `node bin/edge-diff.mjs OLD.js NEW.js REDIRECTS.json URIS.txt`
   compares two viewer-request functions.

The tools in `bin/` were not all run for this document; `check-guards.py` and `check-404.py` were.

## Board

The Kanbus project (key `anthus-web`, config `.kanbus.yml`, data under `project/`) is committed on **`develop`**, not `main`.
To work with it, use a worktree of `develop`: `git worktree add --detach /private/tmp/anthus-board origin/develop`, then in it
`KANBUS_REALTIME_BROKER=off kbs list`, `kbs show <id>`, `kbs create`, `kbs comment`, `kbs close`, and `kbs commit` to
persist issue state. Put board changes on a `board/<slug>` branch and open a pull request into `develop` (examples: #107,
#112). Product code goes to `main`. Tag created cards and comments with `--agent-platform`, `--agent-model` and `--agent-name`.
Hierarchy: initiative, epic, task, sub-task; stories hold Gherkin, not implementation steps. Remove the worktree when done.

## Ownership and coordination

* **This repository's session** owns the site: `web/`, tests, the page copy, the infra configuration and the Papyrus pin.
* **The Papyrus session** (board `PPY`) owns the engine and the shared pieces: the monitoring stack and router, the procedure
  runner, the Cyclotron integration, Prospectus-facing changes on Prospectus `main`. Tell it before you change or depend on
  those; do not patch them from here.
* **Ryan** approves edge and DNS changes, the privacy and consent wording, anything that removes pages, and any merge that
  changes what visitors see in a way the task did not ask for. Ask in chat.

## Current state (2026-10-23)

* **Live:** the arcade-redesign site on the S3 projection since 2026-10-13; the CMS backend was rebuilt on 2026-10-19 after the
  console reconnect (same app id, new data stores) and content was re-imported. Papyrus pinned at 5.53.1 (PR #124 is the 5.42.1 bump;
  the 5.53.1 bump deploys on merge). Merge-driven deploy through Actions and OIDC is in use: Amplify job 39 (the #121 merge) succeeded. The consent
  banner and `/privacy/` shipped together on 2026-10-22; every call to action reports to GA4; the engage form posts to
  Prospectus with an email fallback; Cyclotron is labelled "Early access".
* **Checked today:** distribution `E3UMOOJRMY7FK7` is `Deployed`, aliases `anth.us` and `www.anth.us`; `main` auto-build off;
  `staging` auto-build on with no jobs; edge stack `UPDATE_COMPLETE`; `check-guards.py` and `check-404.py` pass; local
  tests: 189 passed (with Papyrus v5.23.0 on `PYTHONPATH`, before the 5.35.0 bump), 47 + 13 node tests passed, `npm run build` succeeded.
* **In progress on the board (develop):** the conversion tracking and consent epic (verify events in GA4 DebugView, mark
  `generate_lead` as a key event, register custom dimensions, Google Ads conversions blocked, LinkedIn Insight behind consent),
  the Cognitive Debt section story, Search Console verification, and audit bugs filed 2026-10-20 (including a P1 about a
  draft body on a live article). The board can lag the code; run `kbs list` for the truth.
* **Known gaps:** `develop` is about 80 commits behind `main` and its README is stale; the router configuration was
  re-verified after the backend rebuild (2026-10-23) and must be re-checked after any future rebuild; cleanup of old resources retained from the rebuild is pending; reader
  steering, the newsletter plugin, procedures, automations, review requests and the Notification Center are not part of the
  site today.

## Where to look next

* Engine docs: [Papyrus docs index](https://github.com/AnthusAI/Papyrus/blob/main/docs/README.md). Hosting runbook:
  [site-hosting](https://github.com/AnthusAI/Papyrus/blob/main/docs/site-hosting.md). Markus markup (images, citations):
  [markus-content-markup](https://github.com/AnthusAI/Papyrus/blob/main/docs/markus-content-markup.md).
* This repository has no `docs/` directory. Design: `web/DESIGN.md`. Infrastructure: `infra/README.md`. Doctrine mirror:
  `corpora/papyrus-publication-doctrine.yml` (approved 2026-10-21; nothing reads it at build time).
