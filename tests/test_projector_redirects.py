"""The redirect rules and static files of the Anth.us projection (PPY-f1df00)."""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import anthus_urls
import links
import support

REPOSITORY = Path(__file__).resolve().parent.parent
WEB = REPOSITORY / "web"


def rule(source, target, status="301"):
    return {"source": source, "target": target, "status": status}


class EffectiveExactRedirects(unittest.TestCase):
    def test_an_exact_rule_listed_after_a_matching_pattern_never_fired(self):
        rules = [rule("/blog/<slug>/", "/articles/<slug>/"), rule("/blog/plexus/", "/articles/primus/")]
        self.assertEqual(links.effective_exact_redirects(rules, set()), {})

    def test_an_exact_rule_listed_before_the_pattern_is_kept(self):
        rules = [rule("/blog/ai/", "/tags/ai/"), rule("/blog/<slug>/", "/articles/<slug>/")]
        self.assertEqual(links.effective_exact_redirects(rules, set()), {"/blog/ai/": "/tags/ai/"})

    def test_a_placeholder_matches_one_segment_and_a_star_matches_the_rest(self):
        rules = [rule("/a/<name>/", "/b/"), rule("/c/<*>", "/d/"), rule("/a/x/y/", "/kept/"), rule("/c/x/y", "/dead/")]
        self.assertEqual(links.effective_exact_redirects(rules, set()), {"/a/x/y/": "/kept/"})

    def test_a_rule_never_hides_a_page_and_the_catch_all_is_not_a_redirect(self):
        rules = [rule("/about/", "/elsewhere/"), rule("/old/", "/new/"), rule("/<*>", "/404.html", "404-200")]
        self.assertEqual(links.effective_exact_redirects(rules, {"/about/"}), {"/old/": "/new/"})

    def test_the_first_rule_for_a_source_wins(self):
        rules = [rule("/old/", "/first/"), rule("/old/", "/second/")]
        self.assertEqual(links.effective_exact_redirects(rules, set()), {"/old/": "/first/"})


class ProjectedRedirects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()

    def test_a_redirect_never_hides_a_page_of_the_projection(self):
        pages = set()
        for key in self.projection.files:
            if key.endswith("index.html"):
                pages.add("/" + key[: -len("index.html")])
                pages.add("/" + key)
        pages.add("/404.html")
        self.assertEqual(pages & set(self.projection.redirects), set())

    def test_the_store_holds_only_exact_301_sources(self):
        for source, target in self.projection.redirects.items():
            self.assertTrue(source.startswith("/"), source)
            self.assertNotIn("<", source)
            self.assertNotIn("<", target)
            self.assertNotEqual(target, "/404.html")

    def test_the_legacy_snapshot_keeps_the_catch_all_last(self):
        legacy = json.loads((WEB / "legacy-redirect-rules.json").read_text(encoding="utf-8"))
        self.assertEqual(legacy[-1], rule("/<*>", "/404.html", "404-200"))

    def test_the_old_listing_tag_and_share_image_urls_are_redirected(self):
        redirects = self.projection.redirects
        self.assertEqual(redirects["/blog/"], "/articles/")
        self.assertEqual(redirects["/blog/index.html"], "/articles/")
        self.assertEqual(redirects["/blog/page/1/"], "/articles/")
        for tag in ("solutions", "decision-models", "research", "reading", "posts"):
            self.assertEqual(redirects[f"/blog/{tag}/"], f"/tags/{tag}/", tag)
            self.assertEqual(redirects[f"/blog/{tag}/index.html"], f"/tags/{tag}/", tag)
        shared = {s: t for s, t in redirects.items() if s.startswith("/static/")}
        self.assertTrue(shared)
        self.assertTrue(all(t.startswith("/assets/") for t in shared.values()), shared)

    def test_generic_blog_urls_are_the_pattern_rules_not_the_store(self):
        raw = json.loads((WEB / "projection.json").read_text(encoding="utf-8"))["redirects"]["patterns"]
        self.assertIn("^/blog/([^/]+)/$", [entry["pattern"] for entry in raw])
        self.assertNotIn("/blog/plain-article/", self.projection.redirects)  # covered by /blog/<slug>/
        self.assertNotIn("/blog/venue-driver/", self.projection.redirects)

    def test_renamed_pages_redirect_to_their_new_names(self):
        for old, new in anthus_urls.RENAMED_PAGE_REDIRECTS:
            if old in self.projection.redirects:
                self.assertEqual(self.projection.redirects[old], new)


class CommittedStaticFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = support.project_fixture()

    def test_the_committed_static_files_are_projected_byte_for_byte(self):
        files = self.projection.files
        self.assertEqual(files["css/site-theme.css"], (WEB / "css" / "site-theme.css").read_bytes())
        self.assertEqual(files["assets/site-nav.js"], (WEB / "assets" / "site-nav.js").read_bytes())
        self.assertEqual(files["engage-inquiry.js"], (WEB / "static-root" / "engage-inquiry.js").read_bytes())
        self.assertIn("favicon-32x32.png", files)
        self.assertIn("manifest.webmanifest", files)
        self.assertTrue(any(key.startswith("assets/site/") for key in files))
        self.assertTrue(any(key.startswith("icons/") for key in files))
        self.assertNotIn("css/anthus-theme.css", files)
        self.assertNotIn("css/arcade.css", files)

    def test_the_stylesheet_is_linked_with_one_cache_busting_token(self):
        tokens = set()
        for path in ("/", "/about/", "/articles/call-criteria/", "/platform/"):
            tokens |= set(re.findall(r'href="/css/site-theme\.css\?v=([0-9a-f]+)"', self.projection.page(path)))
            tokens |= set(re.findall(r'src="/assets/[a-z-]+\.js\?v=([0-9a-f]+)"', self.projection.page(path)))
        self.assertEqual(len(tokens), 1, tokens)
        self.assertRegex(tokens.pop(), r"^[0-9a-f]{12}$")

    def test_the_cache_busting_token_changes_with_the_stylesheet(self):
        import shutil

        work = Path(tempfile.mkdtemp(prefix="anthus-web-", dir=os.environ.get("ANTHUS_BUILD_DIR"))) / "web"
        shutil.copytree(WEB, work, ignore=shutil.ignore_patterns("__pycache__"))  # a copy of web/ whose stylesheet differs
        token = re.compile(r"site-theme\.css\?v=([0-9a-f]+)")
        empty = Path(tempfile.mkdtemp(prefix="anthus-token-content-", dir=os.environ.get("ANTHUS_BUILD_DIR")))
        (empty / "articles").mkdir()
        same = token.search(support.project_directory(empty).page("/about/")).group(1)
        self.assertEqual(same, token.search(self.projection.page("/about/")).group(1))
        stylesheet = work / "css" / "site-theme.css"
        stylesheet.write_bytes(stylesheet.read_bytes() + b"\n/* changed */\n")
        context = support.make_context(empty, Path(tempfile.mkdtemp(dir=os.environ.get("ANTHUS_BUILD_DIR"))), keep_state=False)
        with support.site_environment("production"):
            from papyrus_content.projection.projector import MarkusSiteProjector

            context.projector = MarkusSiteProjector.from_static_directory(work, renditions=support.FakeRenditionStore())
        from papyrus_content.projection.engine import project_all

        project_all(context)
        changed = (context.writer._root / "about" / "index.html").read_text(encoding="utf-8")
        self.assertNotEqual(same, token.search(changed).group(1))


if __name__ == "__main__":
    unittest.main()
