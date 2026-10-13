"""{{pictogram <name>}} in an article body embeds the animated pictogram (anthus_mdx)."""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPYRUS = os.environ.get("PAPYRUS_ROOT", str(ROOT.parent / "Papyrus"))
sys.path[:0] = [str(ROOT / "web"), str(Path(PAPYRUS) / "src")]

try:
    from anthus_mdx import normalize_body
except ImportError:  # pragma: no cover - needs a Papyrus checkout
    normalize_body = None


def _norm(body):
    return normalize_body(body, resolve_image_name=lambda n: None, resolve_image_path=lambda p: None)[0]


@unittest.skipIf(normalize_body is None, "needs PAPYRUS_ROOT")
class BodyPictogramTest(unittest.TestCase):
    def test_token_becomes_a_sentinel_not_text(self):
        out = _norm("Intro.\n\n{{pictogram relocate}}\n\nAfter.\n")
        self.assertNotIn("{{pictogram", out)
        self.assertIn("Intro.", out)
        self.assertIn("After.", out)

    def test_unknown_name_fails(self):
        with self.assertRaises(KeyError):
            _norm("{{pictogram no-such-thing}}\n")

    def test_token_inside_code_is_left_alone(self):
        out = _norm("```\n{{pictogram relocate}}\n```\n")
        self.assertIn("{{pictogram relocate}}", out)


if __name__ == "__main__":
    unittest.main()
