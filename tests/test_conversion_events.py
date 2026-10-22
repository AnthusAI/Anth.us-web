"""The GA4 conversion events are wired site-wide and every engage call to action is a plain link the listener can see."""
import json
import re
import unittest
from pathlib import Path

import anthus_dom
import support

REPOSITORY = Path(__file__).resolve().parents[1]
LISTENER_NAME = "conversion-events.js"
ENGAGE_LINK = re.compile(r'<a\b[^>]*href="/engage/(?:\?[^"#]*)?(?:#[\w-]+)?"')
PAGES = ("/", "/about/", "/ai-solutions/", "/ryan/", "/decision-models/", "/benchmarks/", "/platform/", "/articles/", "/articles/call-criteria/", "/platform/biblicus/")


def part(html, start, end):
    begin = html.index(start)
    return html[begin : html.index(end, begin)]


class ConversionEventWiringTests(unittest.TestCase):
    def test_the_listener_is_loaded_site_wide_the_way_the_other_chrome_scripts_are(self):
        settings = json.loads((REPOSITORY / "web" / "projection.json").read_text(encoding="utf-8"))
        self.assertIn(f"assets/{LISTENER_NAME}", settings["chrome"]["scripts"])
        self.assertTrue((REPOSITORY / "web" / "assets" / LISTENER_NAME).is_file())
        projection = support.project_fixture()
        self.assertIn(f"assets/{LISTENER_NAME}", projection.files)
        for path in (*PAGES, "/engage/"):
            self.assertRegex(projection.page(path), rf'<script src="/assets/{re.escape(LISTENER_NAME)}\?v=[0-9a-f]+"></script>', path)
        self.assertRegex(projection.text("404.html"), rf'/assets/{re.escape(LISTENER_NAME)}')

    def test_the_header_footer_hero_band_and_article_calls_to_action_are_engage_links(self):
        projection = support.project_fixture()
        self.assertRegex(anthus_dom._header_html("/"), ENGAGE_LINK)
        self.assertRegex(anthus_dom._footer_html(), ENGAGE_LINK)
        self.assertRegex(anthus_dom.ENGAGE_CTA_HTML, ENGAGE_LINK)
        for path in PAGES:
            html = projection.page(path)
            self.assertRegex(part(html, "<header", "</header>"), ENGAGE_LINK, path)
            self.assertRegex(part(html, '<footer class="site-footer"', "</footer>"), ENGAGE_LINK, path)
        for path in ("/", "/about/", "/ai-solutions/", "/ryan/"):  # the hero and the closing band of the authored pages
            self.assertGreaterEqual(len(ENGAGE_LINK.findall(part(projection.page(path), "<main", "</main>"))), 1, path)
        article = part(projection.page("/articles/venue-driver/"), "<main", "</main>")  # tagged client-acquisition
        self.assertIn(anthus_dom.ENGAGE_CTA_HTML, article)
        self.assertNotIn(anthus_dom.ENGAGE_CTA_HTML, projection.page("/articles/plain-article/"))

    def test_the_solution_card_link_names_the_solution_for_attribution(self):
        page = support.project_fixture().page("/ai-solutions/")
        for name in ("Cyclotron", "Chatticus", "Papyrus", "Auritus"):
            self.assertIn(f'href="/engage/?solution={name}"', page)
        self.assertNotIn("/engage/?solution=Primus", page)

    def test_the_site_scripts_carry_no_inline_analytics_handlers(self):
        projection = support.project_fixture()
        for path in PAGES:
            header = part(projection.page(path), "<header", "</header>")
            self.assertNotIn("gtag(", header)
            self.assertNotIn("onclick", header)
        self.assertNotIn("onclick", projection.page("/engage/"))
        self.assertNotIn("onclick", projection.page("/ai-solutions/"))


if __name__ == "__main__":
    unittest.main()
