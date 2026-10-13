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
from arcade_pictograms import _n  # noqa: E402

CSS = (ROOT / "web" / "css" / "arcade-pictograms.css").read_text()
SVG_NS = "{http://www.w3.org/2000/svg}"


def _svg_part(html: str) -> str:
    return html[html.index("<svg"):html.index("</svg>") + len("</svg>")]


class PictogramTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(len(ap.NAMES), 17)
        self.assertEqual(len(set(ap.NAMES)), 17)

    def test_every_name_renders_well_formed(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                ET.fromstring(html)  # whole figure is well-formed XML
                ET.fromstring(_svg_part(html))
                self.assertEqual(html.count("<svg class=\"px__svg"), 2 if name == "hero-loop" else 1)
                self.assertIn(f'data-px="{name}"', html)
                self.assertTrue(html.startswith('<figure class="px'))

    def test_accessibility(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                svg = _svg_part(html)
                self.assertIn('role="img"', html)
                self.assertEqual(html.count('role="img"'), 1)
                label = re.search(r'aria-label="([^"]+)"', html)
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
        allowed = {"svg", "g", "rect", "text", "defs", "clipPath", "use", "animate", "animateTransform"}
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

    def test_motion_is_smil_in_user_units(self):
        # Safari scales CSS px under text zoom differently from SVG user units, so no movement may
        # depend on a CSS length: no CSS animation, no px in any transform, no style attributes.
        self.assertNotRegex(CSS, r"@keyframes|animation-|translate\(|scale\(|(?<![-\w])transform\s*:")
        for name in ap.NAMES:
            with self.subTest(name=name):
                html = ap.render(name)
                self.assertNotIn("style=", html)
                self.assertNotIn('class="an', html)
                for m in re.finditer(r'transform="([^"]*)"', html):
                    self.assertNotRegex(m.group(1), r"px|em|%")
                for m in re.finditer(r'(?:values|keyTimes|begin|dur)="([^"]*)"', html):
                    self.assertNotRegex(m.group(1), r"[0-9](px|em|rem|%)")
                self.assertNotRegex(html, r"translate\([^)]*(px|em)")
                self.assertIn("<animate", html)
                self.assertIn('repeatCount="indefinite"', html)
                self.assertIn('begin="', html)

    def test_solution_marks_have_no_css_length_motion(self):
        css = (ROOT / "web" / "css" / "arcade.css").read_text()
        for needle in ("offset-distance", "offset-path", "sm-chat-gaze", "sm-chat-blink",
                       "sm-cyc-head", "sm-cyc-show"):
            self.assertNotIn(needle, css)
        marks = (ROOT / "web" / "solution_marks.py").read_text()
        self.assertIn("animateMotion", marks)
        self.assertNotRegex(marks, r"translate\([^)]*px")

    def test_css_contract(self):
        for token in ("--px-ink", "--px-pink", "--px-blue", "--px-dim", "--px-bg",
                      "#1b1426", "#dc5497", "#0389d7", "#d6e6f2", "#fbfdff",
                      "#f3eef8", "#ff57b4", "#3fb2f7", "#2e2540", "#0e0b16",
                      "prefers-color-scheme:dark"):
            self.assertIn(token, CSS)

    def test_deterministic(self):
        for name in ap.NAMES:
            self.assertEqual(ap.render(name), ap.render(name))

    def test_size_budget(self):
        for name in ap.NAMES:
            with self.subTest(name=name):
                self.assertLess(len(_svg_part(ap.render(name))), 30000)

    def test_scorecard_one_document_per_row_on_one_clock(self):
        f = ap._BUILDERS["scorecard"]()
        html = f.figure()
        self.assertEqual(len(f.meta["docs"]), len(f.meta["rows"]))
        self.assertEqual(len(f.meta["rows"]), 6)  # rows scored per loop == documents added
        for i, t in enumerate(ap._SC_ROWS):
            self.assertEqual(f.meta["rows"][i], f.meta["docs"][i])  # identical animation
            anim = f.meta["rows"][i]
            self.assertTrue(anim.split('keyTimes="')[1].startswith(f"0;{_n(t / 100)}"))
            self.assertEqual(html.count(anim), 2)  # the row's marks and its document

    def test_copy_rules(self):
        banned = {
            "scorecard": [r"\bcards\b"],
            "relocate": ["never stopped", "no downtime", "never stop", "redundan"],
            "timeline": ["production", "enterprise"],
            "platform-stack": ["RUNTIME", "runtime"],
        }
        for name, pats in banned.items():
            html = ap.render(name)
            for pat in pats:
                self.assertIsNone(re.search(pat, html), (name, pat))
        self.assertIn("hundreds of scorecards", ap.render("scorecard"))
        self.assertIn("DECISION MODELS", ap.render("platform-stack"))
        ps = ap.render("platform-stack")
        self.assertLess(ps.index("DECISION MODELS"), ps.index("AGENTS"))  # below agents
        rl = ap.render("relocate")
        self.assertIn("DOORS", rl)
        self.assertNotIn("redundan", rl)
        self.assertNotIn("Site C", rl)
        self.assertNotIn("SITE C", rl)
        for lbl in ("2007", "2009", "TODAY"):
            self.assertIn(lbl, ap.render("timeline"))

    def test_hero_has_phone_variant_with_single_label(self):
        html = ap.render("hero-loop")
        self.assertEqual(html.count('role="img"'), 1)
        self.assertIn('data-v="wide"', html)
        self.assertIn('data-v="tall"', html)
        self.assertEqual(html.count('aria-hidden="true"'), 2 + html.count("px__g"))

    def test_venue_system_copy(self):
        html = ap.render("venue-system")
        for w in ("TICKETS", "TABLES", "GUEST LIST", "QUEUE", "SERVERLESS", "LOYALTY",
                  "SERVICENOW", "DATA / BI"):
            self.assertIn(w, html)
        texts = re.findall(r">([^<>]+)</text>", html) + re.findall(r'aria-label="([^"]+)"', html)
        self.assertFalse(any(re.search(r"\d", x) for x in texts))

    def test_unknown_name(self):
        with self.assertRaises(KeyError):
            ap.render("nope")


if __name__ == "__main__":
    unittest.main()
