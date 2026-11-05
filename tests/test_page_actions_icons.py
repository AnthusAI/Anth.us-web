"""Article page actions render as icon buttons (projection.json ``pageActions.display: "icons"``).

Gherkin (observable behaviour; the executable checks are below):

  Scenario: An article shows its page actions as icons
    Given the site configures page actions with display "icons"
    When an article page is projected
    Then the page has an icon row with "View as Markdown" and "Copy Markdown" buttons that each carry a text name
    And the AI assistants stay as links in the "More" menu, with their names in words
    And no X, Reddit or Share action is added

  Scenario: The icon row has its stylesheet and script
    When an article page is projected
    Then the head links the page-actions stylesheet and the body loads the page-actions script
    And the site bucket carries both files

  Scenario: An authored page does not grow an icon row
    When the home page is projected
    Then its body carries no page actions (core still links the stylesheet and script on authored pages)
"""

from __future__ import annotations

import re
import unittest

from support import project_fixture

ARTICLE = "/articles/plain-article/"


class IconPageActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = project_fixture()
        cls.article = cls.projection.page(ARTICLE)

    def test_the_article_has_the_icon_row_with_a_name_on_every_button(self):
        self.assertIn("markus-page-actions-icons", self.article)
        self.assertRegex(self.article, r'<a class="markus-action-link markus-icon-action" data-action="view"[^>]*aria-label="View as Markdown" title="View as Markdown"')
        self.assertRegex(self.article, r'<button type="button" class="markus-copy-md markus-icon-action" data-action="copy" aria-label="Copy Markdown" title="Copy Markdown">')
        self.assertEqual(self.article.count('class="markus-action-icon"'), 2)
        self.assertNotRegex(self.article, r">Copy Markdown</button>")

    def test_the_assistants_stay_as_named_links(self):
        for name in ("chatgpt", "claude", "perplexity"):
            self.assertRegex(self.article, rf'data-action="{name}" href="https://')
        for label in ("Open in ChatGPT", "Open in Claude", "Open in Perplexity"):
            self.assertIn(f">{label}</a>", self.article)

    def test_no_social_or_share_action_is_added(self):
        for name in ("x", "reddit"):
            self.assertNotIn(f'data-action="{name}"', self.article)
        self.assertNotIn("data-share", self.article)

    def test_the_stylesheet_and_script_are_linked_and_published(self):
        self.assertRegex(self.article, r'<link rel="stylesheet" href="/_plugins/papyrus-page-actions\.css')
        self.assertRegex(self.article, r'<script[^>]* src="/_plugins/papyrus-page-actions-v1\.js')
        self.assertIn("_plugins/papyrus-page-actions.css", self.projection.files)
        self.assertIn("_plugins/papyrus-page-actions-v1.js", self.projection.files)
        self.assertIn(".markus-page-actions-icons", self.projection.text("_plugins/papyrus-page-actions.css"))

    def test_an_authored_page_has_no_icon_row(self):
        self.assertNotIn("data-papyrus-page-actions", self.projection.page("/"))


if __name__ == "__main__":
    unittest.main()
