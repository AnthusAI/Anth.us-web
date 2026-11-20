"""The published robots.txt names Google's two crawlers as allowed (projection.json ``robots.extra``).

Some tools only read a site when its crawler rules say so in words, not by saying nothing.

Gherkin (observable behaviour; the executable checks are below):

  Scenario: Google's crawlers are allowed by name
    When the site is projected for production
    Then robots.txt allows everyone, then names Googlebot and Google-Extended, each allowed to read everything
    And it blocks nobody
    And it ends by pointing to the sitemap

  Scenario: A site that is not the production site is still closed
    When the site is projected for a non-production origin
    Then robots.txt blocks every crawler and names no one as allowed
"""

from __future__ import annotations

import unittest

from support import project_fixture


class RobotsTest(unittest.TestCase):
    def test_google_crawlers_are_allowed_by_name(self):
        robots = project_fixture().text("robots.txt")
        self.assertTrue(robots.startswith("User-agent: *\nAllow: /\n"), robots)
        self.assertIn("\nUser-agent: Googlebot\nAllow: /\n", robots)
        self.assertIn("\nUser-agent: Google-Extended\nAllow: /\n", robots)
        self.assertNotIn("Disallow", robots)
        self.assertTrue(robots.rstrip().splitlines()[-1].startswith("Sitemap: https://"), robots)

    def test_a_staging_origin_stays_closed_to_everyone(self):
        robots = project_fixture("guarded").text("robots.txt")
        self.assertEqual(robots, "User-agent: *\nDisallow: /\n")
        self.assertNotIn("Google-Extended", robots)


if __name__ == "__main__":
    unittest.main()
