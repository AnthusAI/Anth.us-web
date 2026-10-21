import { defineSite } from "@anthusai/papyrus/define-site";
import { anthUsBrand } from "./publication/brand";

const defaultCognitoDomainPrefix = "papyrus-anth-us-cms";
const defaultRedirectUrls = ["http://localhost:3001/"];

function readNonEmptyEnvironmentValue(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value ? value : undefined;
}

const cognitoDomainPrefixFromEnvironment = readNonEmptyEnvironmentValue("PAPYRUS_COGNITO_DOMAIN_PREFIX");
const redirectUrlsFromEnvironment = readNonEmptyEnvironmentValue("PAPYRUS_OAUTH_REDIRECT_URLS");

export const resolvedAuthConfiguration = {
  cognitoDomainPrefix: cognitoDomainPrefixFromEnvironment ?? defaultCognitoDomainPrefix,
  applyCognitoDomainPrefix: readNonEmptyEnvironmentValue("PAPYRUS_APPLY_COGNITO_DOMAIN_PREFIX") === "true",
  redirectUrls: redirectUrlsFromEnvironment
    ? redirectUrlsFromEnvironment.split(",").map((url) => url.trim()).filter((url) => url.length > 0)
    : defaultRedirectUrls,
};

export default defineSite({
  brands: [anthUsBrand],
  defaultBrand: "anth-us",
  backend: {
    brandId: "anth-us",
    auth: resolvedAuthConfiguration,
    publication: {
      kind: "s3-projection",
      staticDir: "web",
      edgeDistributionArn: "arn:aws:cloudfront::712236451410:distribution/E3UMOOJRMY7FK7",
      cache: { htmlSMaxAgeSeconds: 60 },
      reprojectOnDeploy: true,
    },
    stagingBuild: { enabled: true },
    features: {
      consoleResponder: false,
      inboundEmail: false,
      slack: false,
      storageBackups: false,
    },
  },
});
