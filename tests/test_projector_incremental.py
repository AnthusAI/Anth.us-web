"""Incremental projection of the real Anth.us corpus equals a full projection (PPY-3d905d).

Needs PAPYRUS_ROOT (a Papyrus checkout with the projection engine), the build
requirements, and ANTHUS_PROJECTOR_EXPORT: a ``papyrus ops content export-published``
directory. Skipped otherwise. The optional ANTHUS_PROJECTOR_REFERENCE names the
``dist-papyrus`` of a full build of the same export; the full projection is then
also compared with it byte for byte.

Run: PAPYRUS_ROOT=... ANTHUS_PROJECTOR_EXPORT=... python3 tests/test_projector_incremental.py
"""
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
EXPORT = os.environ.get("ANTHUS_PROJECTOR_EXPORT")
REFERENCE = os.environ.get("ANTHUS_PROJECTOR_REFERENCE")
PAPYRUS = os.environ.get("PAPYRUS_ROOT")
SKIP = not (EXPORT and PAPYRUS)

if not SKIP:
    sys.path.insert(0, str(Path(PAPYRUS) / "src"))
    sys.path.insert(0, PAPYRUS)
    sys.path.insert(0, str(REPOSITORY / "web"))
    os.environ.setdefault("SITE_ENV", "production")
    os.environ.setdefault("AWS_BRANCH", "main")
    import projector as anthus_projector
    from papyrus_content.projection.engine import ProjectionContext, project, project_all, reconcile
    from papyrus_content.projection.item_state import read_item_state
    from papyrus_content.projection.source import PublishedContentSource
    from papyrus_content.publishing import ItemFields, project_item_to_published, save_item, unpublish_item
    from procedures.newsroom.tests.fake_client import FakeAuthoringClient
    from procedures.newsroom.tests.projection_fixtures import RecordingWriter, tree_digests

ACTOR = "projector-tests"
NOW = "2026-10-12T12:00:00Z"
CORPUS_BLOG_ITEMS = 28
SEEDS = tuple(int(seed) for seed in os.environ.get("ANTHUS_PROJECTOR_SEEDS", "1,2").split(","))
STEPS = int(os.environ.get("ANTHUS_PROJECTOR_STEPS", "14"))
EXTRA_TAGS = ("posts", "solutions", "reading", "research", "project", "featured", "engagement", "integrations", "AI")


class FakeRedirectStore:
    def __init__(self):
        self.mapping = {}

    def put_all(self, redirects):
        self.mapping.update(redirects)

    def delete_all(self, sources):
        for source in sources:
            self.mapping.pop(source, None)

    def list_all(self):
        return dict(self.mapping)

    def get(self, source):
        return self.mapping.get(source)


def split_front_matter(text):
    end = text.index("\n---\n", 3)
    return text[4:end] + "\n", text[end + 5 :]


def front_matter_with(front_matter, **changes):
    text = front_matter
    for key, value in changes.items():
        line = f"{key}: {json.dumps(value)}" if not isinstance(value, list) else f"{key}: {json.dumps(value)}"
        if re.search(rf"(?m)^{key}:", text):
            text = re.sub(rf"(?ms)^{key}:.*?(?=^\S|\Z)", line + "\n", text, count=1)
        else:
            text += line + "\n"
    return text


class Corpus:
    """A slice of the real export held as CMS records, with the edits a newsroom makes."""

    def __init__(self, export, seed):
        self.client = FakeAuthoringClient()
        self.rows = {}
        manifest = json.loads((Path(export) / "_papyrus" / "manifest.json").read_text())
        entries = manifest["items"]
        rng = random.Random(seed)
        platform = [entry for entry in entries if entry["section"] == "platform"]
        blog = [entry for entry in entries if entry["section"] != "platform"]
        chosen = rng.sample(platform, min(5, len(platform))) + rng.sample(blog, CORPUS_BLOG_ITEMS)
        self.published = set()
        self.renames = 0
        for entry in sorted(chosen, key=lambda item: item["path"]):
            front_matter, body = split_front_matter((Path(export) / entry["path"]).read_text(encoding="utf-8"))
            item_id = f"item-{entry['section']}-{entry['slug']}"
            self.rows[item_id] = {
                "section": entry["section"],
                "slug": entry["slug"],
                "front_matter": front_matter,
                "body": body,
                "path": entry["path"],
            }

    def fields(self, item_id):
        row = self.rows[item_id]
        return ItemFields(
            type="article",
            slug=row["slug"],
            section=row["section"],
            front_matter_yaml=row["front_matter"],
            body_markus=row["body"],
            aliases=[],
            id=item_id,
            source_path=row.get("path"),
        )

    def publish(self, item_id):
        save_item(self.client, self.fields(item_id), actor=ACTOR, now=NOW)
        item = self.client.get_record("Item", item_id)
        previous = self.client.get_record("PublishedItem", "published-" + item_id)
        version = (previous["versionNumber"] + 1) if previous else 1
        row, _media = project_item_to_published(item, [], published_at=NOW, version_number=version)
        self.client.upsert("PublishedItem", row)
        self.client.update_record("Item", {"id": item_id, "status": "published", "versionNumber": version})
        self.published.add(item_id)

    def unpublish(self, item_id):
        unpublish_item(self.client, item_id, actor=ACTOR, now=NOW)
        self.published.discard(item_id)


def operations(corpus, rng):
    published = sorted(corpus.published)
    drafts = sorted(set(corpus.rows) - corpus.published)
    kinds = ["retitle", "date", "tags", "state", "body", "unpublish", "rename"]
    if drafts:
        kinds += ["publish", "publish"]
    kind = rng.choice(kinds)
    if kind == "publish":
        item_id = rng.choice(drafts)
        corpus.publish(item_id)
        return kind, item_id
    item_id = rng.choice(published)
    row = corpus.rows[item_id]
    if kind == "retitle":
        row["front_matter"] = front_matter_with(row["front_matter"], title=f"Retitled {rng.randint(100, 999)}")
        corpus.publish(item_id)
    elif kind == "date":
        row["front_matter"] = front_matter_with(row["front_matter"], date=f"2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}")
        corpus.publish(item_id)
    elif kind == "tags":
        row["front_matter"] = front_matter_with(row["front_matter"], tags=rng.sample(EXTRA_TAGS, rng.randint(0, 3)))
        corpus.publish(item_id)
    elif kind == "state":
        row["front_matter"] = front_matter_with(row["front_matter"], state=rng.choice(["published", "draft"]))
        corpus.publish(item_id)
    elif kind == "body":
        row["body"] = row["body"] + f"\nAn added paragraph {rng.randint(100, 999)}.\n"
        corpus.publish(item_id)
    elif kind == "unpublish":
        corpus.unpublish(item_id)
    elif kind == "rename":
        corpus.unpublish(item_id)
        corpus.renames += 1
        row["slug"] = f"renamed-{corpus.renames}"
        row["front_matter"] = front_matter_with(row["front_matter"], slug=row["slug"])
        corpus.publish(item_id)
    return kind, item_id


def make_projector(state_path):
    state = json.loads(Path(state_path).read_text())
    config = json.loads((REPOSITORY / "web" / "projector-config.json").read_text())
    return anthus_projector.AnthusProjector(state, config)


@unittest.skipIf(SKIP, "needs PAPYRUS_ROOT and ANTHUS_PROJECTOR_EXPORT")
class IncrementalProjectionOfTheRealCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        content_root = Path(cls.work.name) / "content-root"
        sys.path.insert(0, str(REPOSITORY / "web"))
        from cms_content_root import materialize_content_root

        materialize_content_root(Path(EXPORT), content_root, REPOSITORY / "web" / "content-redirects")
        cls.state_path = Path(cls.work.name) / "site-state.json"
        subprocess.run(
            [sys.executable, str(REPOSITORY / "bin" / "make_site_state.py"), EXPORT, str(content_root), str(cls.state_path)],
            check=True,
            env={**os.environ, "PYTHONPATH": os.pathsep.join([str(Path(PAPYRUS) / "src"), os.environ.get("PYTHONPATH", "")])},
            capture_output=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def context_for(self, corpus, directory):
        store = RecordingWriter(Path(self.work.name) / directory)
        redirects = FakeRedirectStore()
        context = ProjectionContext(
            source=PublishedContentSource(corpus.client),
            projector=make_projector(self.state_path),
            writer=store,
            redirect_store=redirects,
        )
        return context, store, redirects

    def full(self, corpus, label, remembered=None):
        context, store, redirects = self.context_for(corpus, label)
        for entry in remembered.list("_papyrus/items/") if remembered else []:
            store.put(entry.key, remembered.get(entry.key))
        project_all(context)
        return tree_digests(Path(self.work.name) / label), dict(redirects.mapping)

    def test_the_full_projection_equals_the_production_pin_build(self):
        if not REFERENCE:
            self.skipTest("ANTHUS_PROJECTOR_REFERENCE is not set")
        client = FakeAuthoringClient()
        corpus = Corpus(EXPORT, 0)
        corpus.client = client
        manifest = json.loads((Path(EXPORT) / "_papyrus" / "manifest.json").read_text())
        corpus.rows = {}
        for entry in manifest["items"]:
            front_matter, body = split_front_matter((Path(EXPORT) / entry["path"]).read_text(encoding="utf-8"))
            corpus.rows[f"item-{entry['section']}-{entry['slug']}"] = {
                "section": entry["section"], "slug": entry["slug"], "front_matter": front_matter, "body": body, "path": entry["path"]
            }
        for item_id in corpus.rows:
            corpus.publish(item_id)
        pages, redirects = self.full(corpus, "parity")
        reference = tree_digests(Path(REFERENCE))
        self.assertEqual(sorted(pages), sorted(k for k in reference if k.endswith(".html") or k in ("sitemap-0.xml", "sitemap-index.xml", "robots.txt")))
        self.assertEqual({k: v for k, v in pages.items()}, {k: reference[k] for k in pages})
        rules = json.loads((Path(REFERENCE).parent / "custom-rules.json").read_text())
        exact = {r["source"]: r["target"] for r in rules if r["status"] == "301" and "<" not in r["source"] and "<" not in r["target"]}
        self.assertEqual(redirects, exact)

    def test_random_edits_match_a_full_projection_and_write_only_what_changed(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                corpus = Corpus(EXPORT, seed)
                for item_id in sorted(corpus.rows)[: len(corpus.rows) // 2]:
                    corpus.publish(item_id)
                context, store, redirects = self.context_for(corpus, f"incremental-{seed}")
                project_all(context)
                before, _ = self.full(corpus, f"before-{seed}")
                for step in range(STEPS):
                    kind, item_id = operations(corpus, rng)
                    report = project(context, item_id)
                    label = f"seed={seed} step={step} {kind} {item_id}"
                    self.assertTrue(report.ok, (label, report.errors))
                    after, after_redirects = self.full(corpus, f"after-{seed}-{step}", remembered=store)
                    incremental = tree_digests(Path(self.work.name) / f"incremental-{seed}")
                    self.assertEqual(incremental, after, label)
                    self.assertEqual(redirects.mapping, after_redirects, label)
                    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
                    touched = set(report.written) | set(report.deleted)
                    self.assertLessEqual(changed, touched, f"{label}: changed pages not written")
                    state = read_item_state(store, item_id)
                    own = (set(state.page_keys) | set(state.former_page_keys)) if state else set()
                    self.assertEqual(touched - changed - own, set(), f"{label}: pages written without change")
                    before = after
                    print(f"{label}: wrote {sorted(touched)}") if os.environ.get("ANTHUS_PROJECTOR_VERBOSE") else None
                self.assertFalse(reconcile(context, dry_run=True).drift)


if __name__ == "__main__":
    unittest.main()
