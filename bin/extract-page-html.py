#!/usr/bin/env python3
r"""Generate ``web/anthus_page_html.py`` from production Anth.us HTML.

The production stylesheet targets the production DOM, so the bespoke static
pages of the port (about, ai-solutions, ryan, 404, engage, reading, research,
decision-models) reproduce production's ``<main>`` inner HTML verbatim. This
script lifts that HTML out of real production pages and writes it into a
Python module as plain string constants plus small functions that splice the
dynamic lists ("holes") back in. Nothing is hand-copied.

REFERENCE PAGES
    --live-dir DIR (default web/reference/live) -> raw responses of
                   https://anth.us/<page> saved by ``--fetch`` (0.5 s apart):
                   about ai-solutions ryan 404 engage decision-models reading
                   research (.html).  This is the authority: it is what
                   production serves.
    --anthus PATH  (default ../Anth.us-live) -> PATH/public/, a Gatsby build of
                   the exact commit Amplify deployed.  Used only for the
                   cross-check: every page's <main> in the saved live copy must
                   equal the build's <main> (base64 blur placeholders aside),
                   which proves the build reference == production.  The check
                   is skipped (and reported) when no build is present.

TRANSFORM (static regions only -- holes are cut out first)
    1. <main ...> inner HTML = text between the <main> open tag and </main>.
    2. Hole spans are found per page (see PAGES): top-level <ul> elements
       whose open tag starts with a given prefix, matched to their </ul> by
       <ul>/</ul> depth counting (the lists contain nested plain <ul>s), and
       runs of *adjacent* such <ul>s are merged into one hole.
    3. Static regions must contain no <script>, <noscript>,
       gatsby-image-wrapper or /static/ URL (asserted). Plain
       <img src="/assets/images/X"> keeps its markup; only src is rewritten
       to /assets/site/X (X must exist in web/assets/site/).
    4. React text separators are removed with a plain
       str.replace('<!-- -->', '') -- surrounding whitespace is untouched.
    Everything else (hrefs, classes, inline styles, entities, <mark>) is
    byte-verbatim.

USAGE
    python3 bin/extract-page-html.py                 # regenerate + verify
    python3 bin/extract-page-html.py --fetch         # refresh live refs first
    python3 bin/extract-page-html.py --css-report    # also list classes the
                                                     # pages use that are
                                                     # missing from
                                                     # web/css/anthus-theme.css
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "web" / "anthus_page_html.py"
SITE_ASSETS = REPO / "web" / "assets" / "site"
THEME_CSS = REPO / "web" / "css" / "anthus-theme.css"
LIVE_ORIGIN = "https://anth.us"

INDEX_LIST = '<ul class="index-module--list--fb407'
BLOG_LIST = '<ul class="blog"'
GRID_LIST = '<ul class="platform-module--grid--279c8"'

# name -> dict(path=<file in --live-dir>, build=<file in <anthus>/public>,
#              url, func, holes=[(hole name, ul prefix), ...])
# Holes are assigned, in document order, to the merged runs of matching <ul>s.
PAGES: dict[str, dict] = {
    "about": dict(path="about.html", build="about/index.html", url="/about/",
                  func="about_html", holes=[]),
    "ai-solutions": dict(path="ai-solutions.html",
                         build="ai-solutions/index.html",
                         url="/ai-solutions/", func="ai_solutions_html",
                         holes=[("engagements", BLOG_LIST),
                                ("projects", GRID_LIST),
                                ("integrations", INDEX_LIST)]),
    "ryan": dict(path="ryan.html", build="ryan/index.html", url="/ryan/",
                 func="ryan_html",
                 holes=[("portfolio", INDEX_LIST),
                        ("integrations", INDEX_LIST)]),
    "404": dict(path="404.html", build="404.html", url="/404.html",
                func="not_found_html", holes=[]),
    "engage": dict(path="engage.html", build="engage/index.html",
                   url="/engage/", func="engage_html", holes=[]),
    "reading": dict(path="reading.html", build="reading/index.html",
                    url="/reading/", func="reading_html",
                    holes=[("featured", BLOG_LIST), ("earlier", GRID_LIST)]),
    "research": dict(path="research.html", build="research/index.html",
                     url="/research/", func="research_html",
                     holes=[("featured", BLOG_LIST), ("earlier", GRID_LIST)]),
    "decision-models": dict(path="decision-models.html",
                            build="decision-models/index.html",
                            url="/decision-models/",
                            func="decision_models_html", holes=[]),
    "benchmarks": dict(path="benchmarks.html",
                       build="benchmarks/index.html",
                       url="/benchmarks/",
                       func="benchmarks_html", holes=[]),
}

HOLE_DOCS = {
    ("ai-solutions", "engagements"):
        "<ul class=\"blog\"> under <h2>Engagements</h2>: the client-work "
        "posts (the same blog-post-preview items as /blog/ featured lists, "
        "<li class=\"clear-float\"> with a gatsby-image className=\"featured\")",
    ("ai-solutions", "projects"):
        "<ul class=\"platform-module--grid--279c8\"> under <h2>Projects and "
        "examples</h2>: research-cards.jsx cards (platform-module--card, "
        "research-cards-module--imageLink headline image) for the smaller "
        "builds/spinoffs/worked examples",
    ("ai-solutions", "integrations"):
        "the index-module--list <ul> under <h2>Integrations</h2> (Paytronix "
        "... Marketo)",
    ("ryan", "portfolio"):
        "TWO adjacent index-module--list <ul>s under <h2>Portfolio</h2>: the "
        "featured set (B0rd ... Call Criteria, smallImageList) immediately "
        "followed by the portfolio set (Primus ... Checkout Driver)",
    ("ryan", "integrations"):
        "the index-module--list <ul> under <h2>Integrations</h2>",
    ("reading", "featured"):
        "<ul class=\"blog\"> of the 4 newest published posts tagged "
        "'reading' (collection.jsx featured items)",
    ("reading", "earlier"):
        "<ul class=\"platform-module--grid--279c8\"> of the next 8 "
        "(research-cards.jsx)",
    ("research", "featured"):
        "<ul class=\"blog\"> of the 4 newest published posts tagged "
        "'research' (collection.jsx featured items)",
    ("research", "earlier"):
        "<ul class=\"platform-module--grid--279c8\"> of the next 8 "
        "(research-cards.jsx)",
}


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def main_inner(doc: str) -> str:
    m = re.search(r"<main(?:\s[^>]*)?>", doc)
    if not m or doc.count("<main") != 1:
        raise SystemExit("expected exactly one <main>")
    end = doc.index("</main>", m.end())
    return doc[m.end():end]


def ul_end(s: str, start: int) -> int:
    """Index just past the </ul> matching the <ul at ``start``."""
    depth = 0
    for m in re.compile(r"<ul[\s>]|</ul>").finditer(s, start):
        if m.group(0) == "</ul>":
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
    raise SystemExit(f"unbalanced <ul> at {start}")


def find_runs(s: str, prefix: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    i = s.find(prefix)
    while i != -1:
        if not any(a <= i < b for a, b in spans):
            spans.append((i, ul_end(s, i)))
        i = s.find(prefix, i + 1)
    runs: list[list[int]] = []
    for a, b in spans:
        if runs and runs[-1][1] == a:
            runs[-1][1] = b
        else:
            runs.append([a, b])
    return [(a, b) for a, b in runs]


def hole_spans(name: str, inner: str) -> list[tuple[str, int, int]]:
    holes = PAGES[name]["holes"]
    if not holes:
        return []
    prefixes = list(dict.fromkeys(p for _, p in holes))
    runs = sorted(r for p in prefixes for r in find_runs(inner, p))
    if len(runs) != len(holes):
        raise SystemExit(f"{name}: expected {len(holes)} hole runs, "
                         f"found {len(runs)}: {runs}")
    out = []
    for (hname, prefix), (a, b) in zip(holes, runs):
        if not inner.startswith(prefix, a):
            raise SystemExit(f"{name}: hole {hname} at {a} is not {prefix}")
        out.append((hname, a, b))
    return out


_IMG_SRC = re.compile(r'(<img\b[^>]*?\bsrc=")/assets/images/([^"]+)(")')
_SCRIPT = re.compile(r"<script\b.*?</script>", re.S)
_NOSCRIPT = re.compile(r"<noscript\b.*?</noscript>", re.S)


def rewrite_imgs(s: str) -> str:
    def sub(m: re.Match) -> str:
        base = os.path.basename(m.group(2))
        if not (SITE_ASSETS / base).is_file():
            raise SystemExit(f"image {base!r} missing from {SITE_ASSETS}")
        return m.group(1) + "/assets/site/" + base + m.group(3)
    return _IMG_SRC.sub(sub, s)


BIASED_DECISIONS_PATH_LINK = 'href="/biased-decisions/'
BIASED_DECISIONS_SUBDOMAIN_LINK = 'href="https://biased-decisions.anth.us/'


def point_benchmark_links_at_subdomain(s: str) -> str:
    return s.replace(BIASED_DECISIONS_PATH_LINK, BIASED_DECISIONS_SUBDOMAIN_LINK)


def normalize(s: str) -> str:
    """The reference normalisation used for both emission and verification."""
    s = _SCRIPT.sub("", s)
    s = _NOSCRIPT.sub("", s)
    s = s.replace("<!-- -->", "")
    s = point_benchmark_links_at_subdomain(s)
    return rewrite_imgs(s)


def clean_static(name: str, seg: str) -> str:
    for bad in ("<script", "<noscript", "gatsby-image-wrapper", "/static/"):
        if bad in seg:
            raise SystemExit(f"{name}: static region contains {bad!r}")
    out = normalize(seg)
    if "<!-- -->" in out or "/assets/images/" in out:
        raise SystemExit(f"{name}: normalisation incomplete")
    return out


def page_meta(doc: str) -> dict[str, str]:
    t = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', doc)
    if not t or not d:
        raise SystemExit("missing <title> or meta description")
    return {"title": html.unescape(t.group(1)),
            "description": html.unescape(d.group(1))}


def load(args, name: str) -> str:
    path = Path(args.live_dir) / PAGES[name]["path"]
    if not path.is_file():
        raise SystemExit(f"missing reference page {path}; run with --fetch")
    return path.read_text(encoding="utf-8")


def ref_label(args, name: str) -> str:
    p = PAGES[name]
    return f"web/reference/live/{p['path']}  (live {LIVE_ORIGIN}{p['url']})"


_B64 = re.compile(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+")


def cross_check(args, pages: dict[str, dict]) -> bool:
    """Saved live <main> == <main> of the build of the deployed commit?"""
    public = Path(args.anthus) / "public"
    if not public.is_dir():
        print(f"build cross-check skipped: {public} not found")
        return True
    ok = True
    for n, p in pages.items():
        built = public / PAGES[n]["build"]
        if not built.is_file():
            print(f"  {n:16s} build page missing: {built}")
            ok = False
            continue
        mine = _B64.sub("B64", p["inner"])
        theirs = _B64.sub("B64", main_inner(built.read_text(encoding="utf-8")))
        same = mine == theirs
        ok &= same
        print(f"  {n:16s} live <main> == build <main>: "
              f"{'EXACT' if same else 'DIFFERENT'}  ({len(mine)} bytes)")
    return ok


# --------------------------------------------------------------------------
# emission
# --------------------------------------------------------------------------

_BREAK = re.compile(r"(?=<(?:h[1-6]|p|ul|ol|li|dl|dt|dd|section|div|figure|"
                    r"article|img|table|blockquote)[\s>])")


def literal(s: str, indent: str = "    ") -> str:
    """Adjacent string literals, broken before block tags (no added text)."""
    if not s:
        return "''"
    parts = [p for p in _BREAK.split(s) if p]
    assert "".join(parts) == s
    return "(\n" + "".join(f"{indent}{p!r}\n" for p in parts) + ")"


def const_name(page: str, i: int) -> str:
    return "_" + page.upper().replace("-", "_").replace("404", "NOT_FOUND") \
        + f"_{i}"


def emit(args, pages: dict[str, dict]) -> str:
    refs = "\n".join(f"    {n:16s} {ref_label(args, n)}" for n in PAGES)
    hole_lines = []
    for (page, hole), doc in HOLE_DOCS.items():
        hole_lines.append(f"    {PAGES[page]['func']}({hole}=...): {doc}")
    holes_txt = "\n".join(hole_lines)
    out = [f'''"""Production ``<main>`` inner HTML for the bespoke Anth.us pages.

GENERATED by bin/extract-page-html.py -- do not hand-edit; fix the extractor
or the reference and regenerate:

    python3 bin/extract-page-html.py --anthus ../Anth.us-live

Reference pages:
{refs}

Why verbatim: the port ships the production stylesheet, and that stylesheet
targets the production DOM (index-module--*, platform-module--*,
engage-module--*, resume, experience, clear, inline styles, ...). Each
function returns ONLY the inner HTML of <main>, lifted byte-for-byte from the
reference with three normalisations: <script>/<noscript> removed (none occur
outside the holes), React '<!-- -->' separators removed, and plain
<img src="/assets/images/X"> rewritten to src="/assets/site/X" (markup
otherwise unchanged). hrefs are left as production has them.

Dynamic holes are function arguments; pass the rendered list HTML (the
whole <ul> element(s)) and it is concatenated in place:
{holes_txt}

PAGE_META maps each page URL to its production <title> text and meta
description, both HTML-unescaped plain text (escape when emitting).
"""

from __future__ import annotations

from typing import Dict

''']
    out.append("PAGE_META: Dict[str, Dict[str, str]] = {\n")
    for n, p in pages.items():
        out.append(f"    {PAGES[n]['url']!r}: {{\n"
                   f"        'title': {p['meta']['title']!r},\n"
                   f"        'description': {p['meta']['description']!r},\n"
                   f"    }},\n")
    out.append("}\n\n")

    for n, p in pages.items():
        segs = p["static"]
        names = [h for h, _, _ in p["holes"]]
        for i, seg in enumerate(segs):
            before = "start of <main>" if i == 0 else f"after hole '{names[i-1]}'"
            after = "end of <main>" if i == len(segs) - 1 \
                else f"before hole '{names[i]}'"
            out.append(f"# {n}: {before} .. {after}\n")
            out.append(f"{const_name(n, i)} = {literal(segs[i])}\n\n")

    for n, p in pages.items():
        names = [h for h, _, _ in p["holes"]]
        sig = ", ".join(f"{h}: str" for h in names)
        sig = f"*, {sig}" if sig else ""
        body = const_name(n, 0)
        for i, h in enumerate(names):
            body += f" + {h} + {const_name(n, i + 1)}"
        doc = f"<main> inner HTML of {PAGES[n]['url']}"
        if names:
            doc += "; holes: " + ", ".join(names)
        out.append(f"\ndef {PAGES[n]['func']}({sig}) -> str:\n"
                   f"    \"\"\"{doc}.\"\"\"\n"
                   f"    return {body}\n\n")
    return "".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------

def class_tokens(s: str) -> set[str]:
    toks: set[str] = set()
    for c in re.findall(r'class="([^"]*)"', s):
        toks.update(c.split())
    return toks


def verify(pages: dict[str, dict]) -> bool:
    spec = importlib.util.spec_from_file_location("anthus_page_html", OUT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok = True
    placeholders = re.compile(
        r"\{(featured|portfolio|integrations|earlier|engagements|projects)\}")
    for n, p in pages.items():
        inner = p["inner"]
        kwargs = {h: normalize(inner[a:b]) for h, a, b in p["holes"]}
        got = getattr(mod, PAGES[n]["func"])(**kwargs)
        want = normalize(inner)
        # static-only reference: raw inner with hole spans cut out
        raw_static = "".join(p["raw_static"])
        mine_static = "".join(p["static"])
        res = "EXACT" if got == want else "DIFF"
        if got != want:
            ok = False
            k = next(i for i, (x, y) in enumerate(zip(got, want)) if x != y) \
                if any(x != y for x, y in zip(got, want)) else min(len(got), len(want))
            res += f" at {k}: got {got[k-40:k+60]!r} want {want[k-40:k+60]!r}"
        ct_ref, ct_me = class_tokens(raw_static), class_tokens(mine_static)
        mk_ref = raw_static.count("<mark")
        mk_me = mine_static.count("<mark")
        mk_full = inner.count("<mark")
        ph = placeholders.findall(mine_static)
        if ct_ref != ct_me or mk_ref != mk_me or ph:
            ok = False
        print(f"  {n:16s} {res}  len={len(got)}  classes(static) "
              f"ref={len(ct_ref)} mine={len(ct_me)} "
              f"diff={sorted(ct_ref ^ ct_me) or 'none'}  "
              f"<mark> static ref={mk_ref} mine={mk_me} (whole page "
              f"{mk_full})  placeholders={ph or 'none'}")
    return ok


def css_report(args, pages: dict[str, dict]) -> None:
    theme = THEME_CSS.read_text(encoding="utf-8")
    live_css = sorted(Path(args.live_dir).glob("styles.*.css"))
    live = live_css[-1].read_text(encoding="utf-8") if live_css else ""
    print(f"\nCSS class tokens used in <main> but absent from "
          f"{THEME_CSS.relative_to(REPO)}"
          + (f" (live stylesheet: {live_css[-1].name})" if live_css else ""))
    for n, p in pages.items():
        missing = []
        for tok in sorted(class_tokens(p["inner"])):
            pat = re.compile(r"\." + re.escape(tok) + r"(?![\w-])")
            if not pat.search(theme):
                missing.append(f"{tok} (live css: "
                               f"{'yes' if pat.search(live) else 'no'})")
        print(f"  {n}: " + (", ".join(missing) if missing else "none"))


# --------------------------------------------------------------------------

def _get(url: str) -> bytes:
    time.sleep(0.5)  # be polite
    req = urllib.request.Request(url, headers={"User-Agent": "anthus-port-reference/1"})
    with urllib.request.urlopen(req) as r:
        return r.read()


def fetch(args) -> None:
    live = Path(args.live_dir)
    live.mkdir(parents=True, exist_ok=True)
    css_href = None
    for n, p in PAGES.items():
        body = _get(LIVE_ORIGIN + p["url"])
        (live / p["path"]).write_bytes(body)
        m = re.search(rb'data-href="(/styles\.[0-9a-f]+\.css)"', body)
        css_href = m.group(1).decode() if m else css_href
        print(f"fetched {LIVE_ORIGIN}{p['url']} -> {live / p['path']}")
    if css_href:
        for old in live.glob("styles.*.css"):
            old.unlink()
        (live / css_href.lstrip("/")).write_bytes(_get(LIVE_ORIGIN + css_href))
        print(f"fetched {LIVE_ORIGIN}{css_href}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anthus", default=str(REPO.parent / "Anth.us-live"),
                    help="Anth.us Gatsby checkout with a public/ build "
                         "(default ../Anth.us-live)")
    ap.add_argument("--live-dir", default=str(REPO / "web/reference/live"),
                    help="saved live pages (default web/reference/live)")
    ap.add_argument("--fetch", action="store_true",
                    help=f"re-download the live pages + stylesheet from "
                         f"{LIVE_ORIGIN} into --live-dir first")
    ap.add_argument("--css-report", action="store_true",
                    help="list class tokens on the live pages missing from "
                         "web/css/anthus-theme.css")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    if args.fetch:
        fetch(args)

    pages: dict[str, dict] = {}
    for n in PAGES:
        doc = load(args, n)
        inner = main_inner(doc)
        holes = hole_spans(n, inner)
        cuts = [0] + [x for _, a, b in holes for x in (a, b)] + [len(inner)]
        raw = [inner[cuts[i]:cuts[i + 1]] for i in range(0, len(cuts), 2)]
        pages[n] = dict(inner=inner, holes=holes, raw_static=raw,
                        static=[clean_static(n, s) for s in raw],
                        meta=page_meta(doc))

    OUT.write_text(emit(args, pages), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    for n, p in pages.items():
        print(f"  {n:16s} holes=" + (", ".join(f"{h}[{a}:{b}]"
              for h, a, b in p["holes"]) or "none"))

    ok = True
    if not args.no_verify:
        print("verify (holes filled with the reference's own normalised "
              "hole HTML, compared to the normalised reference <main>):")
        ok = verify(pages)
    print("cross-check against the build of the deployed commit:")
    ok &= cross_check(args, pages)
    if args.css_report:
        css_report(args, pages)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
