"""Guard tests (PPY-f1f0a8 / PPY-0ba000). Stdlib only: python3 tests/test_site_env.py"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
import site_env as se  # noqa: E402


def page(env: se.SiteEnv, path_url: str = "/", *, canonical=None) -> str:
    canonical = canonical if canonical is not None else env.origin + path_url
    return (
        f'<html><head><title>t</title><link rel="canonical" href="{canonical}">\n'
        f'<meta property="og:url" content="{canonical}">\n'
        + se.head_extras(env)
        + f"</head><body>x{se.footer_note(env)}</body></html>"
    )


def make_dist(env: se.SiteEnv, root: Path) -> None:
    for rel, url in (("index.html", "/"), ("about/index.html", "/about/"), ("404.html", "/404.html")):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(page(env, url), encoding="utf-8")
    se.write_site_files(env, root, [env.origin + "/", env.origin + "/about/"])


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


class Assertions(unittest.TestCase):
    G = se.resolve({"ANTHUS_SITE_ORIGIN": "https://staging.example.com"})
    P = se.resolve({"SITE_ENV": "production"})

    def run_case(self, env, mutate=None):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_dist(env, root)
            if mutate:
                mutate(root)
            return se.assert_dist(env, root)

    def fails(self, env, mutate, needle):
        with self.assertRaises(se.GuardError) as cm:
            self.run_case(env, mutate)
        self.assertIn(needle, str(cm.exception))

    def edit(self, rel, fn):
        def m(root):
            p = root / rel
            p.write_text(fn(p.read_text()), encoding="utf-8")
        return m

    def test_clean_builds_pass(self):
        self.assertEqual(self.run_case(self.G), 3)
        self.assertEqual(self.run_case(self.P), 3)

    def test_guarded_violations(self):
        self.fails(self.G, self.edit("about/index.html", lambda t: t.replace(se.NOINDEX_META, "")), "noindex robots meta missing")
        self.fails(self.G, self.edit("index.html", lambda t: t.replace(se.STAGING_NOTE_MARKER, "x")), "staging note missing")
        self.fails(self.G, lambda r: (r / "robots.txt").write_text("User-agent: *\nAllow: /\n"), "guarded robots.txt")
        self.fails(self.G, self.edit("index.html", lambda t: t.replace("</head>", '<script src="https://www.googletagmanager.com/gtag/js"></script></head>')), "analytics present")

    def test_production_violations(self):
        self.fails(self.P, self.edit("index.html", lambda t: t.replace("</head>", se.NOINDEX_META + "</head>")), "noindex robots meta present")
        self.fails(self.P, self.edit("about/index.html", lambda t: t.replace("</body>", se.STAGING_NOTE_HTML + "</body>")), "staging note present")
        self.fails(self.P, self.edit("index.html", lambda t: t.replace("https://anth.us/", "https://staging.example.com/", 1)), "canonical")
        self.fails(self.P, lambda r: (r / "robots.txt").write_text("User-agent: *\nDisallow: /\n"), "production robots.txt")
        wrong = se.SiteEnv(True, "https://example.com")
        with self.assertRaises(se.GuardError):
            self.run_case(wrong)
        with self.assertRaises(se.GuardError):  # guarded must not claim the production origin
            self.run_case(se.SiteEnv(False, se.PRODUCTION_ORIGIN))

    def test_sitemap_violations(self):
        self.fails(self.G, lambda r: (r / "sitemap.xml").write_text("<x/>"), "sitemap.xml must not")
        self.fails(self.G, lambda r: (r / "sitemap-0.xml").write_text("<urlset"), "not valid XML")
        self.fails(self.G, self.edit("sitemap-0.xml", lambda t: t.replace("/about/", "/nope/")), "no file nope/index.html")
        self.fails(self.G, self.edit("sitemap-0.xml", lambda t: t.replace("</urlset>", "<url><loc>https://staging.example.com/404.html</loc></url></urlset>")), "404")
        self.fails(self.G, self.edit("sitemap-index.xml", lambda t: t.replace("sitemap-0", "sitemap-9")), "sitemap-index.xml locs")
        self.fails(self.G, self.edit("about/index.html", lambda t: t.replace(se.SITEMAP_LINK, "")), "sitemap <link> missing")


if __name__ == "__main__":
    unittest.main()
