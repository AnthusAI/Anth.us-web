import assert from "node:assert/strict";
import test from "node:test";
import { loadEdgeFunction } from "./load-edge-function.mjs";

const handler = loadEdgeFunction("viewer-response.js");

function respond(statusCode, headers) {
  const normalized = {};
  for (const [name, value] of Object.entries(headers)) normalized[name] = { value };
  return handler({ response: { statusCode, headers: normalized } });
}

test("html pages get the html lifetime and the previous content type", () => {
  const response = respond(200, { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=0, s-maxage=60, stale-while-revalidate=60" });
  assert.equal(response.headers["content-type"].value, "text/html");
  assert.equal(response.headers["cache-control"].value, "public, max-age=0, s-maxage=60, must-revalidate");
});

test("every other file gets the long shared-cache lifetime", () => {
  const response = respond(200, { "content-type": "image/png", "cache-control": "public, max-age=31536000, immutable" });
  assert.equal(response.headers["content-type"].value, "image/png");
  assert.equal(response.headers["cache-control"].value, "public, max-age=0, s-maxage=31536000");
});

test("xml and text keep the types the previous host sent", () => {
  assert.equal(respond(200, { "content-type": "application/xml" }).headers["content-type"].value, "text/xml");
  assert.equal(respond(200, { "content-type": "text/plain; charset=utf-8" }).headers["content-type"].value, "text/plain");
});

test("error pages carry no cache-control", () => {
  const response = respond(404, { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=0, s-maxage=60" });
  assert.equal(response.headers["cache-control"], undefined);
  assert.equal(response.headers["content-type"].value, "text/html");
});
