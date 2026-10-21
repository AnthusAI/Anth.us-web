"""Items that live on their own site emit no page from the projector (full or incremental)."""
import unittest
from types import SimpleNamespace

import hooks
import support
from solution_sites import EXTERNAL_SITES


def summary(section, stem):
    return SimpleNamespace(section=section, output_path=f"{section}/{stem}.mdx", front_matter={"title": stem})


class ExternalSolutionItems(unittest.TestCase):
    def test_the_four_items_are_left_out_of_the_site(self):
        for slug in EXTERNAL_SITES:
            self.assertFalse(hooks.item_filter(summary("platform", slug)), slug)

    def test_other_platform_items_and_articles_stay_in_the_site(self):
        self.assertTrue(hooks.item_filter(summary("platform", "biblicus")))
        self.assertTrue(hooks.item_filter(summary("articles", "x")))

    def test_the_projected_item_pages_follow_the_filter(self):
        files = support.project_fixture().files
        for slug in EXTERNAL_SITES:
            self.assertNotIn(f"platform/{slug}/index.html", files, slug)
        self.assertIn("platform/biblicus/index.html", files)
        self.assertIn("platform/auritus/index.html", files)
        self.assertIn("articles/plain-article/index.html", files)

    def test_an_incremental_projection_of_one_of_them_writes_no_page(self):
        import tempfile

        from papyrus_content.projection.engine import project

        out = tempfile.mkdtemp(prefix="anthus-external-", dir=support.os.environ.get("ANTHUS_BUILD_DIR"))
        context = support.make_context(support.FIXTURE_CONTENT, support.Path(out), keep_state=True)
        report = project(context, "file:platform/primus.md")
        self.assertTrue(report.ok, report.errors)
        self.assertFalse([key for key in report.written if "platform/primus/" in key])
        report = project(context, "file:platform/biblicus.md")
        self.assertIn("platform/biblicus/index.html", report.written)


if __name__ == "__main__":
    unittest.main()
