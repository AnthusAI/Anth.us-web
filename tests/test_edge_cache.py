"""The published site expires on its own and is not purged on every change (papyrus.config.ts ``publication.cache``).

CloudFront bills each purged path after the first thousand a month. The newsroom board alone caused about 80 purges a day, so the site is eventually
consistent instead: the edge keeps a page for an hour.

Gherkin (observable behaviour; the executable check is below):

  Scenario: Publishing does not purge the edge
    Given the site's backend configuration
    Then it turns edge invalidation off
    And it lets the edge keep a page for 3600 seconds
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent


class EdgeCacheTest(unittest.TestCase):
    def test_the_edge_is_not_purged_and_keeps_a_page_for_an_hour(self):
        config = (REPOSITORY / "papyrus.config.ts").read_text(encoding="utf-8")
        self.assertIn('cache: { invalidation: "off", htmlSMaxAgeSeconds: 3600 }', config)


if __name__ == "__main__":
    unittest.main()
