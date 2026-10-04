#!/usr/bin/env python3
"""Post-deploy guard checker (PPY-f1f0a8 / PPY-0ba000). Read-only HTTP GETs.

    bin/check-guards.py <base-url> --expect production|guarded [--no-sitemap]

Verifies, against a live host: the robots meta on a few pages, robots.txt,
the absence of an X-Robots-Tag header (production), the canonical origin, and that
/sitemap-index.xml and /sitemap-0.xml answer 200 on the expected origin.

* guarded:    noindex meta + staging note on every sampled page, robots.txt
              "Disallow: /", canonical origin == the base URL's origin. No
              X-Robots-Tag header is required (staging uses meta + robots.txt).
* production: no noindex, no staging note, robots.txt allows and names the
              sitemap, X-Robots-Tag ABSENT, canonical origin == https://anth.us.

Exit 0 only if every check passes. --no-sitemap skips the sitemap checks (for a
host still serving a build from before PPY-0ba000).
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

PRODUCTION_ORIGIN = "https://anth.us"
NOTE_MARKER = "Staging preview of the Papyrus/Markus port of anth.us."
SAMPLE_PATHS = ["/", "/about/", "/platform/", "/404.html"]
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "anthus-check-guards/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.headers, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        return 0, {}, f"{exc.reason}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base_url")
    ap.add_argument("--expect", required=True, choices=["production", "guarded"])
    ap.add_argument("--no-sitemap", action="store_true")
    args = ap.parse_args()

    parts = urlsplit(args.base_url)
    base = f"{parts.scheme}://{parts.netloc}"
    prod = args.expect == "production"
    origin = PRODUCTION_ORIGIN if prod else base
    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail and not ok else ""))
        if not ok:
            failures.append(label)

    print(f"check-guards {base} --expect {args.expect} (canonical origin {origin})")

    # robots.txt
    status, _, body = get(base + "/robots.txt")
    lines = [ln.strip() for ln in body.splitlines()]
    check(status == 200, "robots.txt returns 200", f"HTTP {status}")
    if prod:
        check("Allow: /" in lines and "Disallow: /" not in lines, "robots.txt allows crawling", repr(body[:120]))
        check(any(ln.startswith("Sitemap: " + PRODUCTION_ORIGIN + "/") for ln in lines),
              "robots.txt has a Sitemap: line on https://anth.us", repr(body[:160]))
    else:
        check("Disallow: /" in lines and "Allow: /" not in lines, "robots.txt disallows /", repr(body[:120]))

    # pages
    for path in SAMPLE_PATHS:
        status, headers, html = get(base + path)
        tag = f"{path}"
        if path == "/404.html" and status != 200:
            continue  # custom-rule 404 handling varies; sampled only when served
        check(status == 200, f"{tag} returns 200", f"HTTP {status}")
        metas = [m for m in re.findall(r"<meta\b[^>]*\bname=[\"']robots[\"'][^>]*>", html, re.I)]
        noindex = any("noindex" in m.lower() for m in metas)
        check(noindex != prod, f"{tag} robots meta {'absent' if prod else 'noindex'}", repr(metas))
        check((NOTE_MARKER in html) != prod, f"{tag} staging note {'absent' if prod else 'present'}")
        xrt = headers.get("X-Robots-Tag") if headers else None
        if prod:
            check(not xrt, f"{tag} no X-Robots-Tag header", f"got {xrt!r}")
        canon = re.findall(r"<link\b[^>]*\brel=[\"']canonical[\"'][^>]*>", html, re.I)
        hrefs = [m.group(1) for c in canon if (m := re.search(r"href=[\"']([^\"']*)", c))]
        check(len(hrefs) == 1 and (hrefs[0] == origin or hrefs[0].startswith(origin + "/")),
              f"{tag} canonical on {origin}", repr(hrefs))

    # sitemaps
    if not args.no_sitemap:
        status, _, body = get(base + "/sitemap-index.xml")
        locs: list[str] = []
        try:
            locs = [e.text or "" for e in ET.fromstring(body).findall("s:sitemap/s:loc", NS)]
        except ET.ParseError:
            pass
        check(status == 200 and locs == [origin + "/sitemap-0.xml"],
              f"/sitemap-index.xml 200 and points at {origin}/sitemap-0.xml", f"HTTP {status} locs={locs}")
        status, _, body = get(base + "/sitemap-0.xml")
        urls: list[str] = []
        try:
            urls = [e.text or "" for e in ET.fromstring(body).findall("s:url/s:loc", NS)]
        except ET.ParseError:
            pass
        bad = [u for u in urls if not (u == origin or u.startswith(origin + "/"))]
        check(status == 200 and bool(urls) and not bad,
              f"/sitemap-0.xml 200, {len(urls)} URLs, all on {origin}", f"HTTP {status} off-origin={bad[:2]}")

    print("OK" if not failures else f"MISMATCH: {len(failures)} check(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
