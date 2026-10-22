"""The tag-driven lists of the authored pages: engagements, featured work, integrations, further reading.

web/pages/ryan.md and web/pages/ai-solutions.md select items by tag (``::include{kind="listing" ...}``). The corpus has
no integration today, so the empty list is pinned as well as the list with one item.
"""
import re
import unittest

import support


def section(html, heading):
    """The ``<section>`` of a page whose ``<h2>`` is ``heading``."""
    start = html.index(f"<h2>{heading}</h2>")
    return html[start : html.index("</section>", start)]


def titles(html):
    return re.findall(r'<h3>(?:<a [^>]*>)?([^<]+)', html)


INTEGRATION = support.article_text("Salesforce Hook", date="2024-05-01", tags=("solutions", "integrations"), extra="authors:\n  - author: '<a href=\"/ryan\">Ryan Porter</a>'\n")
ENGAGED_INTEGRATION = support.article_text("Marketing Sync", date="2024-06-01", tags=("solutions", "engagement", "integrations"))
DRAFT_ENGAGEMENT = support.article_text("Draft Engagement", date="2024-07-01", tags=("solutions", "engagement"), state="draft")


class SolutionLists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()

    def test_engagements_are_the_published_solutions_tagged_engagement(self):
        engagements = section(self.projection.page("/ai-solutions/"), "Client work with a business outcome")
        self.assertEqual(sorted(titles(engagements)), ["Call Criteria", "Venue Driver"])  # not the folded items, no draft, no featured-only item

    def test_the_portfolio_splits_featured_work_from_the_rest_and_keeps_integrations_apart(self):
        ryan = self.projection.page("/ryan/")
        portfolio = section(ryan, "Systems and projects")
        self.assertEqual(sorted(titles(portfolio)), ["Call Criteria", "Robot Routing", "Venue Driver"])
        featured, _, others = portfolio.partition('<ul class="grid grid--list">')[2].partition('<ul class="grid grid--list">')
        self.assertEqual(sorted(titles(featured)), ["Call Criteria", "Robot Routing"])
        self.assertEqual(titles(others), ["Venue Driver"])

    def test_with_no_integrations_the_integrations_section_has_no_list(self):
        integrations = section(self.projection.page("/ryan/"), "What we connect to")
        self.assertEqual(titles(integrations), [])
        self.assertNotIn("<li", integrations)

    def test_further_reading_is_the_newest_projects_and_featured_articles(self):
        reading = section(self.projection.page("/ai-solutions/"), "Projects and articles")
        names = re.findall(r"<a href=\"[^\"]+\">([^<]+)</a></li>", reading)
        self.assertEqual(names, ["Project Notes", "Robot Routing"])  # newest first; engagements are not repeated


class SolutionListsWithIntegrations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        extra = {
            "articles/salesforce-hook.md": INTEGRATION,
            "articles/marketing-sync.md": ENGAGED_INTEGRATION,
            "articles/draft-engagement.md": DRAFT_ENGAGEMENT,
        }
        cls.projection = support.project_directory(support.corpus_with(extra))

    def test_an_integration_is_listed_under_integrations_only(self):
        ryan = self.projection.page("/ryan/")
        self.assertEqual(sorted(titles(section(ryan, "What we connect to"))), ["Marketing Sync", "Salesforce Hook"])
        self.assertNotIn("Salesforce Hook", section(ryan, "Systems and projects"))
        self.assertNotIn("Marketing Sync", section(ryan, "Systems and projects"))

    def test_an_integration_is_not_an_engagement_even_when_tagged_so(self):
        engagements = section(self.projection.page("/ai-solutions/"), "Client work with a business outcome")
        self.assertEqual(sorted(titles(engagements)), ["Call Criteria", "Venue Driver"])

    def test_integrations_stay_out_of_further_reading_and_a_draft_out_of_every_list(self):
        for path in ("/ai-solutions/", "/ryan/", "/"):
            html = self.projection.page(path)
            self.assertNotIn("Draft Engagement", html, path)
        reading = section(self.projection.page("/ai-solutions/"), "Projects and articles")
        self.assertNotIn("Salesforce Hook", reading)
        self.assertNotIn("Marketing Sync", reading)
        self.assertIn("Draft Engagement", self.projection.page("/articles/draft-engagement/"))  # served, noindexed
        self.assertIn("noindex", self.projection.page("/articles/draft-engagement/"))


if __name__ == "__main__":
    unittest.main()
