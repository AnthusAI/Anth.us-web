"""The staging bridge and Papyrus core's guard, head, sitemap and robots output (PPY-f1f0a8, PPY-e329c3).

Needs PAPYRUS_ROOT (a Papyrus checkout with the standard front end): python3 tests/test_site_env.py
"""
import os
import sys
import unittest
from pathlib import Path

PAPYRUS = os.environ.get("PAPYRUS_ROOT")
if PAPYRUS:
    sys.path.insert(0, str(Path(PAPYRUS) / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

try:
    import site_env as se
except ImportError:  # no Papyrus on the path
    se = None


@unittest.skipIf(se is None, "needs PAPYRUS_ROOT")
class Resolve(unittest.TestCase):
    def test_matrix(self):
        r = se.resolve
        self.assertEqual(r({}).mode, "guarded")
        self.assertEqual(r({"SITE_ENV": "production"}).mode, "production")
        self.assertEqual(r({"SITE_ENV": "production", "AWS_BRANCH": "main"}).mode, "production")
        x = r({"SITE_ENV": "production", "AWS_BRANCH": "feature-x", "AWS_APP_ID": "d1"})
        self.assertEqual((x.mode, bool(x.warnings)), ("guarded", True))
        self.assertEqual(x.origin, "https://feature-x.d1.amplifyapp.com")
        for bad in ("Production", "prod", "yes"):
            e = r({"SITE_ENV": bad})
            self.assertEqual((e.mode, bool(e.warnings)), ("guarded", True), bad)
        self.assertEqual(r({"AWS_BRANCH": "main"}).mode, "guarded")  # branch alone is not enough
        self.assertEqual(r({"SITE_ENV": "production"}).origin, "https://anth.us")
        self.assertEqual(r({"ANTHUS_SITE_ORIGIN": "https://s.example/"}).origin, "https://s.example")
        self.assertEqual(r({}).origin, se.LOCAL_FALLBACK_ORIGIN)
        self.assertTrue(r({"SITE_ENV": "production"}).analytics_enabled)
        self.assertFalse(r({}).analytics_enabled)
        # production ignores an origin override
        self.assertEqual(r({"SITE_ENV": "production", "ANTHUS_SITE_ORIGIN": "https://x.y"}).origin, "https://anth.us")


@unittest.skipIf(se is None, "needs PAPYRUS_ROOT")
class CoreOutput(unittest.TestCase):
    GUARDED = se.resolve({"ANTHUS_SITE_ORIGIN": "https://staging.example.com"}) if se else None
    PRODUCTION = se.resolve({"SITE_ENV": "production"}) if se else None

    def head(self, env, **kwargs):
        arguments = dict(title="About | Anthus", path="/about/", description="d & d", image=None)
        arguments.update(kwargs)
        return se.head_tags(env, **arguments)

    def test_production_head(self):
        head = self.head(self.PRODUCTION)
        self.assertIn('<link rel="canonical" href="https://anth.us/about/">', head)
        self.assertIn('<meta property="og:image" content="https://anth.us/assets/site/share-card.png">', head)
        self.assertIn('<meta name="twitter:creator" content="@RyanAlynPorter">', head)
        self.assertIn('<link rel="sitemap" type="application/xml" href="/sitemap-index.xml">', head)
        self.assertNotIn('name="robots"', head)
        self.assertNotIn("alternate", head)  # no feeds are advertised
        self.assertIn("noindex, nofollow", self.head(self.PRODUCTION, noindex=True))  # a draft page

    def test_guarded_head_is_noindex_on_its_own_origin(self):
        head = self.head(self.GUARDED)
        self.assertIn('<meta name="robots" content="noindex, nofollow">', head)
        self.assertIn('href="https://staging.example.com/about/"', head)
        self.assertNotIn("https://anth.us", head)

    def test_article_json_ld_keeps_the_plain_headline(self):
        article = {"headline": "Plain", "published": "2026-01-02", "authors": ["Ann"]}
        head = self.head(self.PRODUCTION, title="Plain | Anthus", path="/articles/plain/", article=article)
        self.assertIn('<meta property="og:title" content="Plain | Anthus">', head)
        self.assertIn('"headline":"Plain"', head)
        self.assertIn('"publisher":{"@type":"Organization","name":"Anthus AI Solutions"}', head)

    def test_site_files(self):
        self.assertEqual(se.robots_txt(self.PRODUCTION), "User-agent: *\nAllow: /\nSitemap: https://anth.us/sitemap-index.xml\n")
        self.assertEqual(se.robots_txt(self.GUARDED), "User-agent: *\nDisallow: /\n")
        self.assertIn("<loc>https://anth.us/sitemap-0.xml</loc>", se.sitemap_index_xml(self.PRODUCTION))
        urls = se.sitemap_0_xml(["/b/", "/a/"], self.PRODUCTION)
        self.assertLess(urls.index("https://anth.us/a/"), urls.index("https://anth.us/b/"))
        self.assertNotIn("<lastmod>", urls)

    def test_staging_note_only_when_guarded(self):
        self.assertEqual(se.footer_note(self.PRODUCTION), "")
        self.assertIn(se.STAGING_NOTE_MARKER, se.footer_note(self.GUARDED))


if __name__ == "__main__":
    unittest.main()
