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

# Anth.us-web

The source of the live **anth.us** site, built on [Papyrus](https://github.com/AnthusAI/Papyrus)'s standard Markus
front end. `anth.us` and `www.anth.us` are served from an **S3 projection**: static pages in a versioned S3 bucket
behind our own CloudFront distribution, written by the publish mutation of the CMS app (Save is live within seconds, no
build, no Amplify reader app). The old Gatsby site lives in `AnthusAI/Anth.us` and is not part of this repo. See
[AGENTS.md](AGENTS.md) and the architecture picture in
[Papyrus](https://github.com/AnthusAI/Papyrus#how-a-papyrus-publication-fits-together).

* Guarded builds (local, review or the CMS staging preview) ship `<meta name="robots" content="noindex, nofollow">`, a
  `robots.txt` of `Disallow: /`, no analytics and a staging note in the footer (AGENTS.md, "Environment switch").
* Never change DNS, an Amplify domain association or the edge stack from this repo without Ryan's approval.

## What is here

The site is configuration, content and a few named hooks. There is no renderer in this repository.

```text
web/
  projection.json         The site: identity, URL policy, collections by tag, pages, notFound, chrome, SEO, redirects
  css/site-theme.css      The one stylesheet (the arcade design system, web/DESIGN.md). Hand-written: edit it directly
  assets/                 Chrome scripts and site imagery (assets/site/), published as they are
  static-root/            Files published at the site root (favicon, manifest, icons, engage-inquiry.js)
  pages/*.md              The authored pages: home, about, ai-solutions, ryan, engage, decision-models, benchmarks,
                          platform (index), 404. Markus files with ::raw HTML and ::include{...} blocks
  hooks.py                The named hooks Papyrus calls (source, item_transform, image_pipeline, page_head, page_body,
                          page_finish, card, block, redirects, page_inputs, item_filter)
  cards.py listings.py    The arcade cards and the listing pages (collections, tag pages, tag index)
  site_blocks.py          The blocks pages include: pictograms, solution grids, further reading, the engage form
  view.py links.py        The page envelope and head; canonical links and every legacy redirect
  site_support.py source_text.py platform_product.py anthus_dom.py anthus_content.py anthus_urls.py
  solution_marks.py arcade_pictograms.py solution_sites.py product_availability_labels.py inquiry_form.py
  legacy-redirect-rules.json legacy-og-images.json content-redirects/   Redirect data
  inquiry-config.json     The engage form's endpoint and notice (only configuration of the form)
bin/                      Parity gate tools (parity.py, crawl.py, poll.py, shoot.cjs, compare.py, edge-diff.mjs), checks
infra/                    Site stack config (site.json) and the edge (CloudFront functions, template)
tests/                    pytest suite over a fixture corpus; node tests for the edge function and the browser scripts
```

Content (articles, platform pages, images) lives in the CMS, not in this repository. A draft is an item whose front matter
has `state: draft`: it is served, noindexed and shown only in the hidden drafts section (`?drafts`).

## Work on it

```bash
# project the published content of the CMS (an `export-published` directory) with this repository's web/ into a folder
PAPYRUS_ROOT=/path/to/Papyrus PAPYRUS_SITE_BUCKET=<site bucket> python3 bin/project_export_locally.py EXPORT OUT --redirects-json R.json
python3 bin/dev-server.py OUT --port 8080
PYTHONPATH=$PAPYRUS_ROOT/src:$PAPYRUS_ROOT python3 -m pytest tests
```

`PAPYRUS_SITE_BUCKET` names the site store whose image rendition records the projector reads. The deploy is a merge to
`main` (AGENTS.md, "Hosting").

## Publication doctrine

`corpora/papyrus-publication-doctrine.yml` mirrors the production doctrine records edited at `/newsroom/administration/policies`. Ryan approved it on 2026-10-21. It is the doctrine the relevance classifier criteria derive from. Nothing in the build reads this file; it is here for version control.
