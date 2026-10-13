# Anth.us infrastructure

`site.json` configures the Papyrus Amplify app-shell stack (the CMS app) for this publication. The public site is **not** an Amplify reader app: it is an S3 projection behind the CloudFront stack `papyrus-edge-anth-us` (`edge/anth-us-s3.template.yaml`), with the edge functions in `edge/viewer-request.js` and `edge/viewer-response.js`. See `Papyrus/docs/site-hosting.md`. `package.json` pins `@anthusai/papyrus` to the same exact version as the repository root.

```bash
npm ci
npx papyrus-infra synth --site site.json
```

Synthesis only prints and writes `cdk.out/`. Deploying is a separate, reviewed step.

## Domains and DNS

Aliases (`anth.us`, `www.anth.us`) and the ACM certificate belong to the edge stack, not to Amplify. `site.json` has no `hostedZoneId` and no domain settings on purpose: never add an Amplify domain association for these hosts. Edge changes are CloudFormation change sets that Ryan approves.

## Legacy reader settings in `site.json`

The `reader` block (redirects, pre-build commands, build command, environment) describes the retired Amplify reader, which is kept only as a rollback origin until it is deleted. The live site's redirects are the key-value-store entries and edge function rules described above, not `reader.redirects`.
