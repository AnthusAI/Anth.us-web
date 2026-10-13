# Anth.us infrastructure

`site.json` configures the Papyrus Amplify app-shell stack (the CMS app) for this publication. `package.json` pins `@anthusai/papyrus`, which supplies the template.

```bash
npm ci
npx papyrus-infra synth --site site.json
```

Synthesis only prints and writes `cdk.out/`. Deploying is a separate, reviewed step.

## No reader app

anth.us is served from the S3 projection through the `papyrus-edge-anth-us` CloudFront stack (template in the Papyrus repo, `infra/edge/anth-us-s3.yaml`). `site.json` has no `reader`, so the stack creates no Amplify reader app. The 402 legacy redirects that used to be `reader.redirects` live in the redirect key-value store the projection writes.

`cms.stagingPreview` is the build the CMS `staging` branch runs to preview drafts. It was `reader.buildCommand` and `reader.baseDirectory` before the reader app was removed, and generates the same staging build spec.
