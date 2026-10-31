"""The /newsroom/ section: stories and Reference grids on one page, a nav link, and no other page changed (PPY-e346f6).

The Reference grids render from the home-page snapshot. These tests use a small synthetic snapshot
(tests/fixtures/home-page) so they need no AWS access; the page is checked against the real snapshot by hand
before each change to it.
"""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import anthus_dom
import support
from papyrus_content.projection.directory_source import DirectoryContentSource
from papyrus_content.projection.engine import ProjectionContext, project_all
from papyrus_content.projection.projector import MarkusSiteProjector
from papyrus_content.projection.writers import LocalDirectoryWriter

WEB = support.WEB
SNAPSHOT_DIRECTORY = Path(__file__).resolve().parent / "fixtures" / "home-page" / "_data" / "home-page"
INCLUDE_LINES = (
    '::include{kind="references" select="recent" count="6" card="tile"}',
    '::include{kind="references" select="confident" count="6" card="row"}',
    '::include{kind="references" select="recommended" count="6" card="row" empty="Nothing is waiting for review right now."}',
)
THREADS_INCLUDE_LINE = '::include{kind="threads" select="recent" count="6" layout="list" empty="No conversations yet."}'

STYLESHEET_LINK = re.compile(r'<link rel="stylesheet" href="/css/papyrus-home-page\.css\?v=[0-9a-f]+">\n?')
ASSET_VERSION = re.compile(r"\?v=[0-9a-f]{12}|__markusAssetVersion = \"[0-9a-f]{12}\"")
NAV_ITEM = re.compile(r'<li><a href="/newsroom/"[^>]*>Newsroom</a></li>')


def project(static_directory: Path, snapshot: Path | None):
    out = Path(tempfile.mkdtemp(prefix="anthus-newsroom-", dir=support.os.environ.get("ANTHUS_BUILD_DIR")))
    with support.site_environment("production"):
        projector = MarkusSiteProjector.from_static_directory(static_directory, renditions=support.FakeRenditionStore())
    if snapshot is not None:
        projector.use_home_page_directory(snapshot)
    context = ProjectionContext(
        source=DirectoryContentSource(support.FIXTURE_CONTENT),
        projector=projector,
        writer=LocalDirectoryWriter(out),
        redirect_store=support.MemoryRedirectStore(),
    )
    report = project_all(context)
    assert report.ok, report.errors
    return support.Projection(out=out, redirects=dict(context.redirect_store.mapping), report=report)


def static_directory_without_the_opt_in() -> Path:
    path = Path(tempfile.mkdtemp(prefix="anthus-web-", dir=support.os.environ.get("ANTHUS_BUILD_DIR"))) / "web"
    shutil.copytree(WEB, path, ignore=shutil.ignore_patterns("__pycache__", ".image-cache"))
    settings = json.loads((path / "projection.json").read_text(encoding="utf-8"))
    del settings["homePage"]
    settings["pages"] = [page for page in settings["pages"] if page["id"] != "newsroom"]
    (path / "projection.json").write_text(json.dumps(settings), encoding="utf-8")
    (path / "pages" / "newsroom.md").unlink()
    return path


class NewsroomSection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.populated = project(WEB, SNAPSHOT_DIRECTORY)
        cls.empty = project(WEB, None)
        cls.baseline = project(static_directory_without_the_opt_in(), None)

    def test_the_page_and_its_markdown_twin_are_projected_and_listed(self):
        self.assertIn("newsroom/index.html", self.populated.files)
        self.assertIn("newsroom/index.md", self.populated.files)
        self.assertIn("(https://anth.us/newsroom/index.md)", self.populated.text("llms.txt"))
        self.assertIn("<loc>https://anth.us/newsroom/</loc>", self.populated.text("sitemap-0.xml"))

    def test_the_markdown_twin_keeps_the_three_references_include_lines(self):
        twin = self.populated.text("newsroom/index.md")
        for line in INCLUDE_LINES:
            self.assertIn(line, twin)

    def test_the_page_mixes_story_listings_with_the_three_reference_grids(self):
        main = self.populated.main("/newsroom/")
        self.assertEqual(re.findall(r'class="home-page-references" data-select="(\w+)"', main), ["recent", "confident", "recommended"])
        self.assertIn("mini-grid", main)
        self.assertIn("Fixture source number 8", main)
        self.assertIn("% confidence", main)
        self.assertIn("Recommended by Cyclotron, not yet accepted", main)

    def test_a_reference_appears_once_on_the_page(self):
        main = self.populated.main("/newsroom/")
        for number in range(1, 13):
            self.assertLessEqual(main.count(f"Fixture source number {number}<"), 1, number)

    def test_without_a_snapshot_the_page_still_builds_and_says_nothing_is_waiting(self):
        main = self.empty.main("/newsroom/")
        self.assertIn("Nothing is waiting for review right now.", main)
        self.assertNotIn("home-page-tile", main)

    def test_the_page_carries_no_identity_shaped_text(self):
        for key in ("newsroom/index.html", "newsroom/index.md"):
            self.assertEqual(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", self.populated.text(key)), [], key)


class ConversationsSection(unittest.TestCase):
    """Feature: The Anth.us newsroom page shows conversations.

    A visitor reading the newsroom sees the most recent public conversations under section 06. Each shows what it is
    about, how many messages it holds and the latest message, written by a public handle or the Editor label, and no
    page or data file carries an email address, a subject or a UUID.
    """

    @classmethod
    def setUpClass(cls):
        cls.populated = project(WEB, SNAPSHOT_DIRECTORY)
        cls.empty = project(WEB, None)

    def test_a_public_thread_appears_in_the_conversations_section(self):
        main = self.populated.main("/newsroom/")
        self.assertIn("<span>06</span>", main)
        self.assertEqual(re.findall(r'class="home-page-threads" data-layout="(\w+)"', main), ["list"])
        self.assertIn("Is this source worth keeping?", main)
        self.assertIn("2 messages", main)
        self.assertIn("by fixturehandle", main)
        self.assertIn("Yes, the method section holds up.", main)

    def test_the_markdown_twin_keeps_the_threads_include_line(self):
        self.assertIn(THREADS_INCLUDE_LINE, self.populated.text("newsroom/index.md"))

    def test_without_threads_the_section_says_there_are_no_conversations_yet(self):
        main = self.empty.main("/newsroom/")
        self.assertIn("No conversations yet.", main)
        self.assertNotIn("home-page-thread\"", main)

    def test_no_email_sub_or_uuid_appears_on_the_page_or_in_the_data_files(self):
        shaped = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
        texts = [self.populated.text("newsroom/index.html"), self.populated.text("newsroom/index.md")]
        texts += [path.read_text(encoding="utf-8") for path in SNAPSHOT_DIRECTORY.rglob("threads*.json")]
        texts += [path.read_text(encoding="utf-8") for path in (SNAPSHOT_DIRECTORY / "threads").glob("*.json")]
        for text in texts:
            self.assertEqual(shaped.findall(text), [])


class NavigationLink(unittest.TestCase):
    def test_the_menu_links_to_the_newsroom_after_the_articles(self):
        links = [href for _label, href, _description in anthus_dom.MENU_LINKS]
        self.assertEqual(links[links.index("/blog/") + 1], "/newsroom/")

    def test_every_html_page_links_to_the_newsroom_in_its_menu(self):
        projection = support.project_fixture()
        for key in sorted(projection.files):
            if key.endswith(".html") and key != "404.html":
                self.assertRegex(projection.text(key), NAV_ITEM, key)


class ExistingPagesAreUnchanged(unittest.TestCase):
    """Against a build without the opt-in, only the sitemap files and the new page's files differ, and the other
    pages differ in nothing but the stylesheet Papyrus adds for the home-page cards and the asset cache-buster that
    hashes the stylesheets."""

    @classmethod
    def setUpClass(cls):
        cls.populated = project(WEB, SNAPSHOT_DIRECTORY)
        cls.baseline = project(static_directory_without_the_opt_in(), None)

    def test_the_new_files_are_the_page_its_twin_and_the_card_stylesheet(self):
        added = set(self.populated.files) - set(self.baseline.files)
        self.assertEqual(added, {"newsroom/index.html", "newsroom/index.md", "css/papyrus-home-page.css"})
        self.assertEqual(set(self.baseline.files) - set(self.populated.files), set())

    def test_no_other_page_differs_beyond_the_stylesheet_link_and_the_asset_version(self):
        listings_of_pages = {"llms.txt", "llms-full.txt", "sitemap-0.xml"}
        for key, before in self.baseline.files.items():
            if key in listings_of_pages or not key.endswith((".html", ".md", ".json", ".xml", ".txt")):
                continue
            after = self.populated.files[key]
            if after == before:
                continue
            normalised = ASSET_VERSION.sub("", STYLESHEET_LINK.sub("", after.decode("utf-8"))).encode("utf-8")
            self.assertEqual(normalised, ASSET_VERSION.sub("", before.decode("utf-8")).encode("utf-8"), key)

    def test_the_site_listings_differ_only_by_the_newsroom_entry(self):
        without_entry = [line for line in self.populated.text("llms.txt").splitlines() if "/newsroom/" not in line]
        self.assertEqual(without_entry, self.baseline.text("llms.txt").splitlines())
        blocks = lambda text: re.findall(r"<url>.*?</url>", text, re.S)
        self.assertEqual(
            [block for block in blocks(self.populated.text("sitemap-0.xml")) if "/newsroom/" not in block],
            blocks(self.baseline.text("sitemap-0.xml")),
        )


if __name__ == "__main__":
    unittest.main()
