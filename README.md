# Anth.us-web

The source of the live **anth.us** website and the configuration of its **newsroom.anth.us** CMS. It is a
[Papyrus](https://github.com/AnthusAI/Papyrus) publication: Papyrus (the engine) renders and serves everything, and this
repository holds only the site's configuration, hand-written pages, a few named Python hooks, the stylesheet and the tests.
There is no renderer here. Content (articles, platform pages, images) lives in the CMS, not in this repository.

If you are an agent, read [AGENTS.md](AGENTS.md) next. It has the map of the parts, the exact commands and the hard rules.

## How it relates to the other repositories

| Repository | Role for this site |
| --- | --- |
| [Papyrus](https://github.com/AnthusAI/Papyrus) | The engine: standard Markus projector, CMS backend and console, plugins, monitoring, the procedure runner. Pinned here as `@anthusai/papyrus` (npm) and `papyrus-newsroom` (PyPI), always the same number. Read-only from this repository. |
| Cyclotron | The shared relevance classifier service. anth.us takes part in the Hacker News relevance routing ([AGENTS.md](AGENTS.md#shared-hacker-news-relevance-routing)). |
| Prospectus | Receives the engage form's contact submissions (`web/inquiry-config.json`). |
| Biblicus, Tactus | Papyrus's knowledge corpus tooling and its procedure language. Nothing in this repository calls them directly. |
| Other Papyrus sites (Pilobol.us, Threat Intelligence, p.apyr.us) | Siblings on the same engine. The privacy page here also covers several Anthus product sites. |
| `AnthusAI/Anth.us` | The old Gatsby site. Superseded; never send fixes there. |

## Where it runs

| Piece | Value |
| --- | --- |
| AWS account | `papyrus-production` (profile name), id `712236451410`, region `us-east-1` |
| Public site `anth.us`, `www.anth.us` | Static pages in a versioned S3 site bucket, behind CloudFront distribution `E3UMOOJRMY7FK7` (edge stack `papyrus-edge-anth-us`, pure S3 origin, 403 and 404 mapped to `/404.html`). DNS is the `anth.us` Route 53 zone in the same account |
| CMS `newsroom.anth.us` | Amplify app `anth-us-cms`, id `d7s858igkyct5` (Next.js SSR, Gen2 backend), behind its own CloudFront distribution `E3JU5W0MDN96GU` |
| Amplify branches | `main` (production, auto-build **off**) and `staging` (auto-build on, draft preview, no jobs run so far) |
| Backend stack | `amplify-app-shell-anth-us-cms`, configured by `infra/site.json` and `papyrus.config.ts` |
| Analytics | Google Analytics 4, measurement id `G-31SC26SDGX` (public), with Consent Mode ([AGENTS.md](AGENTS.md#ga4-and-consent)) |

Checked 2026-10-23 with read-only AWS and `curl` calls.

## Quick start

Prerequisites: Node 22 (CI uses 22; 26 also works), npm, Python 3.12. The tests need the Papyrus Python package at the
pinned version, with the `markus` extra.

```bash
git clone https://github.com/AnthusAI/Anth.us-web && cd Anth.us-web
npm ci
echo '{}' > amplify_outputs.json          # git-ignored stub; the real file is generated per deployment
npx papyrus-app sync                      # writes route shims; it also rewrites a block of .gitignore: do not commit that
npx tsc --noEmit                          # typecheck
npm run build                             # papyrus-app sync && next build (the newsroom app; works with the stub)

python3 -m venv ~/.venvs/anthus-web && . ~/.venvs/anthus-web/bin/activate     # keep the venv outside the repo
pip install "papyrus-newsroom[markus]==5.51.0" pytest
python -m pytest -q tests --ignore=tests/test_projector_incremental.py        # what CI runs
node --test tests/*.test.mjs tests/edge/*.test.mjs                            # browser scripts and the edge functions
```

The full suite, including `tests/test_projector_incremental.py`, needs the Papyrus source tree at the pinned tag:

```bash
git clone --branch v5.51.0 https://github.com/AnthusAI/Papyrus ../Papyrus      # or any checkout of that tag
PYTHONPATH=../Papyrus/src:../Papyrus python -m pytest -q tests
```

Local preview of the real site needs read access to the CMS: export the published content, project it with this
repository's `web/`, and serve the result.

```bash
papyrus ops content export-published --out EXPORT     # AWS credentials for papyrus-production, PAPYRUS_GRAPHQL_AUTH=iam
export PAPYRUS_ROOT=../Papyrus PAPYRUS_SITE_BUCKET=<site bucket>
PYTHONPATH=$PAPYRUS_ROOT/src:$PAPYRUS_ROOT python3 bin/project_export_locally.py EXPORT OUT --redirects-json R.json
python3 bin/dev-server.py OUT --port 8080
```

`PAPYRUS_SITE_BUCKET` names the site store whose image rendition records the projector reads. `npm run dev`
(`next dev --port 3001`) runs the newsroom app against a deployed backend and needs a real `amplify_outputs.json`.

## How a change reaches production

`main` is the production branch. The GitHub default branch `develop` is stale (it holds the Kanbus board and old
instructions). Open pull requests into `main`.

1. Branch from `origin/main` and open a pull request into `main`. The GitHub Actions workflow `CI and deploy`
   (`.github/workflows/deploy.yml`) runs the typecheck, the pytest suite and the node tests on the pull request.
2. Merge. The same workflow runs on the push, and once CI is green it calls the reusable Papyrus workflow
   `amplify-deploy.yml`. That assumes the AWS role `anth-us-github-deploy` through GitHub OIDC (no stored keys), starts an
   Amplify `RELEASE` job for the merged commit on the `main` branch of `anth-us-cms`, and waits for it.
3. The Amplify build (`amplify.yml`) runs `npx ampx pipeline-deploy`, which deploys the backend and bundles `web/` into the
   `content-actions` Lambda. Because `papyrus.config.ts` sets `publication.reprojectOnDeploy: true`, the deploy then renders
   every page inside AWS and runs a dry-run drift check. After that the newsroom app is built.

Merging is the deploy: there is no manual step, and nobody runs `project --all` by hand. **Every merge to `main` starts this,
including documentation-only merges.** The workflow has no path filter, and merge #115 (a README and a YAML file) started
Amplify job 34. Editors' saves in the newsroom reach the public site by themselves within seconds.

Papyrus changes ship separately. A Papyrus `feat:` or `fix:` merged to its `main` branch is released by semantic-release to
npm and PyPI under one version number (a `chore:` or `docs:` commit does not release). To adopt a release, bump the pin in
one pull request: `package.json`, `infra/package.json`, `infra/site.json` (`papyrusVersion`), the `papyrus-newsroom` pin in
`.github/workflows/deploy.yml`, and both lockfiles. Commit `e7351d0` ("chore: bump Papyrus to 5.23.0") is the model.

## Next

- [AGENTS.md](AGENTS.md): operating manual and hard rules for agents.
- [Papyrus docs index](https://github.com/AnthusAI/Papyrus/blob/main/docs/README.md): the engine's documentation.
- `web/DESIGN.md`: the site's design system. `infra/README.md`: the stack configuration.
- The Kanbus board (project key `anthus-web`) lives on the `develop` branch under `project/`; see AGENTS.md, "Board".
