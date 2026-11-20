// edge-diff.mjs OLD.js NEW.js REDIRECTS.json URLS.txt -> compares two viewer-request functions over every URI
import { readFileSync } from "node:fs";
const [oldFile, newFile, redirectsFile, urlsFile] = process.argv.slice(2);
const kv = JSON.parse(readFileSync(redirectsFile, "utf8"));
const load = (file) => {
  const source = readFileSync(file, "utf8").replace(/^import cf from "cloudfront";\n/, "");
  const cf = { kvs: () => ({ get: async (k) => { if (!(k in kv)) throw new Error("KeyNotFound"); return kv[k]; } }) };
  return new Function("cf", `${source}\nreturn handler;`)(cf);
};
const a = load(oldFile), b = load(newFile);
const out = async (h, uri) => {
  const r = await h({ request: { uri, method: "GET", headers: {} } });
  return r.statusCode ? `${r.statusCode} ${r.headers.location.value}` : `rewrite ${r.uri}`;
};
const uris = new Set(readFileSync(urlsFile, "utf8").split("\n").filter(Boolean));
for (const base of ["/", "/about", "/about/", "/about.html", "/x.y", "/a/b/c", "/a/b/c/", "/a/b.c/d", "/blog", "/blog/", "/blog/x", "/blog/x/", "/blog/x.html", "/blog/x/index.html", "/blog/page/", "/blog/page/2", "/blog/page/2/", "/blog/page/2/index.html", "/biased-decisions", "/biased-decisions/", "/biased-decisionsx", "/biased-decisions/a/b/c", "/404", "/404/", "/404.html", "/index.html", "/index", "/a/index.html", "/a/index", "/myindex.html", "/%20", "/a%20b", "/a%20b/", "/ünï/", "/.well-known/x", "/.hidden", "/a/.hidden", "/a/b..c", "//", "//x", "/x//y", "/robots.txt", "/sitemap-index.xml", "/assets/site/a%20b.png", "/_plugins/papyrus-search.js", "/articles/x", "/articles/x/index.html", "/articles/x.html", "/posts/page-3/", "/posts/page-3", "/tags/ai", "/tags/c.s/"]) uris.add(base);
let diffs = 0, n = 0;
for (const uri of [...uris].sort()) {
  n++;
  const [x, y] = [await out(a, uri), await out(b, uri)];
  if (x !== y) { diffs++; console.log(JSON.stringify(uri), "|", x, "|", y); }
}
console.log(`${n} URIs, ${diffs} differences`);
