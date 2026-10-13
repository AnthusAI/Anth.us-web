"""`state: draft` articles: served, noindexed, left out of listings, shown only via ?drafts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

try:
    import build_via_papyrus as build  # first: puts Papyrus on sys.path
    import anthus_pages
    import site_env
    from anthus_content import Collections, ContentNode
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    build = None
    IMPORT_ERROR = error


def node(slug, state, tags=("articles", "research")):
    return ContentNode(slug=slug, source=Path(f"{slug}.mdx"), rel_dir="",
                       front_matter={"title": slug.title(), "state": state, "tags": list(tags),
                                     "date": "2026-09-01", "excerpt": "An excerpt."})


PROD = None


@unittest.skipIf(build is None, f"build module unavailable: {IMPORT_ERROR}")
class DraftReview(unittest.TestCase):
    def setUp(self):
        self.pub, self.draft = node("shown", "published"), node("hidden", "draft")
        self.c = Collections.from_nodes([self.pub, self.draft])
        self.prod = site_env.resolve({"SITE_ENV": "production"})

    def test_drafts_are_out_of_every_normal_collection(self):
        self.assertEqual([n.slug for n in self.c.articles], ["shown"])
        self.assertEqual([n.slug for n in self.c.drafts], ["hidden"])
        self.assertEqual([n.slug for n in self.c.tags["research"]], ["shown"])

    def test_articles_index_has_a_hidden_drafts_section_on_page_one_only(self):
        pages = anthus_pages.articles_collection(self.c.articles, None, self.c.drafts)
        page = pages[1]
        self.assertIn('<section class="drafts-review" hidden>', page)
        self.assertIn("DRAFT</span>", page)
        self.assertIn('rel="nofollow"', page)
        shown, _, drafts = page.partition('<section class="drafts-review"')
        self.assertIn("Shown", shown)
        self.assertNotIn("Hidden", shown)
        self.assertIn("Hidden", drafts)

    def test_card_dates_are_plain_dates_even_for_iso_timestamps(self):
        n = node("stamped", "published")
        n.front_matter["date"] = "2026-09-03T12:00:00-04:00"
        self.assertIn("<time>2026-09-03</time>", anthus_pages._text_card(n))

    def test_draft_cards_use_the_normal_card_markup(self):
        d = anthus_pages._text_card(self.draft, None, draft=True)
        n = anthus_pages._text_card(self.pub, None)
        for cls in ("card notch acard", "acard__vis", "acard__body"):
            self.assertIn(cls, d)
            self.assertIn(cls, n)

    def test_no_drafts_section_without_drafts(self):
        self.assertNotIn("drafts-review", anthus_pages.articles_collection(self.c.articles, None, [])[1])

    def test_research_index_lists_drafts_only_in_the_hidden_section(self):
        page = anthus_pages.research_page(self.c.blog)
        self.assertEqual(page.count("Hidden"), 1)
        self.assertGreater(page.index("Hidden"), page.index('class="drafts-review"'))

    def test_draft_page_head_has_noindex_in_production_and_a_normal_page_does_not(self):
        self.assertIn("noindex", site_env.head_extras(self.prod, draft=True))
        self.assertNotIn("noindex", site_env.head_extras(self.prod))

    def test_production_guard_allows_noindex_only_on_draft_pages(self):
        base = ('<link rel="canonical" href="https://anth.us/x/"><meta property="og:url" content="https://anth.us/x/">'
                + site_env.SITEMAP_LINK)
        draft = '<div class="draft-overlay"></div>' + site_env.NOINDEX_META + base
        normal_noindex = site_env.NOINDEX_META + base
        draft_without = '<div class="draft-overlay"></div>' + base
        self.assertEqual(site_env._check_page(self.prod, "a/index.html", draft), [])
        self.assertTrue(site_env._check_page(self.prod, "a/index.html", normal_noindex))
        self.assertTrue(site_env._check_page(self.prod, "a/index.html", draft_without))
        self.assertEqual(site_env._check_page(self.prod, "a/index.html", base), [])

    def test_draft_hrefs_leave_the_sitemap(self):
        build._DRAFT_HREFS.clear()
        build.register_article_metadata(self.c, _NoImages())
        try:
            self.assertEqual(build._DRAFT_HREFS, {"articles/hidden.html"})
            self.assertEqual(build._DRAFT_OUTPUTS(), {"articles/hidden/index.html"})
        finally:
            build._DRAFT_HREFS.clear()
            build._PAGE_META.clear()
            build._ARTICLE_LD.clear()


class _NoImages:
    def resolve_path(self, *a, **k):
        return None


if __name__ == "__main__":
    unittest.main()
