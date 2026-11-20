"""Content redirect stubs become legacy names (web/content-redirects, read by links.UrlMap)."""
import tempfile
import unittest
from pathlib import Path

import anthus_urls as urls
import support


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


class ProjectedContentRedirectStubs(unittest.TestCase):
    """The committed stubs of web/content-redirects reach the redirect store of a projection."""

    def test_the_stub_of_a_published_article_redirects_to_its_page(self):
        redirects = support.project_fixture().redirects
        self.assertEqual(redirects["/blog/inspected-by-sticker/"], "/articles/inspected-by-pudicus/")
        self.assertEqual(redirects["/blog/inspected-by-sticker/index.html"], "/articles/inspected-by-pudicus/")

    def test_a_stub_whose_article_is_not_in_the_corpus_redirects_nowhere(self):
        redirects = support.project_fixture().redirects
        self.assertEqual(redirects["/blog/pudicus/"], "/articles/inspected-by-pudicus/")
        self.assertNotIn("/blog/an-agent-skill-for-not-sounding-like-ai/", redirects)  # its article is not in the corpus


if __name__ == "__main__":
    unittest.main()
