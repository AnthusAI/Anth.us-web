"""Crawl a site without following redirects; record status, selected headers, body.

bin/crawl.py ORIGIN OUTDIR [--extra FILE_OF_PATHS] [--host-header HOST]
Paths: sitemap(s) from robots.txt/sitemap-index.xml, internal links found in HTML (one level of closure), extra file, hostile list.
"""
import hashlib, json, re, sys, time, urllib.request, urllib.error, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOSTILE = ["/", "/404.html", "/nope-not-here/", "/index.html", "/articles/index.html", "/about.html", "/about", "/articles", "/blog/x/", "/blog/page/2/", "/posts/page-2/",
           "/biased-decisions/anything/", "/robots.txt", "/sitemap.xml", "/sitemap-index.xml", "/sitemap-0.xml", "/feed.xml", "/rss.xml", "/atom.xml", "/favicon.ico", "/llms.txt", "/articles/?drafts"]
KEEP = ("content-type", "cache-control", "location", "content-encoding", "x-robots-tag", "link", "content-security-policy", "strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def fetch(origin, path):
    for attempt in range(5):
        meta, body = fetch_once(origin, path)
        if meta["status"] != 0:
            return meta, body
        time.sleep(1 + attempt)
    return meta, body


def fetch_once(origin, path):
    url = origin + urllib.parse.quote(path, safe="/%?=&:@~,;+!$'()*-._")
    request = urllib.request.Request(url, headers={"User-Agent": "papyrus-parity/1", "Accept-Encoding": "identity"})
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    except Exception as error:  # noqa
        return {"path": path, "status": 0, "error": str(error)}, b""
    body = response.read()
    headers = {k.lower(): v for k, v in response.headers.items()}
    return {"path": path, "status": response.status if hasattr(response, "status") else response.code, "headers": {k: headers[k] for k in KEEP if k in headers}, "sha": hashlib.sha256(body).hexdigest(), "size": len(body)}, body


def links(body, origin, path):
    out = set()
    for match in re.finditer(rb'(?:href|src)="([^"#]+)', body):
        value = match.group(1).decode("utf-8", "replace")
        absolute = urllib.parse.urljoin(origin + path, value)
        parsed = urllib.parse.urlsplit(absolute)
        if parsed.netloc == urllib.parse.urlsplit(origin).netloc:
            out.add(parsed.path + (("?" + parsed.query) if parsed.query else ""))
    return out


def main():
    origin, outdir = sys.argv[1].rstrip("/"), Path(sys.argv[2])
    extra = []
    if "--extra" in sys.argv:
        extra = [line.strip() for line in Path(sys.argv[sys.argv.index("--extra") + 1]).read_text().splitlines() if line.strip()]
    outdir.mkdir(parents=True, exist_ok=True)
    seen = {}
    todo = set(HOSTILE) | set(extra)
    meta, body = fetch(origin, "/sitemap-index.xml")
    for loc in re.findall(rb"<loc>([^<]+)</loc>", body):
        sm = urllib.parse.urlsplit(loc.decode()).path
        todo.add(sm)
        m2, b2 = fetch(origin, sm)
        for l2 in re.findall(rb"<loc>([^<]+)</loc>", b2):
            todo.add(urllib.parse.urlsplit(l2.decode()).path)
    rounds = 0
    while todo and rounds < 3:
        rounds += 1
        batch = sorted(todo - set(seen))
        todo = set()
        with ThreadPoolExecutor(16) as pool:
            for (m, b), path in zip(pool.map(lambda p: fetch(origin, p), batch), batch):
                seen[path] = m
                name = hashlib.sha1(path.encode()).hexdigest()[:16]
                (outdir / name).write_bytes(b)
                m["file"] = name
                if m["status"] == 200 and "text/html" in m.get("headers", {}).get("content-type", ""):
                    todo |= links(b, origin, path)
        print("round", rounds, "fetched", len(batch), file=sys.stderr)
    (outdir / "manifest.json").write_text(json.dumps(seen, indent=1, sort_keys=True))
    from collections import Counter
    print(Counter(m["status"] for m in seen.values()))


main()
