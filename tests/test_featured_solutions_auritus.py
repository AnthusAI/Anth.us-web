"""The featured solutions are Cyclotron, Chatticus, Papyrus and Auritus, in that order, everywhere they are listed."""
import re

import anthus_dom
import site_blocks
import support

FEATURED_SOLUTION_NAMES = ["Cyclotron", "Chatticus", "Papyrus", "Auritus"]


def footer(html):
    return re.search(r'<footer class="site-footer".*?</footer>', html, re.S).group(0)  # the page footer is the first such element


def names_in_footer_solutions_column(html):
    column = re.search(r"Solutions.*?</ul>", footer(html), re.S).group(0)
    return re.findall(r'class="site-footer__pname"[^>]*>([A-Za-z]+)', column)


def products_grid(html):
    """The product grid of a page, to the end of its section (the pictograms inside hold lists of their own)."""
    start = html.index('<ul class="grid grid--products">')
    return html[start : html.index("</section>", start)]


def supporting_row(html):
    return re.search(r'<p class="supporting">.*?</p>', html, re.S).group(0)


def test_products_are_exactly_the_four_featured_solutions_in_order():
    assert [entry[0] for entry in anthus_dom.PRODUCTS] == FEATURED_SOLUTION_NAMES


def test_footer_solutions_column_lists_the_featured_solutions_on_every_kind_of_page():
    projection = support.project_fixture()
    for path in ("/", "/ai-solutions/", "/about/", "/articles/", "/articles/call-criteria/", "/platform/biblicus/"):
        assert names_in_footer_solutions_column(projection.page(path)) == FEATURED_SOLUTION_NAMES, path
    assert names_in_footer_solutions_column(projection.text("404.html")) == FEATURED_SOLUTION_NAMES


def test_ai_solutions_grid_lists_the_featured_solutions():
    page = support.project_fixture().page("/ai-solutions/")
    grid = products_grid(page)
    assert re.findall(r'class="product__name">([A-Za-z]+)', grid) == FEATURED_SOLUTION_NAMES
    assert "Work with us on Auritus" in grid
    assert "Work with us on Primus" not in grid


def test_the_auritus_card_carries_the_auritus_logo_mark():
    page = support.project_fixture().page("/ai-solutions/")
    auritus = next(card for card in products_grid(page).split('<li class="card notch product') if 'class="product__name">Auritus' in card)
    assert 'sm--auritus' in auritus


def test_the_home_page_features_the_same_four_in_order():
    home = support.project_fixture().page("/")
    assert re.findall(r'class="product__name">([A-Za-z]+)', home) == FEATURED_SOLUTION_NAMES


def test_primus_is_supporting_technology_not_featured():
    supporting_names = [entry[0] for entry in anthus_dom.SUPPORTING]
    assert "Primus" in supporting_names
    assert "Auritus" not in supporting_names
    row = supporting_row(support.project_fixture().page("/"))
    assert ">Primus</a>" in row
    assert ">Auritus</a>" not in row


def test_every_featured_solution_has_a_description_and_the_ai_solutions_page_shows_it():
    page = support.project_fixture().page("/ai-solutions/")
    for name in FEATURED_SOLUTION_NAMES:
        assert name in site_blocks._SOLUTION_DESCRIPTIONS
        assert site_blocks._SOLUTION_DESCRIPTIONS[name].split(",")[0].split(".")[0][:40] in page.replace("&#x27;", "'").replace("’", "’")
