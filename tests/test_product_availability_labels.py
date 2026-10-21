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
