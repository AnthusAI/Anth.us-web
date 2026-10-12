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

`reader.preBuildCommands` mirrors the `amplify.yml` provisioning (content submodule, pinned Papyrus source, Markus, Pillow, PyYAML, citeproc-py) and `reader.skipContentExport` is true because the reader builds from the content submodule, not the CMS.
