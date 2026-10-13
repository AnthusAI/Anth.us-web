import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const EDGE_DIRECTORY = resolve(dirname(fileURLToPath(import.meta.url)), "../../infra/edge");

export function loadEdgeFunction(fileName, keyValues = {}) {
  const source = readFileSync(resolve(EDGE_DIRECTORY, fileName), "utf8").replace(/^import cf from "cloudfront";\n/, "");
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
