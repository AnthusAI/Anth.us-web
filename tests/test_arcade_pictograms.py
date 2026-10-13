"""Tests for the animated pixel pictograms (web/arcade_pictograms.py).

Run from the repo root:  python3 tests/test_arcade_pictograms.py
"""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

import arcade_pictograms as ap  # noqa: E402

CSS = (ROOT / "web" / "css" / "arcade-pictograms.css").read_text()
SVG_NS = "{http://www.w3.org/2000/svg}"


def _svg_part(html: str) -> str:
    return html[html.index("<svg"):html.index("</svg>") + len("</svg>")]


class PictogramTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(len(ap.NAMES), 13)
        self.assertEqual(len(set(ap.NAMES)), 13)

    def test_every_name_renders_well_formed(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                ET.fromstring(html)  # whole figure is well-formed XML
                ET.fromstring(_svg_part(html))
                self.assertIn(f'data-px="{name}"', html)
                self.assertTrue(html.startswith('<figure class="px'))

    def test_accessibility(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                svg = _svg_part(html)
                self.assertIn('role="img"', svg)
                label = re.search(r'aria-label="([^"]+)"', svg)
                self.assertIsNotNone(label)
                self.assertGreater(len(label.group(1).split()), 12)
                self.assertIn("<figcaption", html)
                self.assertIn('shape-rendering="crispEdges"', svg)

    def test_no_hex_colours_and_no_script_or_style(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", html))
                self.assertNotIn("<script", html)
                self.assertNotIn("<style", html)
                self.assertNotIn("http", _svg_part(html).replace("http://www.w3.org", ""))

    def test_only_rects_and_text_as_shapes(self):
        allowed = {"svg", "g", "rect", "text", "defs", "clipPath"}
        for name in ap.NAMES:
            with self.subTest(name=name):
                for el in ET.fromstring(_svg_part(ap.render(name))).iter():
                    self.assertIn(el.tag.replace(SVG_NS, ""), allowed)

    def test_integer_grid(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                svg = _svg_part(ap.render(name))
                for m in re.finditer(r'<rect[^>]*?\s(?:x|y|width|height)="([^"]+)"', svg):
                    self.assertRegex(m.group(1), r"^-?\d+$")

    def test_unique_prefixes_and_css_coverage(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                abbr = ap._BUILDERS[name]().abbr
                for cls in set(re.findall(r'class="an(?: sx| r\d)* (px-[a-z]+-\d+)"', html)):
                    self.assertTrue(cls.startswith(f"px-{abbr}-"))
                    self.assertIn(f"@keyframes {cls}{{", CSS, "run --write-css")

    def test_css_contract(self):
        for token in ("--px-ink", "--px-pink", "--px-blue", "--px-dim", "--px-bg",
                      "#1b1426", "#dc5497", "#0389d7", "#d6e6f2", "#fbfdff",
                      "#f3eef8", "#ff57b4", "#3fb2f7", "#2e2540", "#0e0b16",
                      "prefers-color-scheme:dark", "prefers-reduced-motion:reduce",
                      "animation-play-state:paused", ".is-live"):
            self.assertIn(token, CSS)
        self.assertEqual(ap.keyframes_css().strip(),
                         CSS.split(ap.CSS_BEGIN)[1].split(ap.CSS_END)[0].strip(),
                         "generated keyframes are stale: run --write-css")

    def test_deterministic(self):
        for name in ap.NAMES:
            self.assertEqual(ap.render(name), ap.render(name))

    def test_size_budget(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                self.assertLess(len(_svg_part(ap.render(name))), 13000)

    def test_unknown_name(self):
        with self.assertRaises(KeyError):
            ap.render("nope")


if __name__ == "__main__":
    unittest.main()
