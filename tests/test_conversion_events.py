"""GA4 call-to-action events come from Papyrus's shared listener, once per click; every engage call to action is a plain link.

Behaviour (Gherkin):
  Given a page rendered with Papyrus's GA4 events script and the site's own scripts
  When a visitor clicks an engage link, a product link or an outbound link
  Then exactly one cta_click is sent, with the cta_text, the cta_location of the element and the destination host and path
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

import anthus_dom
import support

REPOSITORY = Path(__file__).resolve().parents[1]
RETIRED_LISTENER_NAME = "conversion-events.js"
HARNESS = REPOSITORY / "tests" / "cta_click_harness.mjs"
ENGAGE_LINK = re.compile(r'<a\b[^>]*href="/engage/(?:\?[^"#]*)?(?:#[\w-]+)?"')
PAGES = ("/", "/about/", "/ai-solutions/", "/ryan/", "/decision-models/", "/benchmarks/", "/platform/", "/articles/", "/articles/call-criteria/", "/platform/biblicus/")


def part(html, start, end):
    begin = html.index(start)
    return html[begin : html.index(end, begin)]


class ConversionEventWiringTests(unittest.TestCase):
    def test_the_site_sends_no_cta_click_of_its_own_so_papyrus_is_the_only_sender(self):
        settings = json.loads((REPOSITORY / "web" / "projection.json").read_text(encoding="utf-8"))
        self.assertNotIn(f"assets/{RETIRED_LISTENER_NAME}", settings["chrome"]["scripts"])
        self.assertFalse((REPOSITORY / "web" / "assets" / RETIRED_LISTENER_NAME).exists())
        for script in (REPOSITORY / "web").rglob("*.js"):
            self.assertNotIn("cta_click", script.read_text(encoding="utf-8"), script.name)
        projection = support.project_fixture()
        self.assertNotIn(RETIRED_LISTENER_NAME, "".join(projection.page(path) for path in (*PAGES, "/engage/")))
        for path in (*PAGES, "/engage/"):
            self.assertIn("window.papyrusAnalytics", projection.page(path), path)

    def test_each_click_on_an_engage_product_or_outbound_link_sends_exactly_one_cta_click(self):
        page = support.project_fixture().page("/ai-solutions/")
        events_script = next(s for s in re.findall(r"<script>(.*?)</script>", page, re.S) if "window.papyrusAnalytics" in s)
        links = [
            {"href": "/engage/", "text": "START A PROJECT →", "within": [".site-header"]},
            {"href": "/engage/?solution=Cyclotron", "text": "Work with us on Cyclotron", "within": [".card"]},
            {"href": "https://chattic.us", "text": "Visit Chatticus", "within": [".card"]},
            {"href": "https://primus.anth.us/pricing?utm=x#top", "text": "Visit Primus", "within": [".hero"]},
            {"href": "https://github.com/AnthusAI", "text": "GitHub", "within": [".site-footer"]},
        ]
        completed = subprocess.run(
            ["node", str(HARNESS)], capture_output=True, text=True, check=True,
            input=json.dumps({"navigationSource": (REPOSITORY / "web" / "assets" / "site-nav.js").read_text(encoding="utf-8"),
                              "eventsScript": events_script, "pathname": "/ai-solutions/", "links": links}),
        )
        expected = [
            ("START A PROJECT", "header", "anth.us/engage/"),
            ("Work with us on Cyclotron", "solution-card", "anth.us/engage/"),
            ("Visit Chatticus", "solution-card", "chattic.us/"),
            ("Visit Primus", "hero", "primus.anth.us/pricing"),
            ("GitHub", "footer", "github.com/AnthusAI"),
        ]
        results = json.loads(completed.stdout)
        for (text, place, url), events in zip(expected, results, strict=True):
            self.assertEqual(
                events, [{"verb": "event", "name": "cta_click",
                          "parameters": {"cta_text": text, "cta_location": place, "link_url": url, "transport_type": "beacon"}}], text)

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
