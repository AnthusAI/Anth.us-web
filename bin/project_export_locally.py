#!/usr/bin/env python3
"""Project a Papyrus ``export-published`` directory into a local directory, in process.

Usage: project_export_locally.py EXPORT_DIR OUT_DIR [--redirects-json PATH]

Needs PAPYRUS_ROOT (a Papyrus checkout with the projection engine) on PYTHONPATH as
``$PAPYRUS_ROOT/src`` and ``$PAPYRUS_ROOT``, the ``web/site-state.json`` and
``web/projector-config.json`` the deploy writes, and the build requirements.
Writes exactly what ``papyrus ops content project --all --out OUT_DIR`` writes, plus the
redirect map the site's key-value store would hold.
"""

import argparse
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "web"))

from papyrus_content.projection.engine import ProjectionContext, project_all  # noqa: E402
from papyrus_content.projection.source import PublishedContentSource  # noqa: E402
from papyrus_content.projection.writers import LocalDirectoryWriter  # noqa: E402
from papyrus_content.publishing import ItemFields, project_item_to_published, save_item  # noqa: E402
from procedures.newsroom.tests.fake_client import FakeAuthoringClient  # noqa: E402

import projector as anthus_projector  # noqa: E402

ACTOR = "project-export-locally"
NOW = "2026-10-12T12:00:00Z"


class MemoryRedirectStore:
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


def publish_export(client, export_directory):
    manifest = json.loads((export_directory / "_papyrus" / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["items"]:
        front_matter, body = split_front_matter((export_directory / entry["path"]).read_text(encoding="utf-8"))
        fields = ItemFields(
            type="article",
            slug=entry["slug"],
            section=entry["section"],
            front_matter_yaml=front_matter,
            body_markus=body,
            aliases=[],
            id=f"item-{entry['section']}-{entry['slug']}",
            source_path=entry["path"],
        )
        save_item(client, fields, actor=ACTOR, now=NOW)
        item = client.get_record("Item", fields.id)
        row, _media = project_item_to_published(item, [], published_at=NOW, version_number=1)
        client.upsert("PublishedItem", row)
        client.update_record("Item", {"id": fields.id, "status": "published", "versionNumber": 1})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("export_directory", type=Path)
    parser.add_argument("out_directory", type=Path)
    parser.add_argument("--redirects-json", type=Path)
    arguments = parser.parse_args()
    client = FakeAuthoringClient()
    publish_export(client, arguments.export_directory)
    redirects = MemoryRedirectStore()
    context = ProjectionContext(
        source=PublishedContentSource(client),
        projector=anthus_projector.create_projector(),
        writer=LocalDirectoryWriter(arguments.out_directory),
        redirect_store=redirects,
        keep_state=False,
    )
    report = project_all(context)
    print(f"written {len(report.written)} redirects {report.redirects_written} errors {report.errors}")
    if arguments.redirects_json:
        arguments.redirects_json.write_text(json.dumps(redirects.mapping, indent=1, sort_keys=True), encoding="utf-8")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
