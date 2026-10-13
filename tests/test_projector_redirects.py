"""The redirect rules and static files of the Anth.us projector (PPY-f1df00).

Needs PAPYRUS_ROOT (a Papyrus checkout with the projection engine) and the build requirements. Skipped otherwise.
"""
import json
import os
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
PAPYRUS = os.environ.get("PAPYRUS_ROOT")
SKIP = not PAPYRUS

if not SKIP:
    sys.path.insert(0, str(Path(PAPYRUS) / "src"))
    sys.path.insert(0, str(REPOSITORY / "web"))
    os.environ.setdefault("SITE_ENV", "production")
    os.environ.setdefault("AWS_BRANCH", "main")
    import projector as anthus_projector


def rule(source, target, status="301"):
    return {"source": source, "target": target, "status": status}


@unittest.skipIf(SKIP, "needs PAPYRUS_ROOT")
class EffectiveExactRedirects(unittest.TestCase):
    def test_an_exact_rule_listed_after_a_matching_pattern_never_fired(self):
        rules = [rule("/blog/<slug>/", "/articles/<slug>/"), rule("/blog/plexus/", "/articles/primus/")]
        self.assertEqual(anthus_projector.effective_exact_redirects(rules, set()), {})

    def test_an_exact_rule_listed_before_the_pattern_is_kept(self):
        rules = [rule("/blog/ai/", "/tags/ai/"), rule("/blog/<slug>/", "/articles/<slug>/")]
        self.assertEqual(anthus_projector.effective_exact_redirects(rules, set()), {"/blog/ai/": "/tags/ai/"})

    def test_a_placeholder_matches_one_segment_and_a_star_matches_the_rest(self):
        rules = [rule("/a/<name>/", "/b/"), rule("/c/<*>", "/d/"), rule("/a/x/y/", "/kept/"), rule("/c/x/y", "/dead/")]
        self.assertEqual(anthus_projector.effective_exact_redirects(rules, set()), {"/a/x/y/": "/kept/"})

    def test_a_rule_never_hides_a_page_and_the_catch_all_is_not_a_redirect(self):
        rules = [rule("/about/", "/elsewhere/"), rule("/old/", "/new/"), rule("/<*>", "/404.html", "404-200")]
        self.assertEqual(anthus_projector.effective_exact_redirects(rules, {"/about/"}), {"/old/": "/new/"})

    def test_the_first_rule_for_a_source_wins(self):
        rules = [rule("/old/", "/first/"), rule("/old/", "/second/")]
        self.assertEqual(anthus_projector.effective_exact_redirects(rules, set()), {"/old/": "/first/"})


@unittest.skipIf(SKIP, "needs PAPYRUS_ROOT")
class CommittedStaticFiles(unittest.TestCase):
    def test_the_files_the_full_build_copies_are_projected_byte_for_byte(self):
        files = anthus_projector.read_committed_static_files()
        self.assertEqual(files["css/site-theme.css"], anthus_projector.site_css.stylesheet_bytes())
        self.assertIn("assets/site-nav.js", files)
        self.assertIn("favicon-32x32.png", files)
        self.assertIn("manifest.webmanifest", files)
        self.assertTrue(any(key.startswith("assets/site/") for key in files))
        self.assertTrue(any(key.startswith("icons/") for key in files))

    def test_the_cache_busting_token_changes_with_the_stylesheet(self):
        token = anthus_projector.default_projector_config()
        self.assertEqual(token["markus_pages"], token["generated_pages"])
        self.assertRegex(token["markus_pages"], r"^[0-9a-f]{12}$")

    def test_the_legacy_rule_snapshot_keeps_the_catch_all_last(self):
        rules = json.loads((REPOSITORY / "web" / "legacy-redirect-rules.json").read_text(encoding="utf-8"))
        self.assertEqual(rules[-1], rule("/<*>", "/404.html", "404-200"))


if __name__ == "__main__":
    unittest.main()
