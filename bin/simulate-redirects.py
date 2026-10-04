#!/usr/bin/env python3
"""Replay a URL list (e.g. production's sitemap) against the generated Amplify
redirect rules and the built site, with Amplify's matching semantics.

For each URL it reports one of:

* ``served``      -- a page exists at that path and no rule shadows it
* ``redirect``    -- one 301 hop to a page that exists
* ``chain``       -- the target is itself redirected (a build failure)
* ``dead-target`` -- the rule's target is not a page (a build failure)
* ``shadowed``    -- a rule matches a path that is also a real page (a failure)
* ``404``         -- no rule and no page (production URL the port does not have)

Semantics, measured against Amplify rather than assumed (see anthus_urls.py):
the first matching rule wins and beats the filesystem; ``<name>`` matches one
path segment (mid-segment allowed) and substitutes into the target; sources
match case-sensitively against the percent-encoded path; the final catch-all
``/<*>`` is the 404 document.

    python3 bin/simulate-redirects.py --sitemap sitemap-0.xml
    python3 bin/simulate-redirects.py --urls urls.txt --dist web/dist-papyrus
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent


def compile_rule(rule: dict):
    source = rule["source"]
    if source == "/<*>":
        return None
    pattern = re.escape(source)
    names = re.findall(r"<(\w+)>", source)
    pattern = re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", pattern)
    return re.compile("^" + pattern + "$"), names


def substitute(target: str, match: re.Match) -> str:
    return re.sub(r"<(\w+)>", lambda m: match.group(m.group(1)), target)


def exists(dist: Path, path: str) -> bool:
    path = unquote(path)
    if path.endswith("/"):
        return (dist / path.lstrip("/") / "index.html").is_file()
    return (dist / path.lstrip("/")).is_file()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default=str(ROOT / "web" / "custom-rules.json"))
    ap.add_argument("--dist", default=str(ROOT / "web" / "dist-papyrus"))
    ap.add_argument("--sitemap")
    ap.add_argument("--urls")
    ap.add_argument("--show", type=int, default=40)
    args = ap.parse_args()

    if args.sitemap:
        text = Path(args.sitemap).read_text(encoding="utf-8")
        urls = re.findall(r"<loc>([^<]+)</loc>", text)
    else:
        urls = [u.strip() for u in Path(args.urls).read_text().split() if u.strip()]
    rules = [r for r in json.loads(Path(args.rules).read_text()) if r["status"] == "301"]
    compiled = [(r, compile_rule(r)) for r in rules]
    dist = Path(args.dist)

    def apply(path: str):
        for rule, comp in compiled:
            if comp is None:
                continue
            match = comp[0].match(path)
            if match:
                return rule, substitute(rule["target"], match)
        return None

    buckets: dict[str, list[str]] = {}
    for url in urls:
        path = urlsplit(url).path or "/"
        hit = apply(path)
        if hit is None:
            kind = "served" if exists(dist, path) else "404"
            detail = path
        else:
            _, target = hit
            if exists(dist, path):
                kind, detail = "shadowed", f"{path} -> {target}"
            elif apply(target) is not None:
                kind, detail = "chain", f"{path} -> {target}"
            elif not exists(dist, target):
                kind, detail = "dead-target", f"{path} -> {target}"
            else:
                kind, detail = "redirect", f"{path} -> {target}"
        buckets.setdefault(kind, []).append(detail)

    print(f"{len(urls)} URLs against {len(rules)} rules and {dist}")
    for kind in ("served", "redirect", "404", "chain", "dead-target", "shadowed"):
        items = buckets.get(kind, [])
        print(f"  {kind:12s} {len(items)}")
        if kind in ("404", "chain", "dead-target", "shadowed"):
            for item in items[: args.show]:
                print(f"      {item}")
    bad = sum(len(buckets.get(k, [])) for k in ("chain", "dead-target", "shadowed"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
