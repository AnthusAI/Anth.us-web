"""Listing-card visuals and the `pictogram:` front-matter field.

Needs PAPYRUS_ROOT (and PYTHONPATH=$PAPYRUS_ROOT/src for pytest); skipped when the
build module cannot be imported.
Run: PAPYRUS_ROOT=/path/to/Papyrus python3 tests/test_listing_visuals.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

try:
    import build_via_papyrus as build  # first: it puts Papyrus on sys.path
    import anthus_dom
    import anthus_pages
    from anthus_content import ContentNode
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    build = None
    IMPORT_ERROR = error


def node(**front):
    base = {"title": "Primus Is a Classifier Lab", "slug": "primus", "date": "2026-09-27",
            "state": "published", "tags": ["articles"], "excerpt": "An excerpt."}
    base.update(front)
    return ContentNode(slug=base["slug"], source=Path("primus.mdx"), front_matter=base, rel_dir="")


@unittest.skipIf(build is None, f"build module unavailable: {IMPORT_ERROR}")
class ListingVisuals(unittest.TestCase):
    def test_unknown_pictogram_name_fails_with_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "unknown pictogram 'nope'"):
            anthus_dom.node_pictogram(node(pictogram="nope"))
        with self.assertRaises(ValueError):
            anthus_pages._text_card(node(pictogram="nope"))

    def test_card_with_pictogram_renders_the_figure_and_no_img(self):
        html = anthus_pages._text_card(node(pictogram="self-aligning", preview_image="x.png"))
        self.assertIn('class="px', html)
        self.assertIn("acard__vis--px", html)
        self.assertNotIn("<img", html)

    def test_card_without_visual_gets_the_letter_tile(self):
        html = anthus_pages._text_card(node())
        self.assertIn("acard__vis--letter", html)
        self.assertIn("<span>P</span>", html)

    def test_og_image_falls_back_to_the_pictogram_png(self):
        self.assertEqual(
            build._pictogram_og(node(pictogram="self-aligning")),
            "/assets/site/pictograms/self-aligning.png",
        )
        self.assertIsNone(build._pictogram_og(node()))

    def test_article_header_shows_the_pictogram(self):
        html = anthus_dom.article_heading(node(pictogram="verdict-meter")).html()
        self.assertIn("heading__px", html)
        self.assertIn('class="px', html)


if __name__ == "__main__":
    unittest.main()
