"""Images the committed state predates are read from the rendition records in the site store (PPY-f1df00).

Needs PAPYRUS_ROOT (a Papyrus checkout). Skipped otherwise.
"""
import io
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


class FakeStore:
    def __init__(self, records):
        self.objects = {f"assets/responsive/{name}.meta.json": json.dumps(record).encode() for name, record in records.items()}
        self.reads = []

    def list_objects_v2(self, **arguments):
        return {"Contents": [{"Key": key, "ETag": f'"{len(body)}"'} for key, body in self.objects.items()], "IsTruncated": False}

    def get_object(self, Bucket, Key):
        self.reads.append(Key)
        return {"Body": io.BytesIO(self.objects[Key])}


def empty_state():
    return {"images": {"by_relpath": ["images/old.png"], "by_basename": {"old.png": "images/old.png"}, "site_by_name": {}},
            "dimensions": {}, "gatsby": {"images/old.png": {"size": [10, 10], "alpha": False}}, "passthrough": {}}


NEW_RASTER = {"kind": "gatsby", "source": "images/new.png", "size": [800, 400], "fallbackFormat": "png"}
NEW_VECTOR = {"kind": "passthrough", "source": "images/new.svg", "size": [120, 60]}


@unittest.skipIf(SKIP, "needs PAPYRUS_ROOT")
class StoredImageRecords(unittest.TestCase):
    def test_a_new_image_is_added_to_the_state(self):
        state = empty_state()
        anthus_projector.add_stored_image_records(state, [NEW_RASTER, NEW_VECTOR])
        self.assertIn("images/new.png", state["images"]["by_relpath"])
        self.assertEqual(state["images"]["by_basename"]["new.svg"], "images/new.svg")
        self.assertEqual(state["gatsby"]["images/new.png"], {"size": [800, 400], "alpha": True})
        self.assertEqual(state["passthrough"]["images/new.svg"], [120, 60])
        self.assertEqual(state["dimensions"]["/assets/content/images/new.png"], [800, 400])

    def test_an_image_the_state_knows_is_left_alone(self):
        state = empty_state()
        anthus_projector.add_stored_image_records(state, [{"kind": "gatsby", "source": "images/old.png", "size": [1, 1], "fallbackFormat": "png"}])
        self.assertEqual(state["gatsby"]["images/old.png"], {"size": [10, 10], "alpha": False})

    def test_only_records_the_state_does_not_cover_are_read_and_each_is_read_once(self):
        store = FakeStore({"images/old": {"source": "images/old.png"}, "images/new": NEW_RASTER})
        records = anthus_projector.StoredImageRecords("bucket", store)
        known = {"assets/responsive/images/old.meta.json"}
        self.assertEqual(records.unknown_records(known), [NEW_RASTER])
        self.assertEqual(records.unknown_records(known), [NEW_RASTER])
        self.assertEqual(store.reads, ["assets/responsive/images/new.meta.json"])


if __name__ == "__main__":
    unittest.main()
