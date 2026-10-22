"""Pages folded into Venue Driver: no page, listings exclude them, 301s, link rewrite, projector skip."""
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import anthus_urls
import hooks
import links
import support
from anthus_content import Collections, ContentNode
from solution_sites import FOLDED_INTO

TARGET = "/articles/venue-driver/"


def node(slug, tags=("solutions", "engagement"), authored=None, rel_dir="solutions", stem=None):
    front = {"title": slug.title(), "state": "published", "tags": list(tags), "date": "2020-01-01",
             "excerpt": "x", "slug": authored or slug}
    return ContentNode(slug=slug, source=Path(f"{rel_dir}/{stem or slug}.mdx"), front_matter=front, rel_dir=rel_dir)


class FoldedPages(unittest.TestCase):
    def setUp(self):
        self.folded = [node(s) for s in FOLDED_INTO]
        self.folded.append(node("paytronix", authored="Paytronix", stem="Paytronix"))
        self.keep = [node("venue-driver"), node("call-criteria")]
        self.c = Collections.from_nodes(self.folded + self.keep)
        pages = {f"articles/{n.slug}.html" for n in self.c.blog}
        self.urls = anthus_urls.SiteUrls.from_collections(self.c, pages=pages, posts_per_page=8)

    def test_no_page_and_out_of_every_listing(self):
        kept = {"venue-driver", "call-criteria"}
        self.assertEqual({n.slug for n in self.c.blog}, kept)
        self.assertEqual({n.slug for n in self.c.solutions}, kept)
        self.assertEqual({n.slug for n in self.c.tags["solutions"]}, kept)
        self.assertEqual(len(self.c.folded), len(self.folded))

    def test_every_url_shape_redirects_permanently_to_venue_driver(self):
        rules = {r["source"]: r for r in anthus_urls.legacy_rules(self.urls, og_images={}, page_images={}, dist=None).rules}
        for slug in FOLDED_INTO:
            for shape in (f"/articles/{slug}/", f"/blog/{slug}/", f"/solutions/{slug}/", f"/{slug}/"):
                for src in (shape, shape + "index.html"):
                    self.assertEqual((rules[src]["target"], rules[src]["status"]), (TARGET, "301"), src)
        for src in ("/articles/Paytronix/", "/solutions/Paytronix/", "/blog/Paytronix/index.html"):
            self.assertEqual(rules[src]["target"], TARGET, src)
        order = list(rules)
        self.assertLess(order.index("/blog/ticket-driver/"), order.index("/blog/<slug>/"))

    def test_links_in_bodies_are_rewritten(self):
        mapping = links.UrlMap.__new__(links.UrlMap)  # the map of a fixed set of pages, without a site
        mapping.urls, mapping.unresolved = self.urls, {}
        for url in ("/blog/store-driver/", "/solutions/Paytronix/", "/articles/marketo/", "/vault"):
            self.assertEqual(mapping.absolutize(url, base_dir="articles"), TARGET, url)
        self.assertEqual(mapping.absolutize("/blog/call-criteria/", base_dir="articles"), "/articles/call-criteria/")

    def test_the_hooks_skip_them(self):
        for slug in FOLDED_INTO:
            summary = SimpleNamespace(section="articles", output_path=f"articles/{slug}.mdx", front_matter={"title": slug})
            self.assertFalse(hooks.item_filter(summary), slug)
        keep = SimpleNamespace(section="articles", output_path="articles/venue-driver.mdx", front_matter={"title": "v"})
        self.assertTrue(hooks.item_filter(keep))


class ProjectedFoldedPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()

    def test_the_projection_has_no_page_for_a_folded_item_and_keeps_its_target(self):
        files = self.projection.files
        self.assertNotIn("articles/ticket-driver/index.html", files)
        self.assertNotIn("articles/paytronix/index.html", files)
        self.assertNotIn("articles/Paytronix/index.html", files)
        self.assertIn("articles/venue-driver/index.html", files)

    def test_they_are_in_no_listing_tag_page_sitemap_or_search_data(self):
        projection = self.projection
        for path in ("/ai-solutions/", "/", "/ryan/", "/tags/solutions/", "/tags/engagement/", "/articles/"):
            html = projection.page(path)
            self.assertNotIn("Ticket Driver", html, path)
            self.assertNotIn("ticket-driver", html, path)
            self.assertNotIn("Paytronix", html, path)
        for key in ("sitemap-0.xml", "_data/search-index.json", "_data/latest.json"):
            self.assertNotIn("ticket-driver", projection.text(key), key)
            self.assertNotIn("aytronix", projection.text(key), key)
        engagement = projection.page("/tags/engagement/")
        self.assertIn("Venue Driver", engagement)
        self.assertIn("Call Criteria", engagement)

    def test_every_url_shape_of_every_folded_slug_is_in_the_redirect_store(self):
        redirects = self.projection.redirects
        for slug in FOLDED_INTO:
            for shape in (f"/articles/{slug}/", f"/blog/{slug}/", f"/solutions/{slug}/", f"/{slug}/"):
                for source in (shape, shape + "index.html"):
                    self.assertEqual(redirects.get(source), TARGET, source)
        for source in ("/articles/Paytronix/", "/solutions/Paytronix/", "/blog/Paytronix/index.html"):
            self.assertEqual(redirects[source], TARGET, source)

    def test_body_links_to_folded_items_point_at_venue_driver(self):
        anchors = support.anchors(self.projection.main("/articles/call-criteria/"))
        self.assertEqual(anchors.count(TARGET), 3)  # the guide itself, ticket-driver and Paytronix
        for href in anchors:
            self.assertNotIn("ticket-driver", href)
            self.assertNotIn("Paytronix", href)
        self.assertIn("/articles/plain-article/", anchors)  # an ordinary article is rewritten to its page, not folded

    def test_redirects_exist_for_folded_items_that_are_not_in_the_corpus_at_all(self):
        self.assertEqual(self.projection.redirects["/blog/vault/"], TARGET)
        self.assertEqual(self.projection.redirects["/solutions/ticketing-analysis/"], TARGET)


class FoldedRedirectsWithoutNodesTest(unittest.TestCase):
    """Unpublished folded items have no node, yet their old URLs must still redirect."""

    def test_rules_come_from_the_mapping(self):
        source = open(anthus_urls.__file__, encoding="utf-8").read()
        self.assertIn("for slug, target in FOLDED_INTO.items()", source)
        self.assertIn("vault", FOLDED_INTO)


if __name__ == "__main__":
    unittest.main()
