"""The environment guard and the head, sitemap and robots output of Papyrus core, as the Anth.us projection ships them
(PPY-f1f0a8, PPY-e329c3).

Production is decided by ``site.productionUrl`` in web/projection.json and the two variables Papyrus reads
(``PAPYRUS_SITE_PUBLIC_URL``, ``PAPYRUS_SITE_ENV``); a guarded build is noindex, disallows crawling, has no
analytics script and carries a staging note in the footer.
"""
import json
import re
import unittest
from pathlib import Path

import anthus_dom
import support
from papyrus_content.projection.standard.config import standard_settings_from_mapping
from papyrus_content.projection.standard.environment import resolve_environment

WEB = Path(__file__).resolve().parent.parent / "web"
SETTINGS = standard_settings_from_mapping(json.loads((WEB / "projection.json").read_text(encoding="utf-8")))
STAGING = "https://staging.example.com"


def resolve(**environ):
    env = {}
    if "env" in environ:
        env["PAPYRUS_SITE_ENV"] = environ["env"]
    if "url" in environ:
        env["PAPYRUS_SITE_PUBLIC_URL"] = environ["url"]
    return resolve_environment(SETTINGS, env)


class Resolve(unittest.TestCase):
    def test_the_production_origin_is_anth_us(self):
        self.assertEqual(SETTINGS.identity.production_url, "https://anth.us")
        self.assertTrue(SETTINGS.guard)

    def test_matrix(self):
        self.assertTrue(resolve(env="production").production)
        self.assertEqual(resolve(env="production").origin, "https://anth.us")
        self.assertTrue(resolve(url="https://anth.us/").production)  # the public URL is the production origin
        self.assertEqual(resolve(url="https://anth.us/").origin, "https://anth.us")
        for guarded in (resolve(url=STAGING), resolve(url="staging.example.com"), resolve(url="https://feature-x.d1.amplifyapp.com/")):
            self.assertFalse(guarded.production, guarded)
            self.assertTrue(guarded.guarded)
        self.assertEqual(resolve(url="staging.example.com").origin, STAGING)
        # an explicit value other than "production" is guarded, whatever the origin says (fail safe)
        for bad in ("guarded", "prod", "yes", "staging"):
            self.assertTrue(resolve(env=bad, url="https://anth.us").guarded, bad)
        # and an explicit "production" is production on an origin of its own
        self.assertTrue(resolve(env="production", url=STAGING).production)
        self.assertEqual(resolve(env="production", url=STAGING).origin, STAGING)

    def test_a_site_with_no_variables_at_all_is_the_production_site(self):
        # The projector of the production pipeline sets neither; the guard exists to catch a *different* origin.
        self.assertTrue(resolve().production)
        self.assertEqual(resolve().origin, "https://anth.us")


class ProjectedOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = support.project_fixture("production")
        cls.guarded = support.project_fixture("guarded")

    @staticmethod
    def head(html):
        return html[: html.index("</head>")]

    def test_production_head(self):
        head = self.head(self.production.page("/about/"))
        self.assertIn('<link rel="canonical" href="https://anth.us/about/">', head)
        self.assertIn('<meta property="og:image" content="https://anth.us/assets/site/share-card.png">', head)
        self.assertIn('<meta name="twitter:creator" content="@RyanAlynPorter">', head)
        self.assertIn('<link rel="sitemap" type="application/xml" href="/sitemap-index.xml">', head)
        self.assertNotIn('name="robots"', head)
        self.assertNotIn("alternate", head)  # no feeds are advertised
        self.assertIn("googletagmanager.com/gtag/js?id=G-31SC26SDGX", head)  # analytics is on in production
        self.assertIn("noindex, nofollow", self.head(self.production.page("/articles/draft-article/")))  # a draft page
        self.assertNotIn("noindex", self.head(self.production.page("/articles/plain-article/")))

    def test_guarded_head_is_noindex_on_its_own_origin_with_no_analytics(self):
        for path in ("/about/", "/articles/plain-article/", "/articles/draft-article/", "/"):
            head = self.head(self.guarded.page(path))
            self.assertIn('<meta name="robots" content="noindex, nofollow">', head, path)
            self.assertIn(f'href="{STAGING}{path}"', head, path)
            self.assertNotIn("https://anth.us", head, path)
            self.assertNotIn("googletagmanager", head, path)
            self.assertNotIn("gtag(", self.guarded.page(path), path)
        self.assertIn("noindex", self.guarded.text("404.html"))

    def test_article_json_ld_keeps_the_plain_headline(self):
        head = self.head(self.production.page("/articles/call-criteria/"))
        self.assertIn('<meta property="og:title" content="Call Criteria | Anthus">', head)
        self.assertIn('"headline":"Call Criteria"', head)
        self.assertIn('"publisher":{"@type":"Organization","name":"Anthus AI Solutions"}', head)
        self.assertIn('"author":[{"@type":"Person","name":"Ryan Porter"}]', head)
        self.assertIn('<meta property="article:published_time" content="2023-10-01">', head)
        self.assertNotIn("ld+json", self.head(self.production.page("/articles/draft-article/")))  # a draft is no article for search

    def test_site_files(self):
        self.assertEqual(self.production.text("robots.txt"), "User-agent: *\nAllow: /\nSitemap: https://anth.us/sitemap-index.xml\n")
        self.assertEqual(self.guarded.text("robots.txt"), "User-agent: *\nDisallow: /\n")
        self.assertIn("<loc>https://anth.us/sitemap-0.xml</loc>", self.production.text("sitemap-index.xml"))
        locations = re.findall(r"<loc>([^<]+)</loc>", self.production.text("sitemap-0.xml"))
        self.assertEqual(locations, sorted(locations))
        self.assertIn("https://anth.us/", locations)
        self.assertNotIn("<lastmod>", self.production.text("sitemap-0.xml"))
        self.assertNotIn("https://anth.us", self.guarded.text("sitemap-index.xml"))
        self.assertNotIn("https://anth.us", self.guarded.text("sitemap-0.xml"))
        self.assertTrue(all(url.startswith(STAGING) for url in re.findall(r"<loc>([^<]+)</loc>", self.guarded.text("sitemap-0.xml"))))

    def test_staging_note_only_when_guarded(self):
        marker = "Staging preview of the Papyrus/Markus port of anth.us"
        self.assertIn(marker, anthus_dom.STAGING_NOTE_HTML)
        for path in ("/", "/articles/call-criteria/", "/ai-solutions/"):
            self.assertNotIn(marker, self.production.page(path), path)
            self.assertIn(marker, self.guarded.page(path), path)
        self.assertIn(marker, self.guarded.text("404.html"))
        self.assertNotIn(marker, self.production.text("404.html"))


if __name__ == "__main__":
    unittest.main()
