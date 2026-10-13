#!/usr/bin/env python3
"""Render every pictogram to a 1200x630 PNG (og:image / twitter:image).

An inline SVG cannot be an og:image, so each pictogram in
`arcade_pictograms.NAMES` is rendered in LIGHT mode, in its static
reduced-motion frame, centred on the `--bg` colour with a small ANTHUS
wordmark in the corner. Output: `web/assets/site/pictograms/<name>.png`
(committed; the build only reads them, it never renders).

    python3 bin/render-pictogram-pngs.py [name ...]

Needs Node with puppeteer (default: ~/Projects/Pilobol.us/node_modules) and
Google Chrome (override with PUPPETEER_EXECUTABLE_PATH).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

import anthus_dom  # noqa: E402
import arcade_pictograms  # noqa: E402
import site_css  # noqa: E402

OUT = ROOT / "web" / "assets" / "site" / "pictograms"
PUPPETEER = Path(os.environ.get("PUPPETEER_DIR", Path.home() / "Projects/Pilobol.us/node_modules/puppeteer"))
CHROME = os.environ.get("PUPPETEER_EXECUTABLE_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Jersey+10&family=Jersey+25&display=swap">
<style>{css}
html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:var(--bg)}}
.stage{{width:1200px;height:630px;display:flex;align-items:center;justify-content:center;padding:70px 90px 90px;box-sizing:border-box}}
.stage .px{{width:100%;height:100%;display:flex;align-items:center;justify-content:center}}
.stage .px__svg{{width:100%;height:100%}}
.stage .px__cap{{display:none}}
.mark{{position:absolute;left:48px;bottom:34px}}
.mark .site-logo{{pointer-events:none}}
</style></head><body><div class="stage">{figure}</div>
<div class="mark"><span class="site-logo">{mark}</span></div></body></html>"""

JS = """
const puppeteer = require(process.argv[2]);
(async () => {
  const jobs = JSON.parse(process.argv[4]);
  const b = await puppeteer.launch({executablePath: process.argv[3], headless: 'new'});
  for (const [html, png] of jobs) {
    const p = await b.newPage();
    await p.setViewport({width: 1200, height: 630, deviceScaleFactor: 1});
    await p.emulateMediaFeatures([
      {name: 'prefers-color-scheme', value: 'light'},
      {name: 'prefers-reduced-motion', value: 'reduce'},
    ]);
    await p.goto('file://' + html, {waitUntil: 'load', timeout: 30000});
    await p.evaluate(() => document.fonts.ready);
    await new Promise(r => setTimeout(r, 400));
    await p.screenshot({path: png});
    await p.close();
  }
  await b.close();
})();
"""


def main(argv: list[str]) -> int:
    names = argv or list(arcade_pictograms.NAMES)
    unknown = [n for n in names if n not in arcade_pictograms.NAMES]
    if unknown:
        sys.exit(f"unknown pictogram(s): {', '.join(unknown)}")
    OUT.mkdir(parents=True, exist_ok=True)
    css = site_css.stylesheet_bytes().decode()
    jobs = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            html = Path(tmp) / f"{name}.html"
            html.write_text(
                PAGE.format(css=css, figure=arcade_pictograms.render(name), mark=anthus_dom._LOGO_SVG),
                encoding="utf-8",
            )
            jobs.append([str(html), str(OUT / f"{name}.png")])
        script = Path(tmp) / "render.js"
        script.write_text(JS, encoding="utf-8")
        import json

        subprocess.run(["node", str(script), str(PUPPETEER), CHROME, json.dumps(jobs)], check=True)
    print(f"wrote {len(jobs)} PNG(s) to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
