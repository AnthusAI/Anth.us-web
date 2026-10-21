"""Listing-card visuals and the `pictogram:` front-matter field."""
import re
import unittest
from pathlib import Path

import anthus_dom
import cards
import links
import support
from anthus_content import ContentNode


def node(**front):
    base = {"title": "Primus Is a Classifier Lab", "slug": "primus", "date": "2026-09-27",
            "state": "published", "tags": ["articles"], "excerpt": "An excerpt."}
    base.update(front)
    return ContentNode(slug=base["slug"], source=Path("primus.mdx"), front_matter=base, rel_dir="")


def card_of(html, title):
    """The listing card whose title is ``title``."""
    return next(item for item in html.split('<li class="card notch acard') if f">{title}</a></h3>" in item)


class ListingVisuals(unittest.TestCase):
    def test_unknown_pictogram_name_fails_with_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "unknown pictogram 'nope'"):
            anthus_dom.node_pictogram(node(pictogram="nope"))
        with self.assertRaises(ValueError):
            cards._text_card(node(pictogram="nope"))

    def test_card_with_pictogram_renders_the_figure_and_no_img(self):
        html = cards._text_card(node(pictogram="self-aligning", preview_image="x.png"))
        self.assertIn('class="px', html)
        self.assertIn("acard__vis--px", html)
        self.assertNotIn("<img", html)

    def test_card_without_visual_gets_the_letter_tile(self):
        html = cards._text_card(node())
        self.assertIn("acard__vis--letter", html)
        self.assertIn("<span>P</span>", html)

    def test_og_image_falls_back_to_the_pictogram_png(self):
        self.assertEqual(
            links.pictogram_og(node(pictogram="self-aligning")),
            "/assets/site/pictograms/self-aligning.png",
        )
        self.assertIsNone(links.pictogram_og(node()))

    def test_article_header_shows_the_pictogram(self):
        html = anthus_dom.article_heading(node(pictogram="verdict-meter")).html()
        self.assertIn("heading__px", html)
        self.assertIn('class="px', html)

    def test_card_dates_are_plain_dates_even_for_iso_timestamps(self):
        stamped = node(date="2026-09-03T12:00:00-04:00")
        self.assertIn("<time>2026-09-03</time>", cards._text_card(stamped))


class ProjectedListingVisuals(unittest.TestCase):
    """The same three looks on projected listing pages, and the share image of each page."""

    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()

    def test_a_pictogram_wins_over_a_preview_image_on_the_card(self):
        card = card_of(self.projection.page("/ryan/"), "Robot Routing")  # pictogram and preview_image both set
        self.assertIn("acard__vis--px", card)
        self.assertIn('data-px="self-aligning"', card)
        self.assertNotIn("<img", card)

    def test_a_preview_image_card_shows_the_listing_copy_of_the_image(self):
        card = card_of(self.projection.page("/ai-solutions/"), "Call Criteria")
        self.assertRegex(card, r'<div class="acard__vis[^"]*"><img src="/assets/content/solutions/images/call-criteria-logo.png"')
        self.assertIn('width="1200" height="630"', card)  # measured from the rendition record

    def test_a_card_without_a_visual_gets_the_letter_tile(self):
        card = card_of(self.projection.page("/articles/"), "Plain Article")
        self.assertIn("acard__vis--letter", card)
        self.assertIn("<span>P</span>", card)
        self.assertNotIn("<img", card)

    def test_the_article_page_shows_the_pictogram_in_its_header(self):
        heading = self.projection.main("/articles/pictured-article/").split("</div>\n", 1)[0]
        self.assertIn("heading__px", heading)
        self.assertIn('data-px="verdict-meter"', heading)

    def test_share_image_is_the_preview_then_the_pictogram_png_then_the_default(self):
        def og(path):
            return re.search(r'<meta property="og:image" content="([^"]+)"', self.projection.page(path)).group(1)

        self.assertEqual(og("/articles/call-criteria/"), "https://anth.us/assets/content/solutions/images/call-criteria-logo.png")
        self.assertEqual(og("/articles/pictured-article/"), "https://anth.us/assets/site/pictograms/verdict-meter.png")
        self.assertEqual(og("/articles/plain-article/"), "https://anth.us/assets/site/share-card.png")
        self.assertEqual(og("/about/"), "https://anth.us/assets/site/share-card.png")


if __name__ == "__main__":
    unittest.main()
