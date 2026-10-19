import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))

import anthus_dom
import anthus_pages

MARKUS_SITE = "https://markus.anth.us/"
FLAGSHIP_NAMES = ["Cyclotron", "Chatticus", "Papyrus", "Auritus"]


def render_homepage_without_content():
    return anthus_pages.homepage(articles=[], posts=[], images={})


def markus_section_html(homepage_html):
    return re.search(r'<section class="section" id="markus">.*?</section>', homepage_html, re.S).group(0)


def test_homepage_has_a_markus_feature_section_linking_to_the_markus_site():
    section = markus_section_html(render_homepage_without_content())
    assert f'href="{MARKUS_SITE}" rel="noopener"' in section
    assert "See Markus" in section
    assert "typed layout directives" in section
    assert "open source" in section


def test_markus_feature_comes_after_solutions_and_before_articles():
    homepage_html = render_homepage_without_content()
    assert homepage_html.index('class="product__name"') < homepage_html.index('id="markus"')
    assert homepage_html.index('id="markus"') < homepage_html.index("Latest from the lab.")


def test_homepage_still_features_the_four_flagship_products_in_order():
    homepage_html = render_homepage_without_content()
    assert re.findall(r'class="product__name">([A-Za-z]+)', homepage_html) == FLAGSHIP_NAMES
    assert [entry[0] for entry in anthus_dom.PRODUCTS] == FLAGSHIP_NAMES


def test_markus_stays_in_supporting_technology_for_the_footer():
    assert f'href="{MARKUS_SITE}"' in anthus_dom.FOOTER_HTML
