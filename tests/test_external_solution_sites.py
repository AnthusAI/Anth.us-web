"""Solutions with their own site: no page, a 301 to the site, links rewritten."""
import unittest
from pathlib import Path

import anthus_urls
import links
import support
from anthus_content import Collections, ContentNode
from solution_sites import EXTERNAL_SITES


def platform_node(slug):
    return ContentNode(slug=slug, source=Path(f"platform/{slug}.mdx"),
                       front_matter={"title": slug.title(), "state": "published"}, rel_dir="platform")


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
        mapping = links.UrlMap.__new__(links.UrlMap)
        mapping.urls, mapping.unresolved = self.urls, {}
        for slug, site in EXTERNAL_SITES.items():
            self.assertEqual(mapping.absolutize(f"/platform/{slug}/", base_dir="articles"), site + "/")
        self.assertEqual(mapping.absolutize("/platform/biblicus/", base_dir="articles"), "/platform/biblicus/")


class ProjectedExternalSolutionSites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()

    def test_the_projection_has_no_page_for_them_but_biblicus_keeps_its_page(self):
        files = self.projection.files
        for slug in EXTERNAL_SITES:
            self.assertNotIn(f"platform/{slug}/index.html", files, slug)
        self.assertIn("platform/biblicus/index.html", files)
        sitemap = self.projection.text("sitemap-0.xml")
        for slug in EXTERNAL_SITES:
            self.assertNotIn(f"/platform/{slug}/", sitemap)
        self.assertIn("/platform/biblicus/", sitemap)

    def test_the_redirect_store_sends_each_old_page_to_its_site(self):
        for slug, site in EXTERNAL_SITES.items():
            self.assertEqual(self.projection.redirects[f"/platform/{slug}/"], site, slug)
            self.assertEqual(self.projection.redirects[f"/platform/{slug}/index.html"], site, slug)
        self.assertNotIn("/platform/biblicus/", self.projection.redirects)
        self.assertNotIn("/<*>", self.projection.redirects)  # the catch-all 404 belongs to the edge function

    def test_links_to_the_old_pages_point_at_the_site_in_a_projected_article(self):
        anchors = support.anchors(self.projection.main("/articles/call-criteria/"))
        self.assertIn(EXTERNAL_SITES["primus"] + "/", anchors)
        self.assertIn(EXTERNAL_SITES["chatticus"] + "/", anchors)
        self.assertIn("/platform/biblicus/", anchors)
        self.assertNotIn("/platform/primus/", anchors)
        self.assertNotIn("/platform/chatticus/", anchors)

    def test_the_platform_index_does_not_list_them_as_pages(self):
        lines = self.projection.main("/platform/")
        self.assertNotIn('href="/platform/primus/"', lines)
        self.assertNotIn('href="/platform/kanbus/"', lines)
        self.assertIn('href="/platform/biblicus/"', lines)


if __name__ == "__main__":
    unittest.main()
