import assert from "node:assert/strict";
import test from "node:test";
import { loadEdgeFunction, requestFor } from "./load-edge-function.mjs";

const keyValues = {
  "/blog/ai/": "/tags/ai/",
  "/blog/machine%20learning/index.html": "/tags/machine-learning/",
  "/articles/plexus-classifier-lab/": "/articles/primus-classifier-lab/",
  "/platform/primus/": "https://primus.anth.us",
  "/platform/primus/index.html": "https://primus.anth.us",
};
const handler = loadEdgeFunction("viewer-request.js", keyValues);

async function outcome(uri) {
  const result = await handler(requestFor(uri));
  if (result.statusCode === 301) return { status: 301, location: result.headers.location.value };
  return { rewritten: result.uri };
}

test("an exact key redirects with the stored target", async () => {
  assert.deepEqual(await outcome("/blog/ai/"), { status: 301, location: "/tags/ai/" });
  assert.deepEqual(await outcome("/blog/machine%20learning/index.html"), { status: 301, location: "/tags/machine-learning/" });
});

test("pattern rules redirect any slug and keep the target shape", async () => {
  assert.deepEqual(await outcome("/blog/something/"), { status: 301, location: "/articles/something/" });
  assert.deepEqual(await outcome("/blog/something/index.html"), { status: 301, location: "/articles/something/" });
  assert.deepEqual(await outcome("/blog/page/3/"), { status: 301, location: "/articles/page/3/" });
  assert.deepEqual(await outcome("/blog/page/3/index.html"), { status: 301, location: "/articles/page/3/" });
});

test("an exact key wins over a pattern", async () => {
  assert.deepEqual(await outcome("/blog/ai/"), { status: 301, location: "/tags/ai/" });
});

test("the biased-decisions wildcard sends the rest of the path to the sub-domain", async () => {
  assert.deepEqual(await outcome("/biased-decisions"), { status: 301, location: "https://biased-decisions.anth.us/" });
  assert.deepEqual(await outcome("/biased-decisions/"), { status: 301, location: "https://biased-decisions.anth.us/" });
  assert.deepEqual(await outcome("/biased-decisions/x/y"), { status: 301, location: "https://biased-decisions.anth.us/x/y" });
  assert.deepEqual(await outcome("/biased-decisionsx"), { status: 301, location: "/biased-decisionsx/" });
});

test("a path with a trailing slash maps to its index document", async () => {
  assert.deepEqual(await outcome("/"), { rewritten: "/index.html" });
  assert.deepEqual(await outcome("/about/"), { rewritten: "/about/index.html" });
});

test("static hosting behaviour of the previous host is kept", async () => {
  assert.deepEqual(await outcome("/about"), { status: 301, location: "/about/" });
  assert.deepEqual(await outcome("/about.html"), { status: 301, location: "/about/" });
  assert.deepEqual(await outcome("/x.html"), { status: 301, location: "/x/" });
  assert.deepEqual(await outcome("/about/index.html"), { rewritten: "/about/index.html" });
  assert.deepEqual(await outcome("/index.html"), { rewritten: "/index.html" });
  assert.deepEqual(await outcome("/404.html"), { rewritten: "/404.html" });
  assert.deepEqual(await outcome("/404"), { rewritten: "/404.html" });
  assert.deepEqual(await outcome("/robots.txt"), { rewritten: "/robots.txt" });
  assert.deepEqual(await outcome("/assets/site/a%20b.png"), { rewritten: "/assets/site/a%20b.png" });
  assert.deepEqual(await outcome("/posts/page-3/"), { rewritten: "/posts/page-3/index.html" });
});

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const LEGACY_RULES = JSON.parse(
  readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../../web/legacy-redirect-rules.json"), "utf8"),
);
const RULES_THE_PREVIOUS_HOST_NEVER_MATCHED = ["/posts/page-<n>/"];

function filledIn(template) {
  return template.replace("<n>", "7").replace("<slug>", "sample-slug").replace("<*>", "x/y");
}

test("every pattern rule of the previous host that could match is reproduced", async () => {
  const patternRules = LEGACY_RULES.filter(
    (rule) => rule.status === "301" && rule.source.includes("<") && !RULES_THE_PREVIOUS_HOST_NEVER_MATCHED.includes(rule.source),
  );
  assert.equal(patternRules.length, 5);
  for (const rule of patternRules) {
    assert.deepEqual(
      await outcome(filledIn(rule.source)),
      { status: 301, location: filledIn(rule.target) },
      rule.source,
    );
  }
});

test("the rules the previous host never matched stay unmatched", async () => {
  for (const source of RULES_THE_PREVIOUS_HOST_NEVER_MATCHED) {
    const result = await outcome(filledIn(source));
    assert.ok(result.rewritten !== undefined, source);
  }
});

test("a solution with its own site redirects there, however its old URL is spelled", async () => {
  const site = { status: 301, location: "https://primus.anth.us" };
  assert.deepEqual(await outcome("/platform/primus/"), site);
  assert.deepEqual(await outcome("/platform/primus/index.html"), site);
  assert.deepEqual(await outcome("/platform/primus"), { status: 301, location: "/platform/primus/" });
});
