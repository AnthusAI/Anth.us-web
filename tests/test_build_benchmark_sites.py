"""Benchmark sites follow SITE_ENV: python3 tests/test_build_benchmark_sites.py"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "web"))
import site_env  # noqa: E402

specification = importlib.util.spec_from_file_location(
    "build_benchmark_sites", REPOSITORY_ROOT / "bin" / "build_benchmark_sites.py"
)
build_benchmark_sites = importlib.util.module_from_spec(specification)
specification.loader.exec_module(build_benchmark_sites)

BENCHMARK_SITE = {
    "name": "biased-decisions",
    "publishedPath": "/biased-decisions/",
    "robotsDisallowedPaths": ["/og-gallery/"],
}


def write_page(directory: Path, relative_path: str, html: str) -> None:
    page = directory / relative_path
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")


class GuardedBuild(unittest.TestCase):
    def test_every_benchmark_page_is_marked_noindex_once(self):
        with tempfile.TemporaryDirectory() as directory:
            published = Path(directory)
            write_page(published, "index.html", "<html><head><title>a</title></head></html>")
            write_page(published, "religion/index.html", '<html><head lang="en"><title>b</title></head></html>')
            self.assertEqual(build_benchmark_sites.mark_every_page_noindex(published), 2)
            self.assertEqual(build_benchmark_sites.mark_every_page_noindex(published), 0)
            for page in published.rglob("*.html"):
                self.assertEqual(page.read_text(encoding="utf-8").count(site_env.NOINDEX_META), 1)


class ProductionBuild(unittest.TestCase):
    def test_sitemap_and_robots_rules_keep_the_production_robots_check_passing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / "dist"
            output = root / "astro-dist"
            published = dist / "biased-decisions"
            published.mkdir(parents=True)
            write_page(output, "index.html", "<html><head></head></html>")
            write_page(output, "gender/index.html", "<html><head></head></html>")
            write_page(output, "og-gallery/index.html", "<html><head></head></html>")
            write_page(output, "religion-v2/index.html", '<meta http-equiv="refresh" content="0; url=/x/">')
            environment = site_env.SiteEnv(production=True, origin=site_env.PRODUCTION_ORIGIN)
            (dist / "robots.txt").write_text(site_env.robots_txt(environment), encoding="utf-8")
            build_benchmark_sites.DIST_DIRECTORY = dist
            page_count = build_benchmark_sites.publish_sitemap_and_robots_rules(
                BENCHMARK_SITE, output, published, site_env.PRODUCTION_ORIGIN
            )
            self.assertEqual(page_count, 2)
            sitemap = (published / "sitemap.xml").read_text(encoding="utf-8")
            self.assertIn("<loc>https://anth.us/biased-decisions/gender/</loc>", sitemap)
            self.assertNotIn("og-gallery", sitemap)
            self.assertNotIn("religion-v2", sitemap)
            robots_lines = (dist / "robots.txt").read_text(encoding="utf-8").splitlines()
            self.assertIn("Disallow: /biased-decisions/og-gallery/", robots_lines)
            self.assertIn("Sitemap: https://anth.us/biased-decisions/sitemap.xml", robots_lines)
            self.assertEqual(site_env._check_robots(environment, dist), [])


if __name__ == "__main__":
    unittest.main()
