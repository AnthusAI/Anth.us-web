import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
import product_availability_labels  # noqa: E402

ALLOWED_LABELS = {"Beta", "Early access", "Planned"}


def test_every_configured_label_uses_an_allowed_value():
    assert set(product_availability_labels.PRODUCT_AVAILABILITY_LABEL_BY_NAME.values()) <= ALLOWED_LABELS


def test_labelled_product_renders_a_chip():
    markup = product_availability_labels.availability_chip_markup("Chatticus")
    assert markup == '<span class="availability-chip">Early access</span>'


def test_generally_available_product_renders_nothing():
    assert product_availability_labels.availability_chip_markup("Cyclotron") == ""
    assert product_availability_labels.availability_chip_markup("Kanbus") == ""
