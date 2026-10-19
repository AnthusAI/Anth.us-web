"""The GA4 conversion events are wired site-wide and every engage call to action is a plain link the listener can see."""
import re
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / 'web'))
import anthus_dom
import anthus_pages

LISTENER_NAME = 'conversion-events.js'
ENGAGE_LINK = re.compile(r'<a\b[^>]*href="/engage/(?:\?[^"]*)?"')


class ConversionEventWiringTests(unittest.TestCase):
    def test_the_listener_is_loaded_site_wide_the_way_the_other_chrome_scripts_are(self):
        self.assertIn(f'"assets/{LISTENER_NAME}"', (REPOSITORY / 'web' / 'build_via_papyrus.py').read_text(encoding='utf-8'))
        self.assertIn(f'"{LISTENER_NAME}"', (REPOSITORY / 'web' / 'build_via_papyrus.py').read_text(encoding='utf-8'))
        self.assertIn(f'"{LISTENER_NAME}"', (REPOSITORY / 'web' / 'projector.py').read_text(encoding='utf-8'))
        self.assertTrue((REPOSITORY / 'web' / 'assets' / LISTENER_NAME).is_file())

    def test_the_header_footer_hero_band_and_article_calls_to_action_are_engage_links(self):
        self.assertRegex(anthus_dom._header_html('/'), ENGAGE_LINK)
        self.assertRegex(anthus_dom._footer_html(), ENGAGE_LINK)
        self.assertRegex(anthus_dom.ENGAGE_CTA_HTML, ENGAGE_LINK)
        self.assertRegex(anthus_pages._cta(), ENGAGE_LINK)
        self.assertRegex(anthus_pages._btn('Tell us the problem', '/engage/'), ENGAGE_LINK)

    def test_the_solution_card_link_names_the_solution_for_attribution(self):
        card = anthus_pages._product_card('Primus', 'https://primus.example.test', 'line', 'hero-loop', None, describe=True)
        self.assertIn('href="/engage/?solution=Primus"', card)

    def test_the_site_scripts_carry_no_inline_analytics_handlers(self):
        header = anthus_dom._header_html('/')
        self.assertNotIn('gtag(', header)
        self.assertNotIn('onclick', header)


if __name__ == '__main__':
    unittest.main()
