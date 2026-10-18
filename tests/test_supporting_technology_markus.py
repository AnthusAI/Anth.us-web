import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))

import anthus_dom
import anthus_pages

MARKUS_SITE = "https://markus.anth.us/"


def markus_entries():
    return [entry for entry in anthus_dom.SUPPORTING if entry[0] == "Markus"]


def test_markus_is_listed_once_as_external_supporting_technology():
    entries = markus_entries()
    assert len(entries) == 1
    name, href, line, external = entries[0]
    assert href == MARKUS_SITE
    assert external is True
    assert "layout intent" in line


def test_footer_links_to_the_markus_site():
    assert f'href="{MARKUS_SITE}"' in anthus_dom.FOOTER_HTML


def test_markus_gets_no_page_on_anth_us():
    assert "Markus" not in anthus_dom.SUPPORTING_PAGES


def test_supporting_row_links_to_the_markus_site():
    assert f'href="{MARKUS_SITE}"' in anthus_pages._supporting_row()
