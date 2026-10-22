"""Solution marks: each renders, is valid XML, and carries no hard-coded colour that would break the dark footer."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import anthus_dom  # noqa: E402
import solution_marks  # noqa: E402
import support  # noqa: E402

WEB = Path(__file__).resolve().parents[1] / "web"
THEME = (WEB / "css" / "site-theme.css").read_text(encoding="utf-8")

NAMES = ("Cyclotron", "Chatticus", "Papyrus", "Primus")
FOOTER_NAMES = ("Cyclotron", "Chatticus", "Papyrus")


@pytest.mark.parametrize("name", NAMES)
def test_mark_is_valid_decorative_svg(name):
    svg = solution_marks.mark(name)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") and root.get("aria-hidden") == "true"
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", svg), "brand colors live in site-theme.css, not the markup"


@pytest.mark.parametrize("name", NAMES)
def test_labelled_mark(name):
    root = ET.fromstring(solution_marks.mark(name, label=True))
    assert root.get("role") == "img" and root.get("aria-label") == f"{name} logo"


def test_unknown_name_is_empty():
    assert solution_marks.mark("Nope") == ""


def test_auritus_mark_is_the_decorative_announcer_image():
    mark = solution_marks.mark("Auritus")
    assert 'sm--auritus' in mark and 'aria-hidden="true"' in mark and 'alt=""' in mark
    assert (Path(__file__).resolve().parents[1] / "web" / mark.split('src="/')[1].split('"')[0]).exists()
    assert 'alt="Auritus logo"' in solution_marks.mark("Auritus", label=True)


def footer(html):
    begin = html.index('<footer class="site-footer"')
    return html[begin : html.index("</footer>", begin)]


def test_footer_carries_the_auritus_mark():
    assert "sm--auritus" in anthus_dom.FOOTER_HTML
    assert "sm--auritus" in footer(support.project_fixture().page("/"))


def test_footer_carries_each_mark():
    for page in ("/", "/ai-solutions/", "/articles/call-criteria/"):
        html = footer(support.project_fixture().page(page))
        for name in FOOTER_NAMES:
            assert f"sm--{name.lower()}" in html, (page, name)
    for name in FOOTER_NAMES:
        assert f"sm--{name.lower()}" in anthus_dom.FOOTER_HTML


def test_client_marks_decorative_and_themable():
    cc = ET.fromstring(solution_marks.mark("Call Criteria"))
    assert cc.get("aria-hidden") == "true"
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", solution_marks.mark("Call Criteria"))
    vd = solution_marks.mark("Venue Driver")
    assert 'aria-hidden="true"' in vd and 'alt=""' in vd
    assert (WEB / vd.split('src="/')[1].split('"')[0]).exists()
    assert ".sm--call-criteria" in THEME  # its colours live in the theme and turn light on the dark page


def test_client_cards_and_article_headings_carry_the_mark():
    home = support.project_fixture().page("/")
    for name, cls in (("Call Criteria", "sm--call-criteria"), ("Venue Driver", "sm--venue-driver")):
        card = next(
            case for case in home.split('<li class="card notch case') if f'class="case__name"><a href=' in case and f">{name}</a>" in case
        )
        assert cls in card and card.index(name) < card.index(cls)  # the mark follows the name
    assert set(anthus_dom.ARTICLE_MARKS.values()) == {"Call Criteria", "Venue Driver"}
    heading = anthus_dom.ArticleHeading(title="T", mark_html=solution_marks.mark("Call Criteria")).html()
    assert '<h1 class="heading__title">T<svg' in heading
    for slug, cls in (("call-criteria", "sm--call-criteria"), ("venue-driver", "sm--venue-driver")):
        page = support.project_fixture().page(f"/articles/{slug}/")
        assert re.search(r'<h1 class="heading__title">[^<]+<(?:svg|img)[^>]*' + cls, page), slug
    plain = support.project_fixture().page("/articles/plain-article/")
    assert re.search(r"<h1(?: class=\"heading__title\")?>Plain Article</h1>", plain), "an article of no client carries no mark"


def test_brand_hit_rect_covers_the_gaps():
    assert "pointer-events" in THEME
    header = support.project_fixture().page("/")
    assert 'class="site-brand__home"' in header
    assert 'class="site-brand__hit"' in header
