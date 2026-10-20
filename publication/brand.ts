import type { SiteBrand } from "@anthusai/papyrus/lib/site-brand";
import { ANTH_US_THEME_PACK_TOKENS } from "@anthusai/papyrus/lib/site-stack";

export const anthUsBrand: SiteBrand = {
  id: "anth-us",
  appTitle: "Anthus",
  appDescription:
    "Anthus builds and operates self-aligning AI systems — custom models, agent harnesses, and evaluation loops with a human in the loop, grounded in 14 years of production operations.",
  mastheadTitle: "Anthus",
  mastheadSubtitle: "AI Solutions",
  backToHomeLabel: "Back to Anthus",
  articleTitleSuffix: "Anthus",
  placeholderByline: "Ryan Porter",
  defaultPresentation: "blog",
  textFont:
    '"Montserrat", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
  mastheadWordSplit: false,
  mastheadDateFormat: "formatted",
  mastheadSource: "brand",
  sectionLinkStrategy: "route",
  kanbusTheme: "newspaper-gothic",
  themePack: "anth-us",
  themeTokens: ANTH_US_THEME_PACK_TOKENS,
  renderer: { kind: "markus" },
  hosting: { kind: "amplify-ssr" },
  readerDeployment: {
    kind: "amplify-static",
    repository: "https://github.com/AnthusAI/Anth.us-Papyrus",
  },
  rootRoute: { kind: "newsroom" },
  newsroomBasePath: "",
  opsChrome: "app",
  corpusKey: "anth-us",
  steeringConfigPath: "corpora/anth-us-steering.yml",
  newsroomSectionsConfigPath: "corpora/anth-us-newsroom-sections.yml",
  analysisProfilesPath: "corpora/anth-us-analysis-profiles.yml",
  publicationName: "Anthus",
};
