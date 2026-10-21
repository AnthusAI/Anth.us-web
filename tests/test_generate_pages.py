"""generate_pages / register_article_metadata (PPY-aebfcd).

Needs PAPYRUS_ROOT and the build requirements (Markus, Pillow, PyYAML,
citeproc-py); skipped when the build module cannot be imported.
Run: PAPYRUS_ROOT=/path/to/Papyrus python3 tests/test_generate_pages.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

try:
    import build_via_papyrus as build
    from anthus_content import Collections
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    build = None
    IMPORT_ERROR = error

EXPECTED_GENERATED_HREFS = {
    "404.html",
    "about.html",
    "ai-solutions.html",
    "articles/index.html",
    "benchmarks.html",
    "decision-models.html",
    "engage.html",
    "index.html",
    "platform/index.html",
    "posts/index.html",
    "reading.html",
    "research.html",
    "ryan.html",
    "tags/index.html",
}


class ImageIndexThatMustNotBeTouched:
    def __getattr__(self, name):
        raise AttributeError(name)


@unittest.skipIf(build is None, f"build module unavailable: {IMPORT_ERROR}")
class GeneratePagesOnEmptyCollections(unittest.TestCase):
    def setUp(self):
        self.state = build.SiteState()
        self.collections = Collections.from_nodes([])
        self.images = ImageIndexThatMustNotBeTouched()

    def test_generates_exactly_the_fixed_page_set(self):
        build.generate_pages(self.state, self.collections, self.images)
        self.assertEqual(set(self.state.generated), EXPECTED_GENERATED_HREFS)
        for href, (title, fragment) in self.state.generated.items():
            self.assertTrue(title, href)
            self.assertTrue(fragment.strip(), href)

    def test_registers_metadata_for_pages_with_a_meta_key(self):
        build.generate_pages(self.state, self.collections, self.images)
        for href in ("about.html", "ryan.html", "platform/index.html", "articles/index.html"):
            self.assertIn(href, self.state.page_meta)

    def test_is_deterministic(self):
        build.generate_pages(self.state, self.collections, self.images)
        first_pages = dict(self.state.generated)
        first_meta = dict(self.state.page_meta)
        build.generate_pages(self.state, self.collections, self.images)
        self.assertEqual(self.state.generated, first_pages)
        self.assertEqual(self.state.page_meta, first_meta)

    def test_register_article_metadata_without_articles_registers_nothing(self):
        build.register_article_metadata(self.state, self.collections, self.images)
        self.assertEqual(self.state.page_meta, {})
        self.assertEqual(self.state.article_ld, {})


if __name__ == "__main__":
    unittest.main()
