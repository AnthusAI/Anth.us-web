"""Solution marks: each renders, is valid XML, and carries no hard-coded colour that would break the dark footer."""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
import solution_marks  # noqa: E402

NAMES = ("Cyclotron", "Chatticus", "Papyrus", "Primus")


@pytest.mark.parametrize("name", NAMES)
def test_mark_is_valid_decorative_svg(name):
    svg = solution_marks.mark(name)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") and root.get("aria-hidden") == "true"
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", svg), "brand colors live in arcade.css, not the markup"


@pytest.mark.parametrize("name", NAMES)
def test_labelled_mark(name):
    root = ET.fromstring(solution_marks.mark(name, label=True))
    assert root.get("role") == "img" and root.get("aria-label") == f"{name} logo"


def test_unknown_name_is_empty():
    assert solution_marks.mark("Nope") == ""


def test_footer_carries_each_mark():
    import anthus_dom
    for name in NAMES:
        assert f'sm--{name.lower()}' in anthus_dom.FOOTER_HTML
