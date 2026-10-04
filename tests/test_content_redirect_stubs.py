"""Content redirect stubs become legacy names: python3 tests/test_content_redirect_stubs.py"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
import anthus_urls as urls  # noqa: E402


def write_stub(redirect_stubs_directory: Path, name: str, target_path: str) -> None:
    stub_directory = redirect_stubs_directory / name
    stub_directory.mkdir(parents=True)
    (stub_directory / "index.html").write_text(
        f'<!doctype html><meta http-equiv="refresh" content="0; url={target_path}">',
        encoding="utf-8",
    )


class ContentRedirectStubs(unittest.TestCase):
    def site_urls_with_one_article(self) -> urls.SiteUrls:
        site_urls = urls.SiteUrls()
        site_urls.article_by_name["inspected-by-pudicus"] = "inspected-by-pudicus"
        site_urls.blog_names["inspected-by-pudicus"] = "inspected-by-pudicus"
        return site_urls

    def test_a_stub_name_redirects_to_the_article_it_points_at(self):
        site_urls = self.site_urls_with_one_article()
        with tempfile.TemporaryDirectory() as directory:
            write_stub(Path(directory), "inspected-by-sticker", "/blog/inspected-by-pudicus/")
            site_urls.add_content_redirect_stubs(Path(directory))
        self.assertEqual(site_urls.blog_names["inspected-by-sticker"], "inspected-by-pudicus")
        rules = urls.legacy_rules(site_urls)
        sources_to_targets = {rule["source"]: rule["target"] for rule in rules.rules}
        self.assertEqual(
            sources_to_targets.get("/blog/inspected-by-sticker/"),
            urls.page_url("articles/inspected-by-pudicus.html"),
        )

    def test_a_stub_pointing_at_an_unknown_article_is_ignored(self):
        site_urls = self.site_urls_with_one_article()
        with tempfile.TemporaryDirectory() as directory:
            write_stub(Path(directory), "orphan", "/blog/no-such-article/")
            site_urls.add_content_redirect_stubs(Path(directory))
        self.assertNotIn("orphan", site_urls.blog_names)

    def test_a_missing_redirects_directory_changes_nothing(self):
        site_urls = self.site_urls_with_one_article()
        site_urls.add_content_redirect_stubs(Path("/nonexistent/redirects"))
        self.assertEqual(set(site_urls.blog_names), {"inspected-by-pudicus"})


if __name__ == "__main__":
    unittest.main()
