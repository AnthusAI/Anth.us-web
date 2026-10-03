#!/usr/bin/env python3
r"""Regenerate ``web/css/anthus-theme.css`` from the live Anth.us style sources.

The port's visual contract is *the production Gatsby site's compiled
stylesheet*, byte for byte where it matters. That bundle is assembled by
Gatsby out of three different kinds of source, which is why this script
exists instead of a one-line `sass` invocation:

1. ``src/components/layout.scss`` — the bulk of the chrome. Plain Sass, and it
   ``@import``\s ``node_modules/priority-plus/dist/priority-plus``, so the
   ``.p-plus*`` nav rules come in through it.
2. ``src/components/index.module.css`` and ``platform.module.css`` — CSS
   Modules. Gatsby's css-loader rewrites every local class name to
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

``--verify`` compares the generated selector set against a shipped Gatsby
bundle; `--verify-ssr` additionally checks the gatsby-plugin-image block.

Usage (developer machine only — the result is committed, because an Amplify
CI build has neither a Dart Sass binary nor the Anth.us checkout):

    # needs a checkout of AnthusAI/Anth.us with node_modules installed
    python3 bin/build-theme-css.py --anthus ../Anth.us

    # one-off, after a fresh Gatsby build changes a CSS-module hash
    python3 bin/build-theme-css.py --anthus ../Anth.us --extract-hashes \
        ../Anth.us/public/styles.*.css

    # compare the generated selector set against a shipped Gatsby bundle
    python3 bin/build-theme-css.py --anthus ../Anth.us \
        --verify ../Anth.us/public/styles.*.css
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

MODULES = ("index", "platform")

# The exact marker gatsby-plugin-image's gatsby-ssr.js wraps its inline CSS in.
_GATSBY_IMAGE_CSS = re.compile(
    r"(\.gatsby-image-wrapper\{position:relative;overflow:hidden\}.*?"
    r"\.gatsby-image-wrapper-constrained\{[^}]*\})"
)

HEADER = """/* Anth.us theme — GENERATED, do not hand-edit.
 *
 * Regenerate with:  python3 bin/build-theme-css.py --anthus ../Anth.us
 *
 * Sources (all in the AnthusAI/Anth.us Gatsby repo):
 *   src/components/layout.scss          (+ src/styles/variables.scss,
 *                                          node_modules/priority-plus)
 *   src/components/index.module.css     local names hashed per
 *   src/components/platform.module.css  web/css/css-module-hashes.json
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

    return _LOCAL.sub(repl, selector)


def _module_css(module: str, components: Path, hashes: dict[str, str]) -> str:
    """Rewrite one CSS-module file's local class names to Gatsby's hashed names.

    Done block-by-block so that declaration values (`padding:.5rem`) are never
    touched -- only the selector text in front of each `{`.
    """
    source = components / f"{module}.module.css"
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
    return match.group(1)


def extract_hashes(bundle: Path) -> dict[str, str]:
    text = bundle.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for match in re.finditer(
        r"\.((?:index|platform))-module--([A-Za-z0-9_]+)--([0-9a-f]{5})", text
    ):
        found[f"{match.group(1)}:{match.group(2)}"] = match.group(3)
    if not found:
        sys.exit(f"No CSS-module class names found in {bundle}")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--anthus",
        default=str(REPO.parent / "Anth.us"),
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
    for module in MODULES:
        parts.append(f"/* {module}.module.css */\n")
        parts.append(_module_css(module, components, hashes))
        parts.append("\n")
    parts.append("/* gatsby-plugin-image/gatsby-ssr.js inline stylesheet */\n")
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
        return 1 if (only_ref or only_mine) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
