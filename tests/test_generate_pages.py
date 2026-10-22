"""The fixed page set of the site, its page metadata and the determinism of a projection (PPY-aebfcd).

The pages are the authored page files of web/pages (named in web/projection.json) and the listing pages of the
collections. An empty corpus projects the authored pages alone.
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

import support

WEB = Path(__file__).resolve().parent.parent / "web"

#: The pages the site always has once its collections have items (the listing pages exist from the first item).
EXPECTED_HTML = {
    "404.html",
    "about/index.html",
    "ai-solutions/index.html",
    "articles/index.html",
    "benchmarks/index.html",
    "decision-models/index.html",
    "engage/index.html",
    "index.html",
    "platform/index.html",
    "posts/index.html",
    "privacy/index.html",
    "reading/index.html",
    "research/index.html",
    "ryan/index.html",
    "tags/index.html",
}
AUTHORED_ONLY = {
    "404.html", "about/index.html", "ai-solutions/index.html", "benchmarks/index.html", "decision-models/index.html",
    "engage/index.html", "index.html", "platform/index.html", "privacy/index.html", "ryan/index.html",
}


def empty_corpus() -> Path:
    path = Path(tempfile.mkdtemp(prefix="anthus-empty-", dir=support.os.environ.get("ANTHUS_BUILD_DIR")))
    (path / "articles").mkdir()
    return path


def html_files(projection):
    return {key for key in projection.files if key.endswith(".html")}


class FixedPageSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()
        cls.empty = support.project_directory(empty_corpus())

    def test_the_fixed_pages_are_all_projected(self):
        self.assertEqual(EXPECTED_HTML - html_files(self.projection), set())
        for key in EXPECTED_HTML:
            self.assertTrue(self.projection.text(key).strip(), key)
            self.assertIn("<title>", self.projection.text(key), key)

    def test_the_pages_files_named_in_projection_json_are_exactly_the_authored_pages(self):
        settings = json.loads((WEB / "projection.json").read_text(encoding="utf-8"))
        sources = {page["source"] for page in settings["pages"]} | {settings["notFound"]["source"]}
        self.assertEqual(sources, {f"pages/{path.name}" for path in (WEB / "pages").glob("*.md")})

    def test_an_empty_corpus_projects_the_authored_pages_alone(self):
        self.assertEqual(html_files(self.empty), AUTHORED_ONLY)
        for key in AUTHORED_ONLY:
            self.assertTrue(self.empty.text(key).strip(), key)
        self.assertEqual(json.loads(self.empty.text("_data/search-index.json")), [])
        self.assertEqual(self.empty.report.errors, [])

    def test_every_page_is_complete_markup_with_no_directive_leftovers(self):
        for key in html_files(self.projection) | html_files(self.empty):
            html = self.projection.files.get(key) or self.empty.files[key]
            text = html.decode("utf-8")
            self.assertTrue(text.startswith("<!DOCTYPE html>"), key)
            self.assertNotRegex(text, r"::(?:raw|endraw|include|band|column|button|island)", key)
            self.assertNotIn("<!--bare-->", text, key)
            self.assertNotRegex(re.sub(r"<pre.*?</pre>", "", text, flags=re.S), r"\{\{[a-z]", key)  # a code sample may show the token
            self.assertNotRegex(re.sub(r'<div class="markus-page-actions.*?</div>', "", text, flags=re.S), r'class="[^"]*\bmarkus-', key)  # the site's own class vocabulary only

    def test_page_metadata(self):
        titles = {"about/index.html": "About Us | Anthus", "ryan/index.html": "Ryan Porter | Anthus",
                  "platform/index.html": "Anthus Platform | Anthus", "engage/index.html": "Engage Anthus | Anthus"}
        for key, title in titles.items():
            html = self.projection.text(key)
            self.assertIn(f"<title>{title}</title>", html, key)
            self.assertRegex(html, r'<meta name="description" content="[^"]{40,}">', key)
            self.assertIn(f'<link rel="canonical" href="https://anth.us/{key[:-len("index.html")]}">', html, key)
        collection = self.projection.text("articles/index.html")
        self.assertIn("Long-form articles from Anthus", collection)

    def test_a_projection_is_deterministic(self):
        again = support.project_directory(support.FIXTURE_CONTENT)
        self.assertEqual(again.files, self.projection.files)
        self.assertEqual(again.redirects, self.projection.redirects)
        self.assertEqual(support.project_directory(empty_corpus()).files, self.empty.files)

    def test_no_articles_register_no_article_metadata(self):
        self.assertFalse([key for key in self.empty.files if key.startswith("articles/")])
        self.assertEqual(json.loads(self.empty.text("_data/latest.json")), [])
        self.assertNotIn("application/ld+json", self.empty.page("/about/"))
        self.assertNotIn("<loc>https://anth.us/articles/", self.empty.text("sitemap-0.xml"))

    def test_the_404_page_is_the_authored_page_in_the_site_shell(self):
        html = self.projection.text("404.html")
        self.assertIn("<main", html)
        self.assertIn('<footer class="site-footer"', html)
        self.assertEqual(html, self.empty.text("404.html"))  # it depends on no content


if __name__ == "__main__":
    unittest.main()
