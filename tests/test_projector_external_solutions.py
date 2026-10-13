"""Items that live on their own site emit no page from the projector (full or incremental)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

try:
    import projector
    from solution_sites import EXTERNAL_SITES
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    projector = None
    IMPORT_ERROR = error


def summary(section, stem):
    return SimpleNamespace(section=section, output_path=f"{section}/{stem}.mdx", front_matter={"title": stem})


@unittest.skipIf(projector is None, f"projector unavailable: {IMPORT_ERROR}")
class ExternalSolutionItems(unittest.TestCase):
    def setUp(self):
        self.projector = projector.AnthusProjector.__new__(projector.AnthusProjector)

    def test_the_four_items_have_no_page_path(self):
        for slug in EXTERNAL_SITES:
            self.assertEqual(self.projector.item_page_paths(summary("platform", slug)), (), slug)

    def test_item_pages_renders_nothing_for_them(self):
        for slug in EXTERNAL_SITES:
            item = SimpleNamespace(summary=summary("platform", slug))
            self.assertEqual(self.projector.item_pages(item, site=None), {}, slug)

    def test_other_platform_items_and_articles_keep_their_page(self):
        self.assertEqual(self.projector.item_page_paths(summary("platform", "biblicus")), ("platform/biblicus/index.html",))
        self.assertEqual(self.projector.item_page_paths(summary("articles", "x")), ("articles/x/index.html",))


if __name__ == "__main__":
    unittest.main()
