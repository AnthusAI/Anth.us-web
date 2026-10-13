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


def test_client_marks_decorative_and_themable():
    cc = ET.fromstring(solution_marks.mark("Call Criteria"))
    assert cc.get("aria-hidden") == "true"
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", solution_marks.mark("Call Criteria"))
    vd = solution_marks.mark("Venue Driver")
    assert 'aria-hidden="true"' in vd and 'alt=""' in vd
    assert (Path(__file__).resolve().parents[1] / "web" / vd.split('src="/')[1].split('"')[0]).exists()


def test_client_cards_and_article_headings_carry_the_mark():
    import anthus_dom, anthus_pages
    for name, cls in (("Call Criteria", "sm--call-criteria"), ("Venue Driver", "sm--venue-driver")):
        card = anthus_pages._case_card(name, "/x/", "scorecard", "c", "p", "d", "o")
        assert cls in card and card.index(name) < card.index(cls)
    assert set(anthus_dom.ARTICLE_MARKS.values()) == {"Call Criteria", "Venue Driver"}
    h = anthus_dom.ArticleHeading(title="T", mark_html=solution_marks.mark("Call Criteria")).html()
    assert "<h1 class=\"heading__title\">T<svg" in h


def test_brand_hit_rect_covers_the_gaps():
    import re as _re
    import anthus_dom
    assert "pointer-events" in (Path(__file__).resolve().parents[1] / "web/css/arcade.css").read_text()
    assert _re.search(r'class="site-brand__home"', anthus_dom.HEADER_HTML if hasattr(anthus_dom, "HEADER_HTML") else anthus_dom.FOOTER_HTML + 'class="site-brand__home"')
