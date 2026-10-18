import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))

import anthus_dom
import anthus_pages

FEATURED_SOLUTION_NAMES = ["Cyclotron", "Chatticus", "Papyrus", "Auritus"]


def names_in_footer_solutions_column():
    column = re.search(r'Solutions.*?</ul>', anthus_dom.FOOTER_HTML, re.S).group(0)
    return re.findall(r'class="site-footer__pname"[^>]*>([A-Za-z]+)', column)


def test_products_are_exactly_the_four_featured_solutions_in_order():
    assert [entry[0] for entry in anthus_dom.PRODUCTS] == FEATURED_SOLUTION_NAMES


def test_footer_solutions_column_lists_the_featured_solutions():
    assert names_in_footer_solutions_column() == FEATURED_SOLUTION_NAMES


def test_ai_solutions_grid_lists_the_featured_solutions():
    grid = anthus_pages._products_grid(describe=True)
    assert re.findall(r'class="product__name">([A-Za-z]+)', grid) == FEATURED_SOLUTION_NAMES
    assert "Work with us on Auritus" in grid
    assert "Work with us on Primus" not in grid


def test_primus_is_supporting_technology_not_featured():
    supporting_names = [entry[0] for entry in anthus_dom.SUPPORTING]
    assert "Primus" in supporting_names
    assert "Auritus" not in supporting_names
    assert ">Primus</a>" in anthus_pages._supporting_row()
    assert ">Auritus</a>" not in anthus_pages._supporting_row()


def test_every_featured_solution_has_a_description():
    for name in FEATURED_SOLUTION_NAMES:
        assert name in anthus_pages._SOLUTION_DESCRIPTIONS
