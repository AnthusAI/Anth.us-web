"""`state: draft` articles: served, noindexed, left out of listings, tag pages and the sitemap, shown only via ?drafts."""
import json
import unittest
from pathlib import Path

import cards
import support
from anthus_content import Collections, ContentNode


def node(slug, state, tags=("articles", "research")):
    return ContentNode(slug=slug, source=Path(f"{slug}.mdx"), rel_dir="",
                       front_matter={"title": slug.title(), "state": state, "tags": list(tags),
                                     "date": "2026-09-01", "excerpt": "An excerpt."})


def split_drafts(html):
    """(the visible page, the hidden drafts section) of a listing page."""
    shown, _, drafts = html.partition('<section class="drafts-review"')
    return shown, drafts


class DraftCollections(unittest.TestCase):
    def setUp(self):
        self.pub, self.draft = node("shown", "published"), node("hidden", "draft")
        self.c = Collections.from_nodes([self.pub, self.draft])

    def test_drafts_are_out_of_every_normal_collection(self):
        self.assertEqual([n.slug for n in self.c.articles], ["shown"])
        self.assertEqual([n.slug for n in self.c.drafts], ["hidden"])
        self.assertEqual([n.slug for n in self.c.tags["research"]], ["shown"])

    def test_card_dates_are_plain_dates_even_for_iso_timestamps(self):
        n = node("stamped", "published")
        n.front_matter["date"] = "2026-09-03T12:00:00-04:00"
        self.assertIn("<time>2026-09-03</time>", cards._text_card(n))

    def test_draft_cards_use_the_normal_card_markup(self):
        d = cards._text_card(self.draft, None, draft=True)
        n = cards._text_card(self.pub, None)
        for cls in ("card notch acard", "acard__vis", "acard__body"):
            self.assertIn(cls, d)
            self.assertIn(cls, n)
        self.assertIn('rel="nofollow"', d)
        self.assertNotIn('rel="nofollow"', n)


class ProjectedDrafts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = support.project_fixture("production")
        cls.guarded = support.project_fixture("guarded")

    def test_a_draft_is_served_and_noindexed(self):
        page = self.production.page("/articles/draft-article/")
        self.assertIn("Draft body.", page)
        self.assertIn('<meta name="robots" content="noindex, nofollow">', page)
        self.assertNotIn('name="robots"', self.production.page("/articles/plain-article/"))

    def test_the_articles_index_has_a_hidden_drafts_section(self):
        page = self.production.page("/articles/")
        self.assertIn('<section class="drafts-review" hidden>', page)
        shown, drafts = split_drafts(page)
        self.assertIn("Plain Article", shown)
        self.assertNotIn("Hidden Draft", shown)
        self.assertIn("Hidden Draft", drafts)
        self.assertIn("DRAFT</span>", drafts)
        self.assertIn('rel="nofollow"', drafts)
        self.assertIn('href="/articles/draft-article/"', drafts)
        self.assertEqual(page.count("Hidden Draft"), 1)  # once, in the hidden section

    def test_the_drafts_script_ships_and_loads_on_every_page(self):
        self.assertIn("assets/drafts.js", self.production.files)
        self.assertIn("/assets/drafts.js?v=", self.production.page("/articles/"))

    def test_the_research_index_lists_drafts_only_in_the_hidden_section(self):
        page = self.production.page("/research/")
        self.assertEqual(page.count("Hidden Draft"), 1)
        shown, drafts = split_drafts(page)
        self.assertNotIn("Hidden Draft", shown)
        self.assertIn("Bias Experiment", shown)
        self.assertIn("Hidden Draft", drafts)

    def test_a_draft_is_in_no_other_listing_tag_page_or_index(self):
        for path in ("/", "/posts/", "/reading/", "/ryan/", "/ai-solutions/", "/tags/", "/tags/ai/", "/tags/research/", "/platform/"):
            self.assertNotIn("Hidden Draft", self.production.page(path), path)
            self.assertNotIn("draft-article", self.production.page(path), path)
        self.assertNotIn("draft-article", self.production.page("/articles/call-criteria/"))

    def test_draft_hrefs_leave_the_sitemap_and_the_public_data(self):
        for key in ("sitemap-0.xml", "_data/search-index.json", "_data/latest.json"):
            self.assertNotIn("draft-article", self.production.text(key), key)
        self.assertNotIn("/articles/draft-article/", self.production.text("sitemap-0.xml"))
        self.assertIn("/articles/plain-article/", self.production.text("sitemap-0.xml"))
        self.assertEqual({entry.get("title") for entry in json.loads(self.production.text("_data/search-index.json"))} & {"Hidden Draft"}, set())

    def test_a_guarded_page_is_noindex_draft_or_not(self):
        for path in ("/articles/draft-article/", "/articles/plain-article/"):
            self.assertIn("noindex", self.guarded.page(path), path)

    def test_the_drafts_section_is_on_page_one_only(self):
        extra = {f"articles/filler-{number:02d}.md": support.article_text(f"Filler {number:02d}", date=f"2024-01-{number:02d}") for number in range(1, 13)}
        projection = support.project_directory(support.corpus_with(extra))
        first, second = projection.page("/articles/"), projection.page("/articles/page/2/")
        self.assertIn('<section class="drafts-review" hidden>', first)
        self.assertIn("Hidden Draft", split_drafts(first)[1])
        self.assertNotIn("drafts-review", second)
        self.assertNotIn("Hidden Draft", second)
        self.assertIn("Page 2 of 2", second)

    def test_no_drafts_section_without_drafts(self):
        projection = support.project_directory(support.corpus_with({}, without=("articles/draft-article.md",)))
        self.assertNotIn("drafts-review", projection.page("/articles/"))
        self.assertNotIn("drafts-review", projection.page("/research/"))


if __name__ == "__main__":
    unittest.main()
