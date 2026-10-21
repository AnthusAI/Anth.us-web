import re

import anthus_dom
import support

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
    page = support.project_fixture().page("/about/")
    assert f'href="{MARKUS_SITE}"' in page[page.index('<footer class="site-footer"'):]


def test_markus_gets_no_page_on_anth_us():
    assert "Markus" not in anthus_dom.SUPPORTING_PAGES
    projection = support.project_fixture()
    assert not [key for key in projection.files if "markus" in key.lower() and key.endswith(".html")]
    assert "/platform/markus/" not in str(projection.text("sitemap-0.xml"))


def test_supporting_row_and_cards_link_to_the_markus_site():
    projection = support.project_fixture()
    row = re.search(r'<p class="supporting">.*?</p>', projection.page("/"), re.S).group(0)
    assert f'href="{MARKUS_SITE}"' in row
    assert f'href="{MARKUS_SITE}"' in projection.page("/platform/")
