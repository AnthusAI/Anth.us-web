import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPOSITORY = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const EDGE_DIRECTORY = resolve(REPOSITORY, "infra/edge");
const PAPYRUS_INFRA = resolve(REPOSITORY, "node_modules/@anthusai/papyrus/bin/papyrus-infra.mjs");

/** The viewer-request function is Papyrus core's, with the rules of web/projection.json compiled in. */
function edgeFunctionSource(fileName) {
  if (fileName === "viewer-request.js") {
    return execFileSync("node", [PAPYRUS_INFRA, "compile-edge-function", "--static-dir", resolve(REPOSITORY, "web")], { encoding: "utf8" });
  }
  return readFileSync(resolve(EDGE_DIRECTORY, fileName), "utf8");
}

export function loadEdgeFunction(fileName, keyValues = {}) {
  const source = edgeFunctionSource(fileName).replace(/^import cf from "cloudfront";\n/, "");
  const cf = {
    kvs: () => ({
      get: async (key) => {
        if (!(key in keyValues)) throw new Error("KeyNotFound");
        return keyValues[key];
      },
    }),
  };
  return new Function("cf", `${source}\nreturn handler;`)(cf);
}

export function requestFor(uri) {
  return { request: { uri, method: "GET", headers: {} } };
}
