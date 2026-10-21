"""Parity for anth.us: compare two "sites", each either a local projection (dir + redirect map, served through a simulated edge)
or a live crawl (crawl.py manifest).

    bin/parity.py A B REPORT.json [--allow allow.json] [--patterns patterns.json]
    A / B:  dir:<tree>,<redirects.json>   or   live:<crawl dir>

The simulated edge is a Python port of infra/edge/viewer-request.js + viewer-response.js (exact KVS lookup, pattern rules,
index rewrite, .html canonicalisation, response headers). Every URL of either side (tree keys, sitemap URLs, redirect
sources, links found in HTML, hostile URLs) is compared: status, redirect chain target, content type, cache control,
normalised DOM, head metadata, sitemap URL set, robots.txt, feeds, 404.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

import lxml.html

HERE = Path(__file__).resolve().parent
HOSTILE = ["/", "/404.html", "/404", "/nope-not-here/", "/index.html", "/articles/index.html", "/about.html", "/about", "/articles", "/blog/x/", "/blog/x/index.html",
           "/blog/page/2/", "/posts/page-2/", "/biased-decisions/", "/biased-decisions/anything/", "/robots.txt", "/sitemap.xml", "/sitemap-index.xml", "/sitemap-0.xml",
           "/feed.xml", "/rss.xml", "/atom.xml", "/favicon.ico", "/llms.txt", "/articles/?drafts", "/tags/", "/tags/nope/", "/articles/page/2/", "/articles/page/999/"]

DEFAULT_PATTERNS = [
    (r"^/blog/page/([^/]+)/$", "/articles/page/$1/"),
    (r"^/blog/page/([^/]+)/index\.html$", "/articles/page/$1/"),
    (r"^/blog/([^/]+)/$", "/articles/$1/"),
    (r"^/blog/([^/]+)/index\.html$", "/articles/$1/"),
    (r"^/biased-decisions(?:/(.*))?$", "https://biased-decisions.anth.us/$1"),
]


# ------------------------------------------------------------------ simulated edge
def content_type_for(key: str) -> str:
    from papyrus_content.projection.writers import content_type_for as core

    return core(key)


def response_content_type(stored: str) -> str:
    base = stored[: -len("; charset=utf-8")] if stored.endswith("; charset=utf-8") else stored
    return "text/xml" if base == "application/xml" else base


def cache_control(content_type: str) -> str:
    return "public, max-age=0, s-maxage=60, must-revalidate" if content_type == "text/html" else "public, max-age=0, s-maxage=31536000"


class LocalSite:
    kind = "dir"

    def __init__(self, tree_dir: Path, redirects: dict, patterns=None, served_html=("/404.html",), canonicalise_html=True):
        self.tree = {p.relative_to(tree_dir).as_posix(): p.read_bytes() for p in sorted(tree_dir.rglob("*")) if p.is_file()}
        self.redirects = redirects
        self.patterns = [(re.compile(p), t) for p, t in (patterns or DEFAULT_PATTERNS)]
        self.served_html = served_html
        self.canonicalise_html = canonicalise_html

    def request_paths(self):
        from papyrus_content.projection.writers import request_paths_for_key

        out = set(self.redirects)
        for key in self.tree:
            out.add(request_paths_for_key(key)[0])
        return out

    def get(self, uri: str) -> dict:
        path = uri.split("?", 1)[0]
        if path in self.redirects:
            return {"status": 301, "location": self.redirects[path]}
        for pattern, target in self.patterns:
            m = pattern.search(path)
            if m:
                captured = m.group(1) if m.lastindex and m.group(1) is not None else ""
                return {"status": 301, "location": target.replace("$1", captured)}
        key = None
        if path.endswith("/"):
            key = path.lstrip("/") + "index.html"
        elif path == "/404":
            key = "404.html"
        else:
            last = path.rsplit("/", 1)[-1]
            if "." in last:
                is_index = path == "/index.html" or path.endswith("/index.html")
                if self.canonicalise_html and path.endswith(".html") and not is_index and path not in self.served_html:
                    return {"status": 301, "location": path[: -len(".html")] + "/"}
                key = path.lstrip("/")
            else:
                return {"status": 301, "location": path + "/"}
        if key in self.tree:
            ctype = response_content_type(content_type_for(key))
            return {"status": 200, "content_type": ctype, "cache_control": cache_control(ctype), "body": self.tree[key]}
        return {"status": 404, "body": self.tree.get("404.html", b""), "content_type": "text/html", "cache_control": None}


class LiveSite:
    kind = "live"

    def __init__(self, crawl_dir: Path):
        self.dir = crawl_dir
        self.manifest = json.loads((crawl_dir / "manifest.json").read_text())

    def request_paths(self):
        return set(self.manifest)

    def get(self, uri: str) -> dict:
        m = self.manifest.get(uri)
        if m is None or m["status"] == 0:
            return {"status": 0}
        h = m.get("headers", {})
        out = {"status": m["status"], "content_type": h.get("content-type", "").split(";")[0] or None, "cache_control": h.get("cache-control")}
        if "location" in h:
            out["location"] = h["location"]
        out["body"] = (self.dir / m["file"]).read_bytes()
        return out


# ------------------------------------------------------------------ normalisation
def _squash(text):
    return re.sub(r"\s+", " ", text or "").strip()


TOKEN = re.compile(r"\?v=[0-9a-f]{8,16}")


def _canon(element, out):
    if not isinstance(element.tag, str):
        return
    attrs = {}
    for name, value in element.attrib.items():
        if name in ("href", "src", "srcset", "content", "style"):
            value = TOKEN.sub("", value)
        attrs[name] = value
    out.append("<" + element.tag + "".join(f' {k}="{v}"' for k, v in sorted(attrs.items())) + ">")
    if element.text and _squash(element.text):
        out.append(re.sub(r'__markusAssetVersion = "[0-9a-f]+"', '__markusAssetVersion = "<t>"', TOKEN.sub("", _squash(element.text))))
    for child in element:
        _canon(child, out)
        if child.tail and _squash(child.tail):
            out.append(_squash(child.tail))
    out.append(f"</{element.tag}>")


def dom_lines(html: bytes) -> list[str]:
    document = lxml.html.fromstring(html)
    body = document.find("body")
    lines: list[str] = []
    _canon(body, lines)
    return lines


def head_meta(html: bytes) -> dict:
    document = lxml.html.fromstring(html)
    head = document.find("head")
    meta = defaultdict(list)
    meta["title"].append(_squash(head.findtext("title") or ""))
    for tag in head.iterchildren():
        if tag.tag == "meta":
            name = tag.get("name") or tag.get("property")
            if name and tag.get("content") is not None:
                meta[name].append(TOKEN.sub("", tag.get("content")))
            elif tag.get("charset"):
                meta["@charset"].append(tag.get("charset"))
        elif tag.tag == "link":
            rel = tag.get("rel")
            meta[f"link:{rel}" + (f":{tag.get('type')}" if tag.get("type") else "")].append(TOKEN.sub("", tag.get("href") or ""))
        elif tag.tag == "script":
            if tag.get("type") == "application/ld+json":
                meta["ld+json"].append(json.loads(tag.text))
            else:
                meta["script"].append(TOKEN.sub("", tag.get("src") or _squash(tag.text)[:80]))
        elif tag.tag == "style":
            meta["style"].append(_squash(tag.text)[:200])
    return dict(meta)


def _ld_equal(a, b, ignore_if_empty, added_keys):
    def norm(items, other):
        out = []
        for item in items:
            out.append({k: v for k, v in item.items() if not (k in ignore_if_empty and not v) and not (k in added_keys and k not in other)})
        return out
    return norm(a, b[0] if b else {}) == norm(b, a[0] if a else {}) if len(a) == len(b) else False


def sitemap_urls(data: bytes) -> list[str]:
    root = ElementTree.fromstring(data)
    return sorted(loc.text for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"))


def parse_site(spec: str, patterns):
    kind, _, rest = spec.partition(":")
    if kind == "dir":
        tree, redirects = rest.split(",")
        return LocalSite(Path(tree), json.loads(Path(redirects).read_text()), patterns)
    return LiveSite(Path(rest))


def main():
    a_spec, b_spec, report_path = sys.argv[1:4]
    allow = json.loads(Path(sys.argv[sys.argv.index("--allow") + 1]).read_text()) if "--allow" in sys.argv else {}
    patterns_b = None
    if "--patterns-b" in sys.argv:
        patterns_b = [(r["pattern"], r["to"]) for r in json.loads(Path(sys.argv[sys.argv.index("--patterns-b") + 1]).read_text())]
    a = parse_site(a_spec, None)
    b = parse_site(b_spec, patterns_b)
    IGNORE = ('/assets/content/', '/assets/responsive/')
    paths = {p for p in set(HOSTILE) | a.request_paths() | b.request_paths() if p and not p.startswith(IGNORE)}
    for site in (a, b):
        for path in ("/sitemap-index.xml", "/sitemap-0.xml", "/sitemap.xml"):
            r = site.get(path)
            if r["status"] == 200:
                for url in sitemap_urls(r["body"]):
                    paths.add(urlsplit(url).path)
    rows, blocking, allowed, category = [], [], Counter(), Counter()
    allowed_diffs = Counter()
    allowed_paths = allow.get("paths", {})
    for path in sorted(paths):
        ra, rb = a.get(path), b.get(path)
        row = {"path": path, "a": ra.get("status"), "b": rb.get("status")}
        reason = allowed_paths.get(path)
        problems = []
        if ra["status"] != rb["status"] or ra.get("location") != rb.get("location"):
            problems.append(f"status/redirect {ra.get('status')} {ra.get('location')} vs {rb.get('status')} {rb.get('location')}")
        elif ra["status"] in (200, 404):
            if ra.get("content_type") != rb.get("content_type"):
                problems.append(f"content-type {ra.get('content_type')} vs {rb.get('content_type')}")
            if ra.get("cache_control") != rb.get("cache_control"):
                problems.append(f"cache-control {ra.get('cache_control')} vs {rb.get('cache_control')}")
            if ra.get("content_type") == "text/html" and ra.get("body") and rb.get("body"):
                try:
                    if dom_lines(ra["body"]) != dom_lines(rb["body"]):
                        problems.append("normalised DOM differs")
                    ha, hb = head_meta(ra["body"]), head_meta(rb["body"])
                    for k in sorted(set(ha) | set(hb)):
                        if ha.get(k) != hb.get(k):
                            added_reason = allow.get("head_added", {}).get(k)
                            changed_reason = allow.get("head_changed", {}).get(k)
                            if k == "ld+json" and ha.get(k) and hb.get(k) and _ld_equal(ha[k], hb[k], allow.get("ld_ignore_keys_if_empty", ()), allow.get("ld_added_keys", ())):
                                allowed_diffs[allow.get("ld_reason", "json-ld")] += 1
                            elif added_reason and not ha.get(k):
                                allowed_diffs[added_reason] += 1
                            elif changed_reason:
                                allowed_diffs[changed_reason] += 1
                            else:
                                problems.append(f"head {k}: {str(ha.get(k))[:120]} -> {str(hb.get(k))[:120]}")
                except Exception as error:  # noqa
                    problems.append(f"unparseable: {error}")
            elif ra["status"] == 200 and ra.get("body") != rb.get("body"):
                if path.endswith((".xml", ".txt")) and path not in ("/robots.txt",):
                    if path.endswith(".xml") and "sitemap" in path:
                        if sitemap_urls(ra["body"]) != sitemap_urls(rb["body"]) :
                            problems.append("sitemap URL set differs")
                        else:
                            strip = lambda b: re.sub(rb' xmlns:\w+="[^"]+"', b"", b)
                            if strip(ra["body"]) == strip(rb["body"]):
                                allowed_diffs[allow.get("sitemap_reason", "sitemap namespaces")] += 1
                            else:
                                problems.append("sitemap body differs beyond namespace declarations")
                    elif TOKEN.sub("", ra["body"].decode("utf-8", "replace")) != TOKEN.sub("", rb["body"].decode("utf-8", "replace")):
                        problems.append("text body differs")
                else:
                    problems.append("body bytes differ")
        category["compared"] += 1
        if problems:
            row["problems"] = problems
            if reason:
                allowed[f"{reason}"] += 1
                row["allowed"] = reason
            else:
                blocking.append(f"{path}: " + "; ".join(problems))
        rows.append(row)
    summary = {"urls compared": len(rows), "blocking differences": len(blocking), "allow-listed URLs": sum(allowed.values()), "allow-listed differences": dict(allowed_diffs)}
    Path(report_path).write_text(json.dumps({"summary": summary, "allowed": dict(allowed), "blocking": blocking, "rows": rows}, indent=1, default=str))
    print(json.dumps(summary))
    for line in blocking[:40]:
        print("  ", line[:300])
    if len(blocking) > 40:
        print("   ...", len(blocking) - 40, "more")


if __name__ == "__main__":
    main()
