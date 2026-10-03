#!/usr/bin/env python3
r"""Regenerate ``web/css/anthus-theme.css`` from the live Anth.us style sources.

The port's visual contract is *the production Gatsby site's compiled
stylesheet*, byte for byte where it matters. That bundle is assembled by
Gatsby out of three different kinds of source, which is why this script
exists instead of a one-line `sass` invocation:

1. ``src/components/layout.scss`` — the bulk of the chrome. Plain Sass, and it
   ``@import``\s ``node_modules/priority-plus/dist/priority-plus``, so the
   ``.p-plus*`` nav rules come in through it.
2. Every ``*.module.css`` under ``src/`` (``MODULES`` below: index, engage-cta,
   platform, research-cards and ``src/pages/engage``) — CSS Modules.  They use
   css-loader's ``:global(a.button)`` escape, which is honoured here. Gatsby's css-loader rewrites every local class name to
   ``<file>-module--<localName>--<hash>``, where ``<hash>`` is derived by
   webpack from the module path and content. That hash is **not reproducible
   outside Gatsby's own webpack configuration**, and the rendered markup has
   to use the identical string or the rules match nothing. So the mapping is
   committed in ``web/css/css-module-hashes.json``, extracted once from the
   shipped production bundle (see ``--extract-hashes``). ``anthus_pages``
   reads the same JSON, so CSS and DOM cannot drift apart.
3. ``gatsby-plugin-image``'s own rules. The plugin injects them from
   ``node_modules/gatsby-plugin-image/gatsby-ssr.js`` as an inline ``<style>``
   on every page, so they are *not* in ``public/styles.*.css`` even though
   ``.gatsby-image-wrapper`` is load-bearing for every floated, centred and
   full-width article image. They are pulled straight out of the plugin here.

   The plugin ships a second rule pair inside ``<noscript><style>``; it is
   included too.  The bundle itself is also inlined into most pages as
   ``<style data-href=...>`` (identical bytes), so nothing else is outside it.

``--verify`` compares the generated selector set against a shipped Gatsby
bundle (identical except the gatsby-plugin-image rules, which are inline-only)
and then compares the cascaded declarations of every (at-rule, selector) pair,
undoing the semantics-preserving cssnano/autoprefixer rewrites it knows about
(calc operand order, ``transparent`` vs ``rgba(0,0,0,0)``, ``flex:1 1`` vs
``flex:1``, hex case/shortening, dropped ``-webkit-`` twins, ...).  Exit status
is non-zero on any selector difference or unexplained declaration difference;
``-v`` lists each rule that was an equivalence.

Usage (developer machine only — the result is committed, because an Amplify
CI build has neither a Dart Sass binary nor the Anth.us checkout):

    # needs a checkout of AnthusAI/Anth.us with node_modules installed
    python3 bin/build-theme-css.py --anthus ../Anth.us-live

    # one-off, after a fresh Gatsby build changes a CSS-module hash
    python3 bin/build-theme-css.py --anthus ../Anth.us-live --extract-hashes \
        ../Anth.us-live/public/styles.*.css

    # compare the generated selector set against a shipped Gatsby bundle
    python3 bin/build-theme-css.py --anthus ../Anth.us-live \
        --verify ../Anth.us-live/public/styles.*.css
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CSS_DIR = REPO / "web" / "css"
HASHES = CSS_DIR / "css-module-hashes.json"
OUT = CSS_DIR / "anthus-theme.css"

# Every CSS Module the live Gatsby build ships, in the order they appear in
# ``public/styles.*.css`` (Gatsby emits them in import order after the
# layout.scss chunk).  name -> path relative to the Anth.us checkout.  The
# name is the ``<file>`` part of ``<file>-module--<local>--<hash>``.
# ``check_module_inventory`` fails loudly if the checkout grows a
# ``*.module.css`` that is not listed here (or one listed here vanishes), so a
# new module can never be silently dropped from the port again.
MODULES: dict[str, str] = {
    "index": "src/components/index.module.css",
    "engage-cta": "src/components/engage-cta.module.css",
    "platform": "src/components/platform.module.css",
    "research-cards": "src/components/research-cards.module.css",
    "engage": "src/pages/engage.module.css",
}
_MODULE_NAME = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"

# The exact markers gatsby-plugin-image's gatsby-ssr.js wraps its inline CSS
# in: the main <style> in <head>, and a second <style> inside <noscript>.
_GATSBY_IMAGE_CSS = re.compile(
    r"(\.gatsby-image-wrapper\{position:relative;overflow:hidden\}.*?"
    r"\.gatsby-image-wrapper-constrained\{[^}]*\})"
)
_GATSBY_IMAGE_NOSCRIPT_CSS = re.compile(
    r"(\.gatsby-image-wrapper noscript \[data-main-image\]\{[^}]*\}"
    r"\.gatsby-image-wrapper \[data-placeholder-image\]\{[^}]*\})"
)

HEADER = """/* Anth.us theme — GENERATED, do not hand-edit.
 *
 * Regenerate with:  python3 bin/build-theme-css.py --anthus ../Anth.us-live
 *
 * Sources (all in the AnthusAI/Anth.us Gatsby repo):
 *   src/components/layout.scss          (+ src/styles/variables.scss,
 *                                          node_modules/priority-plus)
 *   every *.module.css under src/       local names hashed per
 *     (index, engage-cta, platform,     web/css/css-module-hashes.json
 *      research-cards, pages/engage)
 *
 * This is the production site's real stylesheet, not an approximation of it.
 * The emitted DOM is built to match the selectors here; see web/anthus_dom.py
 * and web/anthus_pages.py. Fix a wrong colour/measure in layout.scss upstream
 * and re-run this script — never patch the output.
 */
"""


def _sass(node_modules: Path, scss: Path, load_paths: list[Path]) -> str:
    script = (
        "const sass=require(%s);"
        "const r=sass.compile(%s,{style:'compressed',loadPaths:%s});"
        "process.stdout.write(r.css);"
    ) % (
        json.dumps(str(node_modules / "sass")),
        json.dumps(str(scss)),
        json.dumps([str(p) for p in load_paths]),
    )
    proc = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        sys.exit(f"sass failed:\n{proc.stderr}")
    return proc.stdout


def _minify_css(text: str) -> str:
    """Whitespace/comment squeeze. Not a full minifier — just enough that the
    CSS-module chunks read like the rest of the bundle."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([{}:;,>])\s*", r"\1", text)
    text = re.sub(r";}", "}", text)
    return text.strip()


_LOCAL = re.compile(r"\.(?!\d)([A-Za-z_][A-Za-z0-9_]*)")
# css-loader's ``:global(...)`` escape hatch: the wrapper is dropped and the
# classes inside keep their plain names (``.box :global(a.button)`` becomes
# ``.engage-cta-module--box--xxxxx a.button``).
_GLOBAL = re.compile(r":global\(([^)]*)\)")


def _rewrite_selector(selector: str, module: str, hashes: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        key = f"{module}:{name}"
        if key not in hashes:
            sys.exit(
                f"No committed hash for {module}.module.css class {name!r}. "
                f"Re-run with --extract-hashes against a fresh Gatsby bundle."
            )
        return f".{module}-module--{name}--{hashes[key]}"

    out: list[str] = []
    pos = 0
    for glob in _GLOBAL.finditer(selector):
        out.append(_LOCAL.sub(repl, selector[pos : glob.start()]))
        out.append(glob.group(1))
        pos = glob.end()
    out.append(_LOCAL.sub(repl, selector[pos:]))
    return "".join(out)


def _module_css(module: str, source: Path, hashes: dict[str, str]) -> str:
    """Rewrite one CSS-module file's local class names to Gatsby's hashed names.

    Done block-by-block so that declaration values (`padding:.5rem`) are never
    touched -- only the selector text in front of each `{`.
    """
    text = source.read_text(encoding="utf-8").lstrip("\ufeff")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    pieces: list[str] = []
    index = 0
    while True:
        open_brace = text.find("{", index)
        if open_brace < 0:
            break
        selector = text[index:open_brace]
        # Find the matching close brace (CSS modules here nest only at-rules).
        depth = 1
        scan = open_brace + 1
        while scan < len(text) and depth:
            if text[scan] == "{":
                depth += 1
            elif text[scan] == "}":
                depth -= 1
            scan += 1
        body = text[open_brace + 1 : scan - 1]
        if selector.strip().startswith("@"):
            inner = _module_css_body(body, module, hashes)
            pieces.append(f"{_minify_css(selector)}{{{inner}}}")
        else:
            pieces.append(
                f"{_minify_css(_rewrite_selector(selector, module, hashes))}"
                f"{{{_minify_css(body)}}}"
            )
        index = scan
    return "".join(pieces)


def _module_css_body(body: str, module: str, hashes: dict[str, str]) -> str:
    pieces: list[str] = []
    index = 0
    while True:
        open_brace = body.find("{", index)
        if open_brace < 0:
            break
        selector = body[index:open_brace]
        close = body.find("}", open_brace)
        inner = body[open_brace + 1 : close]
        pieces.append(
            f"{_minify_css(_rewrite_selector(selector, module, hashes))}"
            f"{{{_minify_css(inner)}}}"
        )
        index = close + 1
    return "".join(pieces)


def gatsby_image_css(node_modules: Path) -> str:
    """Pull gatsby-plugin-image's inline stylesheet out of the installed plugin.

    This build emits the plugin's *markup shape* (a constrained wrapper, an
    aspect-ratio sizer, and the real <img> absolutely filling it) so these
    rules apply unchanged. Without them `.gatsby-image-wrapper.right` floats
    an unsized box and every article image in the corpus lays out wrong.
    """
    ssr = node_modules / "gatsby-plugin-image" / "gatsby-ssr.js"
    if not ssr.is_file():
        sys.exit(f"gatsby-plugin-image not installed: {ssr} missing")
    match = _GATSBY_IMAGE_CSS.search(ssr.read_text(encoding="utf-8"))
    if not match:
        sys.exit(
            f"Could not locate the gatsby-plugin-image CSS block in {ssr}. "
            "The plugin's internals changed; update _GATSBY_IMAGE_CSS."
        )
    noscript = _GATSBY_IMAGE_NOSCRIPT_CSS.search(ssr.read_text(encoding="utf-8"))
    if not noscript:
        sys.exit(f"Could not locate the gatsby-plugin-image <noscript> CSS in {ssr}.")
    return match.group(1) + noscript.group(1)


def check_module_inventory(anthus: Path) -> None:
    """The set of ``*.module.css`` files under src/ must equal MODULES."""
    found = {
        p.name[: -len(".module.css")]: str(p.relative_to(anthus))
        for p in (anthus / "src").rglob("*.module.css")
        if "site-content" not in p.parts and "node_modules" not in p.parts
    }
    declared = {k: v for k, v in MODULES.items()}
    if found != declared:
        sys.exit(
            "CSS-module inventory mismatch. Update MODULES in "
            f"bin/build-theme-css.py.\n  checkout only: "
            f"{sorted(set(found.items()) - set(declared.items()))}\n  script only:  "
            f"{sorted(set(declared.items()) - set(found.items()))}"
        )


def extract_hashes(bundle: Path) -> dict[str, str]:
    text = bundle.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for match in re.finditer(
        rf"\.({_MODULE_NAME})-module--([A-Za-z0-9_]+)--([0-9a-f]{{5}})", text
    ):
        found[f"{match.group(1)}:{match.group(2)}"] = match.group(3)
    if not found:
        sys.exit(f"No CSS-module class names found in {bundle}")
    shipped = {k.split(":")[0] for k in found}
    if shipped != set(MODULES):
        sys.exit(
            f"bundle ships CSS modules {sorted(shipped)} but MODULES lists "
            f"{sorted(MODULES)}"
        )
    return dict(sorted(found.items()))


def selector_set(text: str) -> set[str]:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out: set[str] = set()
    for match in re.finditer(r"([^{}]+)\{", text):
        selector = match.group(1).strip()
        if selector.startswith("@") or not selector:
            continue
        for part in selector.split(","):
            # `::after` and `:after` are the same thing; cssnano normalises one
            # way and Dart Sass the other, so compare on a canonical form.
            part = part.strip().replace("::", ":")
            part = re.sub(r"\*:(after|before|last-child)", r":\1", part)
            if part:
                out.add(part)
    return out


# --------------------------------------------------------------------------
# declaration-level comparison
# --------------------------------------------------------------------------
# The shipped bundle went through cssnano (+ autoprefixer's browserslist
# pruning); this script emits Dart Sass / hand-minified CSS.  Selector sets
# must match exactly, and for declarations the script compares the *cascaded*
# property map of every (at-rule context, selector) pair after undoing the
# known, semantics-preserving cssnano rewrites below.  Anything left over is a
# real difference and fails --verify.

def _ctx(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"\s*([:,>])\s*", r"\1", text)
    return re.sub(r"\s*\(\s*", "(", text).replace(" and(", "and(").replace("and (", "and(")


def _declarations(body: str) -> list[tuple[str, str]]:
    out = []
    for decl in re.split(r";(?![^(]*\))", body):
        key, _, value = decl.strip().partition(":")
        if key.strip():
            out.append((key.strip().lower(), value.strip()))
    return out


def cascaded_rules(text: str) -> dict[tuple[tuple[str, ...], str], dict[str, str]]:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    rules: dict[tuple[tuple[str, ...], str], dict[str, str]] = {}

    def block(chunk: str, ctx: tuple[str, ...]) -> None:
        index = 0
        while True:
            open_brace = chunk.find("{", index)
            if open_brace < 0:
                return
            head = chunk[index:open_brace].strip()
            depth, scan = 1, open_brace + 1
            while scan < len(chunk) and depth:
                depth += (chunk[scan] == "{") - (chunk[scan] == "}")
                scan += 1
            body = chunk[open_brace + 1 : scan - 1]
            index = scan
            if head.startswith("@-webkit-keyframes"):
                continue  # vendor-prefixed copy; cssnano/autoprefixer drop it
            if head.startswith("@") and not head.startswith("@font-face"):
                block(body, ctx + (_ctx(head),))
                continue
            for one in re.sub(r"\s+", " ", head).split(","):
                one = re.sub(r"\*:(after|before)", r":\1", one.strip().replace("::", ":"))
                one = re.sub(r"(^|[\s>+~])\*:(last-child|first-child)", r"\1:\2", one)
                one = re.sub(r"\s*>\s*", ">", re.sub(r"\s+:", " :", one))
                one = "100%" if one == "to" else one
                for key, value in _declarations(body):
                    rules.setdefault((ctx, one), {})[key] = value

    block(text, ())
    return rules


_FACTORS = re.compile(r"(var\([^)]*\)|-?[\d.]+)\*(var\([^)]*\)|-?[\d.]+)")


def _norm_value(prop: str, value: str) -> str:
    v = re.sub(r"\s+", " ", value.strip())
    v = re.sub(r"\s*([,/*])\s*", r"\1", v)
    v = re.sub(r"\(\s+", "(", v)
    v = re.sub(r"\s+\)", ")", v)
    v = v.replace(" !important", "!important")
    v = re.sub(r"(?<![\w.#-])(-?)0+\.(\d)", r"\1.\2", v)
    v = re.sub(r"(?<![\w.#-])0(px|rem|em)\b", "0", v)
    # multiplication commutes: calc(2*var(--x)) == calc(var(--x)*2)
    v = _FACTORS.sub(lambda m: "*".join(sorted((m.group(1), m.group(2)))), v)
    v = v.replace("Jersey\\ 25", "Jersey 25")
    v = re.sub(r"#([0-9a-f])\1([0-9a-f])\2([0-9a-f])\3\b", r"#\1\2\3", v.lower()) \
        if "#" in v else v
    v = {"white": "#fff", "transparent": "rgba(0,0,0,0)"}.get(v, v)
    v = re.sub(r"hsla\(0,0%?,100%,([^)]*)\)", r"rgba(255,255,255,\1)", v)
    v = v.replace("linear-gradient(90deg,", "linear-gradient(to right,")
    if "gradient(" in v:  # `0%` == `0`; an unpositioned last stop is 100%
        v = re.sub(r"(?<=[\w)]) 0%", " 0", v)
        v = re.sub(r"(?<=[\w)]) 100%\)$", ")", v)
        v = re.sub(r"(?<=[\w)]) 0(?=[,)])", " 0%", v)
    if prop == "font-family":  # `Jersey\ 25` (cssnano) == `"Jersey 25"` (Sass)
        v = v.replace('"', "").replace("'", "")
    if prop == "font-weight":
        v = {"normal": "400", "bold": "700"}.get(v, v)
    if prop == "flex" and v == "1 1":
        v = "1"
    if prop.startswith("border") and re.fullmatch(r"[^ ]+ [^ ]+ [^ ]+", v):
        v = " ".join(sorted(v.split(" ")))
    return v


def _expand(props: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in props.items():
        if key.startswith(("-webkit-", "-moz-", "-ms-")):
            continue  # prefixed twin of an unprefixed property cssnano kept
        norm = _norm_value(key, value)
        if key in ("margin", "padding"):
            bang = "!important" if norm.endswith("!important") else ""
            parts = (norm[: -len(bang)] if bang else norm).split(" ")
            if len(parts) == 1:
                parts = parts * 4
            elif len(parts) == 2:
                parts = parts * 2
            elif len(parts) == 3:
                parts = parts + [parts[1]]
            for side, part in zip(("top", "right", "bottom", "left"), parts):
                out[f"{key}-{side}"] = part + bang
        elif key == "animation":
            out[key] = " ".join(sorted(re.split(r"\s+", norm)))
        else:
            out[key] = norm
    return out


def declaration_diffs(reference: str, generated: str, ignore: set[str]):
    """Return (equivalent, real) lists of per-rule declaration differences."""
    ref, mine = cascaded_rules(reference), cascaded_rules(generated)
    equivalent: list[str] = []
    real: list[str] = []
    for key in sorted(set(ref) | set(mine), key=str):
        ctx, selector = key
        if key not in ref:
            if selector.split(" ")[0] in ignore or any(
                part in selector for part in ignore
            ):
                continue
            real.append(f"only in generated: {ctx} {selector}")
            continue
        if key not in mine:
            real.append(f"only in reference: {ctx} {selector}")
            continue
        raw_ref, raw_mine = ref[key], mine[key]
        if raw_ref == raw_mine:
            continue
        a, b = _expand(raw_ref), _expand(raw_mine)
        label = f"{' '.join(ctx)} {selector}".strip()
        if a == b:
            changed = sorted(
                k for k in set(raw_ref) | set(raw_mine) if raw_ref.get(k) != raw_mine.get(k)
            )
            equivalent.append(f"{label}: {', '.join(changed)}")
        else:
            for k in sorted(set(a) | set(b)):
                if a.get(k) != b.get(k):
                    real.append(f"{label}: {k}: ref={a.get(k)!r} generated={b.get(k)!r}")
    return equivalent, real


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anthus",
        default=str(REPO.parent / "Anth.us-live"),
        help="path to the AnthusAI/Anth.us Gatsby checkout (needs node_modules)",
    )
    parser.add_argument(
        "--extract-hashes",
        metavar="BUNDLE.css",
        help="refresh web/css/css-module-hashes.json from a shipped Gatsby bundle",
    )
    parser.add_argument(
        "--verify",
        metavar="BUNDLE.css",
        help="compare the generated selector set against a shipped Gatsby bundle",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="with --verify, list every cssnano-equivalent rule")
    args = parser.parse_args()

    anthus = Path(args.anthus).resolve()
    components = anthus / "src" / "components"
    node_modules = anthus / "node_modules"
    layout = components / "layout.scss"
    if not layout.is_file():
        sys.exit(f"Not an Anth.us checkout: {layout} missing")
    if not (node_modules / "sass").is_dir():
        sys.exit(f"Dart Sass not installed: {node_modules / 'sass'} missing. Run npm ci there.")

    if args.extract_hashes:
        HASHES.write_text(
            json.dumps(extract_hashes(Path(args.extract_hashes)), indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {HASHES.relative_to(REPO)}")

    if not HASHES.is_file():
        sys.exit(f"{HASHES} missing; run once with --extract-hashes")
    hashes = json.loads(HASHES.read_text(encoding="utf-8"))

    base = _sass(
        node_modules,
        layout,
        [anthus, anthus / "src", components, anthus / "src" / "styles"],
    )
    # src/styles/variables.scss carries a UTF-8 BOM, which Dart Sass passes
    # straight through and which would then sit in front of the first
    # selector in the bundle.
    parts = [HEADER, base.lstrip("\ufeff").rstrip("\n"), "\n"]
    check_module_inventory(anthus)
    for module, rel in MODULES.items():
        parts.append(f"/* {module}.module.css */\n")
        parts.append(_module_css(module, anthus / rel, hashes))
        parts.append("\n")
    parts.append("/* gatsby-plugin-image/gatsby-ssr.js inline stylesheets (<head> + <noscript>) */\n")
    parts.append(gatsby_image_css(node_modules))
    parts.append("\n")
    generated = "".join(parts)
    OUT.write_text(generated, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(generated.encode())} bytes)")

    if args.verify:
        reference = Path(args.verify).read_text(encoding="utf-8")
        ref = selector_set(reference)
        mine = selector_set(generated)
        only_ref = sorted(ref - mine)
        # The gatsby-plugin-image rules are injected inline by the plugin on
        # every production page rather than living in the bundle, so they are
        # expected to show up as "extra" against a bundle-only comparison.
        plugin = selector_set(gatsby_image_css(node_modules))
        only_mine = sorted(mine - ref - plugin)
        print(f"selectors: reference {len(ref)}, generated {len(mine)}")
        if only_ref:
            print(f"  MISSING from generated ({len(only_ref)}):")
            for selector in only_ref:
                print(f"    {selector}")
        if only_mine:
            print(f"  EXTRA in generated ({len(only_mine)}):")
            for selector in only_mine:
                print(f"    {selector}")
        if not only_ref and not only_mine:
            print("  selector sets are identical")
        equivalent, real = declaration_diffs(
            reference, generated, {".gatsby-image-wrapper", ".gatsby-image-wrapper-constrained"}
        )
        print(
            f"declarations: {len(equivalent)} rules differ only by cssnano/"
            f"autoprefixer-equivalent rewrites, {len(real)} real differences"
        )
        if args.verbose:
            for line in equivalent:
                print(f"    equivalent: {line}")
        for line in real:
            print(f"    REAL: {line}")
        return 1 if (only_ref or only_mine or real) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
