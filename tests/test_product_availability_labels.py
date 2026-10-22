import re

import product_availability_labels
import support

ALLOWED_LABELS = {"Beta", "Early access", "Planned"}


def test_every_configured_label_uses_an_allowed_value():
    assert set(product_availability_labels.PRODUCT_AVAILABILITY_LABEL_BY_NAME.values()) <= ALLOWED_LABELS


def test_labelled_product_renders_a_chip():
    markup = product_availability_labels.availability_chip_markup("Chatticus")
    assert markup == '<span class="availability-chip">Early access</span>'


def test_generally_available_product_renders_nothing():
    assert product_availability_labels.availability_chip_markup("Cyclotron") == ""
    assert product_availability_labels.availability_chip_markup("Kanbus") == ""


def test_the_chips_reach_the_projected_pages_next_to_the_right_names():
    page = support.project_fixture().page("/ai-solutions/")
    chatticus = re.search(r'class="product__name">Chatticus.*?</h3>', page, re.S).group(0)
    cyclotron = re.search(r'class="product__name">Cyclotron.*?</h3>', page, re.S).group(0)
    assert '<span class="availability-chip">Early access</span>' in chatticus
    assert "availability-chip" not in cyclotron


def test_the_footer_shows_the_same_chips_as_the_grids():
    from anthus_dom import _footer_html
    footer = _footer_html()
    for name, label in product_availability_labels.PRODUCT_AVAILABILITY_LABEL_BY_NAME.items():
        if f">{name}" not in footer:
            continue  # Babulus has no footer link
        assert re.search(rf'>{name}(?:(?!</a>).)*</a><span class="availability-chip">{label}</span>', footer, re.S), name
    assert re.search(r'>Cyclotron(?:(?!</a>).)*</a>(?!<span class="availability-chip")', footer, re.S)


def test_the_engage_page_labels_the_product_links_it_lists():
    page = support.project_fixture().page("/engage/")
    assert '<a href="https://p.apyr.us">Papyrus</a>\n<span class="availability-chip">Early access</span>' in page
    assert re.search(r'<a href="https://primus.anth.us">Primus</a>\s*<span class="availability-chip">Early access</span>', page)
    assert not re.search(r'>Cyclotron</a>\s*<span class="availability-chip"', page)


def test_the_home_and_platform_pages_label_every_configured_product_they_list():
    projection = support.project_fixture()
    for path in ("/", "/ai-solutions/", "/platform/"):
        page = projection.page(path)
        for name in ("Primus", "Tactus"):
            assert re.search(rf'<a [^>]*>{name}</a><span class="availability-chip">', page), (path, name)
        assert re.search(r'class="product__name">Chatticus.*?availability-chip', page, re.S), path


def test_every_place_the_chip_is_rendered_uses_the_one_helper():
    import pathlib
    web = pathlib.Path(support.WEB)
    markup = '<span class="availability-chip"'
    offenders = [p.name for p in web.glob("*.py") if markup in p.read_text() and p.name != "product_availability_labels.py"]
    assert offenders == []
