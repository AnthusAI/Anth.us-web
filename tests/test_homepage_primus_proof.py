import re

import anthus_dom
import support

MARKUS_SITE = "https://markus.anth.us/"
FLAGSHIP_NAMES = ["Cyclotron", "Chatticus", "Papyrus", "Auritus"]


def homepage():
    return support.project_fixture().page("/")


def empty_homepage():
    """The home page of a site with no articles or posts at all."""
    import tempfile
    from pathlib import Path

    empty = Path(tempfile.mkdtemp(prefix="anthus-empty-", dir=support.os.environ.get("ANTHUS_BUILD_DIR")))
    (empty / "articles").mkdir()
    return support.project_directory(empty).page("/")


def primus_proof_section_html(homepage_html):
    return re.search(r'<section class="section" id="primus-proof">.*?</section>', homepage_html, re.S).group(0)


def test_homepage_has_a_primus_credibility_section_linking_to_the_case_study():
    for html in (homepage(), empty_homepage()):
        section = primus_proof_section_html(html)
        assert 'href="/articles/call-criteria/"' in section
        assert 'href="https://primus.anth.us" rel="noopener"' in section
        assert "operated it for them for years" in section
        assert "Built and run for years" in section
        assert "free and open source" in section


def test_homepage_does_not_feature_markus_as_a_section():
    assert 'id="markus"' not in homepage()


def test_primus_proof_comes_after_solutions_and_before_articles():
    homepage_html = homepage()
    assert homepage_html.index('class="product__name"') < homepage_html.index('id="primus-proof"')
    assert homepage_html.index('id="primus-proof"') < homepage_html.index("Latest from the lab.")


def test_homepage_still_features_the_four_flagship_products_in_order():
    for html in (homepage(), empty_homepage()):
        assert re.findall(r'class="product__name">([A-Za-z]+)', html) == FLAGSHIP_NAMES
    assert [entry[0] for entry in anthus_dom.PRODUCTS] == FLAGSHIP_NAMES


def test_markus_stays_in_supporting_technology_for_the_footer():
    assert f'href="{MARKUS_SITE}"' in homepage()[homepage().index('<footer class="site-footer"'):]
    assert f'href="{MARKUS_SITE}"' in anthus_dom.FOOTER_HTML
