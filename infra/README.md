# Anth.us infrastructure

`site.json` configures the Papyrus Amplify app-shell stack (CMS app plus reader app) for this publication. `package.json` pins `@anthusai/papyrus` to the same exact version as the repository root.

```bash
npm ci
npx papyrus-infra synth --site site.json
```

Synthesis only prints and writes `cdk.out/`. Deploying is a separate, reviewed step.

## Domains are deliberately absent

`site.json` has no `hostedZoneId`, no `reader.domainName` and no `reader.domainPrefixes`, so the stack creates no Amplify domain association. Production `anth.us` is still served by a separate legacy app. At cutover (a separate reviewed `cdk diff`) add `hostedZoneId`, `reader.domainName` `anth.us` and `reader.domainPrefixes` `["", "www"]`.

## Reader redirects

`reader.redirects` holds the 402 legacy 301 rules from `web/custom-rules.json`, in order. The template appends the `/<*>` to `/404.html` `404-200` rule last. Regenerate this list from `web/custom-rules.json` (dropping its final `404-200` entry) whenever the build changes the rules.

## Reader build

`reader.preBuildCommands` provisions the pinned Papyrus source, Markus, Pillow, PyYAML and citeproc-py, and `reader.skipContentExport` is false: the reader runs `papyrus ops content export-published --auth guest --out content-export --clean` and `web/build_via_papyrus.py` builds from that export (`ANTHUS_CONTENT_EXPORT`), so the CMS drives the site. `reader.environment` holds the CMS backend ids the guest export reads (`PAPYRUS_GRAPHQL_ENDPOINT`, `PAPYRUS_IDENTITY_POOL_ID`, `PAPYRUS_MEDIA_BUCKET`, non-secret) plus `SITE_ENV` and `PAPYRUS_SITE_BRAND`; keep them listed here, because a stack update replaces the branch's variables with this list.
