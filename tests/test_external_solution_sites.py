"""Solutions with their own site: no page, a 301 to the site, links rewritten."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

try:
    import build_via_papyrus as build  # first: puts Papyrus on sys.path
    import anthus_urls
    from anthus_content import Collections, ContentNode
    from solution_sites import EXTERNAL_SITES
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    build = None
    IMPORT_ERROR = error


def platform_node(slug):
    return ContentNode(slug=slug, source=Path(f"platform/{slug}.mdx"),
                       front_matter={"title": slug.title(), "state": "published"}, rel_dir="platform")


@unittest.skipIf(build is None, f"build module unavailable: {IMPORT_ERROR}")
class ExternalSolutionSites(unittest.TestCase):
    def setUp(self):
        nodes = [platform_node(s) for s in (*EXTERNAL_SITES, "biblicus")]
        self.collections = Collections.from_nodes(nodes)
        pages = {"platform/index.html", "platform/biblicus.html"}
        self.urls = anthus_urls.SiteUrls.from_collections(self.collections, pages=pages, posts_per_page=8)

    def test_no_page_is_emitted_for_them_but_biblicus_keeps_its_page(self):
        self.assertEqual([n.slug for n in self.collections.platform], ["biblicus"])
        self.assertEqual(sorted(n.slug for n in self.collections.external_platform), sorted(EXTERNAL_SITES))

    def test_permanent_redirects_to_each_site(self):
        rules = anthus_urls.legacy_rules(self.urls, og_images={}, page_images={}, dist=None).rules
        by_source = {r["source"]: r for r in rules}
        for slug, site in EXTERNAL_SITES.items():
            rule = by_source[f"/platform/{slug}/"]
            self.assertEqual((rule["target"], rule["status"]), (site, "301"))
        self.assertLess([r["source"] for r in rules].index("/platform/primus/"),
                        [r["source"] for r in rules].index("/<*>"))

    def test_links_to_the_old_pages_point_at_the_site(self):
        state = build.SiteState(urls=self.urls)
        for slug, site in EXTERNAL_SITES.items():
            self.assertEqual(build._absolutize(state, f"/platform/{slug}/", base_dir="articles"), site + "/")
        self.assertEqual(build._absolutize(state, "/platform/biblicus/", base_dir="articles"), "/platform/biblicus/")


if __name__ == "__main__":
    unittest.main()
