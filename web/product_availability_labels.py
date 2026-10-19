from __future__ import annotations

from html import escape

PRODUCT_AVAILABILITY_LABEL_BY_NAME: dict[str, str] = {
    "Chatticus": "Early access",
    "Papyrus": "Early access",
    "Primus": "Early access",
    "Tactus": "Beta",
    "Babulus": "Planned",
}


def availability_label_for(product_name: str) -> str:
    return PRODUCT_AVAILABILITY_LABEL_BY_NAME.get(product_name, "")


def availability_chip_markup(product_name: str) -> str:
    label = availability_label_for(product_name)
    if not label:
        return ""
    return f'<span class="availability-chip">{escape(label)}</span>'
