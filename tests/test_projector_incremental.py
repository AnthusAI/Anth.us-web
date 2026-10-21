"""Incremental projection after publishes, edits and unpublishes equals a full projection (PPY-3d905d).

A working copy of a corpus (a directory of ``.md`` files) is edited the way a newsroom edits: retitle, redate, retag,
flip ``state``, change a body, unpublish (delete the file), rename, publish a held-back item. After each edit the one
changed item is projected incrementally into a long-lived site directory (``engine.project``), and the result must
equal a fresh ``project_all`` of the same corpus (pages, redirects), write only the pages that changed, and leave no
drift for ``reconcile``.

By default the corpus is the synthetic fixture (tests/fixtures/content). Set ``ANTHUS_PROJECTOR_EXPORT`` to a directory
of published ``.md`` files (a ``papyrus ops content export-published`` directory) to run on a slice of it instead; its
images are measured from the files of the export. ``ANTHUS_PROJECTOR_SEEDS`` (default ``1,2``) and
``ANTHUS_PROJECTOR_STEPS`` (default ``14``) size the run; ``ANTHUS_PROJECTOR_VERBOSE=1`` prints each step.
"""
import json
import os
import random
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import pytest

import support
from papyrus_content.projection.directory_source import DirectoryContentSource
from papyrus_content.projection.engine import project, project_all, reconcile
from papyrus_content.projection.item_state import read_item_state
from procedures.newsroom.tests.projection_fixtures import RecordingWriter, tree_digests

EXPORT = os.environ.get("ANTHUS_PROJECTOR_EXPORT")
SEEDS = tuple(int(seed) for seed in os.environ.get("ANTHUS_PROJECTOR_SEEDS", "1,2").split(","))
STEPS = int(os.environ.get("ANTHUS_PROJECTOR_STEPS", "14"))
VERBOSE = os.environ.get("ANTHUS_PROJECTOR_VERBOSE")
EXPORT_PLATFORM_ITEMS = 5
EXPORT_ARTICLES = 28
EXTRA_TAGS = ("posts", "solutions", "reading", "research", "project", "featured", "engagement", "integrations", "AI")


def split_front_matter(text):
    end = text.index("\n---\n", 3)
    return text[4:end] + "\n", text[end + 5 :]


def front_matter_with(front_matter, **changes):
    text = front_matter
    for key, value in changes.items():
        line = f"{key}: {json.dumps(value)}"
        if re.search(rf"(?m)^{key}:", text):
            text = re.sub(rf"(?ms)^{key}:.*?(?=^\S|\Z)", line + "\n", text, count=1)
        else:
            text += line + "\n"
    return text


class Corpus:
    """A working directory of ``.md`` files; the files present are the published items, the pool holds the rest."""

    def __init__(self, source: Path, work: Path, seed: int) -> None:
        self.content = work / f"content-{seed}"
        self.content.mkdir(parents=True)
        files = sorted(path.relative_to(source).as_posix() for path in Path(source).rglob("*.md") if not any(part.startswith((".", "_")) for part in path.relative_to(source).parts))
        rng = random.Random(seed)
        if EXPORT:
            platform = [name for name in files if name.startswith("platform/")]
            blog = [name for name in files if not name.startswith("platform/")]
            files = sorted(rng.sample(platform, min(EXPORT_PLATFORM_ITEMS, len(platform))) + rng.sample(blog, min(EXPORT_ARTICLES, len(blog))))
        self.texts = {name: (Path(source) / name).read_text(encoding="utf-8") for name in files}
        self.live = set(files[: len(files) // 2])
        for name in self.live:
            self.write(name)
        self.renames = 0

    def write(self, name: str) -> None:
        path = self.content / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.texts[name], encoding="utf-8")
        self.live.add(name)

    def remove(self, name: str) -> None:
        (self.content / name).unlink()
        self.live.discard(name)

    @property
    def pool(self) -> list[str]:
        return sorted(set(self.texts) - self.live)

    @staticmethod
    def item_id(name: str) -> str:
        return f"file:{name}"

    def edit(self, name: str, *, front: dict | None = None, body_suffix: str = "") -> None:
        head, body = split_front_matter(self.texts[name])
        if front:
            head = front_matter_with(head, **front)
        self.texts[name] = f"---\n{head}---\n{body}{body_suffix}"
        self.write(name)


def slugs_linked_from_authored_pages() -> set[str]:
    """Slugs the authored pages link to (``/blog/x/``, ``/articles/x/``, ``/platform/x/``), and the slugs of items
    that have no page of their own (folded into another, or with their own site)."""
    from solution_sites import EXTERNAL_SITES, FOLDED_INTO

    linked = {slug.lower() for slug in (*FOLDED_INTO, *EXTERNAL_SITES)}
    for path in (support.WEB / "pages").glob("*.md"):
        linked |= {slug.lower() for slug in re.findall(r"/(?:blog|articles|platform)/([A-Za-z0-9_-]+)/?[\"#]", path.read_text(encoding="utf-8"))}
    return linked


LIFECYCLE = ("publish", "unpublish", "rename")


def apply_operation(corpus: Corpus, rng: random.Random, pinned: set[str] = frozenset()):
    """One edit of the corpus, as a generator of ``(kind, item id)``: each yield is a state to project and compare.

    An item that an authored page links to, or that has no page, is edited but never published, unpublished or
    renamed: the pages that link to it are not re-rendered when it comes or goes (``ProjectionOfLinkedItems`` below).
    A rename is two states (the old name unpublished, the new name published), as it is for the projector.
    """
    def movable(names):
        return [name for name in names if Path(name).stem.lower() not in pinned]

    live, pool = sorted(corpus.live), corpus.pool
    kinds = ["retitle", "date", "tags", "state", "body"]
    if movable(live):
        kinds += ["unpublish", "rename"]
    if movable(pool):
        kinds += ["publish", "publish"]
    kind = rng.choice(kinds)
    if kind == "publish":
        name = rng.choice(movable(pool))
        corpus.write(name)
        yield kind, corpus.item_id(name)
        return
    name = rng.choice(movable(live) if kind in LIFECYCLE else live)
    if kind == "retitle":
        corpus.edit(name, front={"title": f"Retitled {rng.randint(100, 999)}"})
    elif kind == "date":
        corpus.edit(name, front={"date": f"2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}"})
    elif kind == "tags":
        corpus.edit(name, front={"tags": rng.sample(EXTRA_TAGS, rng.randint(0, 3))})
    elif kind == "state":
        corpus.edit(name, front={"state": rng.choice(["published", "draft"])})
    elif kind == "body":
        corpus.edit(name, body_suffix=f"\nAn added paragraph {rng.randint(100, 999)}.\n")
    elif kind == "unpublish":
        corpus.remove(name)
    elif kind == "rename":
        corpus.renames += 1
        renamed = f"{name.split('/')[0]}/renamed-{corpus.renames}.md"
        head, body = split_front_matter(corpus.texts.pop(name))
        corpus.texts[renamed] = f"---\n{front_matter_with(head, slug=f'renamed-{corpus.renames}')}---\n{body}"
        corpus.remove(name)
        yield "rename (old name)", corpus.item_id(name)
        corpus.write(renamed)
        yield "rename (new name)", corpus.item_id(renamed)
        return
    yield kind, corpus.item_id(name)


class IncrementalProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Path(tempfile.mkdtemp(prefix="anthus-incremental-", dir=os.environ.get("ANTHUS_BUILD_DIR")))
        cls.source = Path(EXPORT) if EXPORT else support.FIXTURE_CONTENT
        cls.store = support.store_for_directory(cls.source) if EXPORT else support.FakeRenditionStore()
        cls.pinned = slugs_linked_from_authored_pages()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def point(self, context, corpus):
        """A fresh process for the next event: a new source and a new projector over the same site store."""
        context.source = DirectoryContentSource(corpus.content)
        context.projector = support.make_projector(self.store)

    def full(self, corpus, label, remembered=None):
        directory = self.work / label
        writer = RecordingWriter(directory)
        context = support.make_context(corpus.content, directory, store=self.store, writer=writer, keep_state=True)
        for entry in remembered.list("_papyrus/items/") if remembered else []:
            writer.put(entry.key, remembered.get(entry.key))
        report = project_all(context)
        self.assertTrue(report.ok, report.errors)
        digests, redirects = tree_digests(directory), dict(context.redirect_store.mapping)
        shutil.rmtree(directory, ignore_errors=True)  # a site is 20 MB of assets; keep one at a time
        return digests, redirects

    def test_random_edits_match_a_full_projection_and_write_only_what_changed(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                corpus = Corpus(self.source, self.work, seed)
                writer = RecordingWriter(self.work / f"incremental-{seed}")
                context = support.make_context(corpus.content, self.work / f"incremental-{seed}", store=self.store, writer=writer, keep_state=True)
                self.point(context, corpus)
                self.assertTrue(project_all(context).ok)
                before, _ = self.full(corpus, f"before-{seed}")
                for step in range(STEPS):
                    for kind, item_id in apply_operation(corpus, rng, self.pinned):
                        label = f"seed={seed} step={step} {kind} {item_id}"
                        self.point(context, corpus)
                        report = project(context, item_id)
                        self.assertTrue(report.ok, (label, report.errors))
                        touched = set(report.written) | set(report.deleted)
                        after, after_redirects = self.full(corpus, f"after-{seed}-{step}", remembered=writer)
                        incremental = tree_digests(self.work / f"incremental-{seed}")
                        self.assertEqual(sorted(incremental), sorted(after), label)
                        # llms-full.txt is keyed on item version numbers, which the CMS bumps on every save but this fixture's
                        # direct edits do not, so it is the one file the fixture cannot compare.
                        self.assertEqual({key for key in after if incremental[key] != after[key]} - {"llms-full.txt"}, set(), label)
                        self.assertEqual(context.redirect_store.mapping, after_redirects, label)
                        changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
                        self.assertLessEqual(changed - {"llms-full.txt"}, touched, f"{label}: changed pages not written")
                        state = read_item_state(writer, item_id)
                        own = (set(state.page_keys) | set(state.former_page_keys)) if state else set()
                        item_pages = {key for key in after if re.fullmatch(r"(?:articles|platform)/[^/]+/index\.html", key)}
                        # Listing, tag, authored and data pages are written again when a field of an entry they list changes,
                        # printed or not (their inputs are the entries' fields); an item page only for its own item, or
                        # for every item on a publish, unpublish or rename (the URL map they rewrite links with).
                        allowed = own | (item_pages if kind.split(" ")[0] in LIFECYCLE else set())
                        self.assertEqual((touched & item_pages) - changed - allowed, set(), f"{label}: item pages written without change")
                        before = after
                        if VERBOSE:
                            print(f"{label}: wrote {sorted(touched)}")
                self.point(context, corpus)
                self.assertFalse(reconcile(context, dry_run=True).drift)
                shutil.rmtree(self.work / f"incremental-{seed}", ignore_errors=True)


class ProjectionOfLinkedItems(unittest.TestCase):
    """Incremental projection of the items other pages link to: publishing one refreshes the pages that link to it; a known gap remains for
    an item that has no page of its own (strict xfail).

    Each starts from a full projection, changes the corpus by one item, projects that item incrementally, and compares
    every file with a fresh full projection. The randomized test above avoids these two operations.
    """

    def differences(self, content: Path, change, item_id: str) -> set[str]:
        work = Path(tempfile.mkdtemp(prefix="anthus-linked-", dir=os.environ.get("ANTHUS_BUILD_DIR")))
        store = support.FakeRenditionStore()
        writer = RecordingWriter(work / "incremental")
        context = support.make_context(content, work / "incremental", store=store, writer=writer, keep_state=True)
        project_all(context)
        change(content)
        context.source = DirectoryContentSource(content)
        context.projector = support.make_projector(store)
        self.assertTrue(project(context, item_id).ok)
        fresh = support.make_context(content, work / "full", store=store, writer=RecordingWriter(work / "full"), keep_state=True)
        for entry in writer.list("_papyrus/items/"):
            fresh.writer.put(entry.key, writer.get(entry.key))
        project_all(fresh)
        incremental, full = tree_digests(work / "incremental"), tree_digests(work / "full")
        shutil.rmtree(work, ignore_errors=True)
        return {key for key in set(incremental) | set(full) if incremental.get(key) != full.get(key)}

    def test_publishing_an_item_an_authored_page_links_to_refreshes_that_page(self):
        content = support.corpus_with({}, without=("articles/venue-driver.md",))
        restore = support.FIXTURE_CONTENT / "articles" / "venue-driver.md"
        different = self.differences(content, lambda path: (path / "articles" / "venue-driver.md").write_text(restore.read_text(encoding="utf-8"), encoding="utf-8"), "file:articles/venue-driver.md")
        self.assertEqual(different, set())

    @pytest.mark.xfail(strict=True, reason=(
        "web/hooks.py + the projection engine: an item that has no page (folded into another, or with its own site) still "
        "changes the URL map every page is rewritten with, but unpublishing it projects nothing (the engine returns early for "
        "an item without projected pages), so the articles that link to it keep the rewritten href: after deleting "
        "articles/Paytronix.md, articles/call-criteria/ still links /articles/venue-driver/ where a full projection leaves "
        "/solutions/Paytronix/"
    ))
    def test_unpublishing_a_folded_item_refreshes_the_pages_that_link_to_it(self):
        content = support.corpus_with({})
        different = self.differences(content, lambda path: (path / "articles" / "Paytronix.md").unlink(), "file:articles/Paytronix.md")
        self.assertEqual(different, set())


if __name__ == "__main__":
    unittest.main()
