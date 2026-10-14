"""Pages folded into Venue Driver: no page, listings exclude them, 301s, link rewrite, projector skip."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

try:
    import build_via_papyrus as build  # first: puts Papyrus on sys.path
    import anthus_pages
    import anthus_urls
    import projector
    from anthus_content import Collections, ContentNode
    from solution_sites import FOLDED_INTO
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    build = None
    IMPORT_ERROR = error

TARGET = "/articles/venue-driver/"


def node(slug, tags=("solutions", "engagement"), authored=None, rel_dir="solutions", stem=None):
    front = {"title": slug.title(), "state": "published", "tags": list(tags), "date": "2020-01-01",
             "excerpt": "x", "slug": authored or slug}
    return ContentNode(slug=slug, source=Path(f"{rel_dir}/{stem or slug}.mdx"), front_matter=front, rel_dir=rel_dir)


@unittest.skipIf(build is None, f"build module unavailable: {IMPORT_ERROR}")
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
        page = anthus_pages.ai_solutions_page(self.c.blog)
        self.assertNotIn("Ticket-Driver", page.replace(" ", "-"))
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
        build._SITE_URLS = self.urls
        for url in ("/blog/store-driver/", "/solutions/Paytronix/", "/articles/marketo/", "/vault"):
            self.assertEqual(build._absolutize(url, base_dir="articles"), TARGET, url)
        self.assertEqual(build._absolutize("/blog/call-criteria/", base_dir="articles"), "/articles/call-criteria/")

    def test_projector_skips_them(self):
        proj = projector.AnthusProjector.__new__(projector.AnthusProjector)
        for slug in FOLDED_INTO:
            summary = SimpleNamespace(section="articles", output_path=f"articles/{slug}.mdx", front_matter={"title": slug})
            self.assertEqual(proj.item_page_paths(summary), (), slug)
            self.assertEqual(proj.item_pages(SimpleNamespace(summary=summary), site=None), {}, slug)
        keep = SimpleNamespace(section="articles", output_path="articles/venue-driver.mdx", front_matter={"title": "v"})
        self.assertEqual(proj.item_page_paths(keep), ("articles/venue-driver/index.html",))


if __name__ == "__main__":
    unittest.main()


class FoldedRedirectsWithoutNodesTest(unittest.TestCase):
    """Unpublished folded items have no node, yet their old URLs must still redirect."""

    def test_rules_come_from_the_mapping(self):
        import anthus_urls
        from solution_sites import FOLDED_INTO
        source = open(anthus_urls.__file__, encoding="utf-8").read()
        self.assertIn("for slug, target in FOLDED_INTO.items()", source)
        self.assertIn("vault", FOLDED_INTO)
