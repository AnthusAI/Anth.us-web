#!/usr/bin/env python3
"""Extract the old Gatsby og:image / twitter:image /static/... paths (PPY-5a64a2).

    bin/extract-legacy-og-images.py /Users/home/Projects/Anth.us-live/public

Writes web/legacy-og-images.json: {live page path: [old /static/... path, ...]}.
The live build is not available to Amplify, so the result is committed and
web/anthus_urls.py turns it into 301 rules. Re-run only if the live site changes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

TAG = re.compile(r"<meta\b[^>]*\b(?:property=\"og:image\"|name=\"twitter:image\")[^>]*>")
CONTENT = re.compile(r"\bcontent=\"([^\"]*)\"")


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    out: dict[str, list[str]] = {}
    for page in sorted(root.rglob("index.html")):
        path = "/" + page.parent.relative_to(root).as_posix() + "/"
        path = "/" if path == "/./" else path
        urls = []
        for tag in TAG.findall(page.read_text(encoding="utf-8", errors="replace")):
            m = CONTENT.search(tag)
            if not m:
                continue
            p = urlsplit(m.group(1).replace("&amp;", "&")).path
            if p.startswith("/static/") and p not in urls:
                urls.append(p)
        if urls:
            out[path] = urls
    dest = Path(__file__).resolve().parent.parent / "web" / "legacy-og-images.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(out)} pages, {sum(len(v) for v in out.values())} URLs -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
