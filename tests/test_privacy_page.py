"""The /privacy/ page: rendered by anthus_pages, linked from the footer, registered in the build and projector.

The policy is grounded in what the site does (GA4, the Prospectus contact form, AWS hosting, Google Fonts).
Details the repository cannot supply stay as visible bracketed placeholders rather than invented values.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
import anthus_dom
import anthus_pages
import anthus_urls
import inquiry_form

try:
    import build_via_papyrus as build
    BUILD_ERROR = None
except (ImportError, SystemExit) as error:
    build = None
    BUILD_ERROR = error

PLACEHOLDERS = (
    '[PRIVACY CONTACT EMAIL — Ryan to supply]',
    '[LEGAL ENTITY NAME — Ryan to supply]',
    '[POSTAL ADDRESS — Ryan to supply]',
)
PAGE = anthus_pages.privacy_page()
TEXT = re.sub(r'<[^>]+>', ' ', PAGE)


class PrivacyPageTests(unittest.TestCase):
    def test_page_has_one_h1_and_the_expected_sections(self):
        self.assertEqual(PAGE.count('<h1>'), 1)
        self.assertIn('Privacy policy', PAGE)
        for heading in ('Who we are', 'What we collect', 'Cookies and similar technologies', 'How long we keep it',
                        'Sharing and service providers', 'International transfers', 'Your rights', 'Children',
                        'Changes to this policy'):
            self.assertIn(heading, PAGE)

    def test_effective_date_is_shown(self):
        self.assertIn('2026-10-19', TEXT)

    def test_unknown_details_are_bracketed_placeholders_not_invented_values(self):
        for placeholder in PLACEHOLDERS:
            self.assertIn(placeholder, TEXT)
        self.assertNotIn('mailto:', PAGE)
        self.assertIsNone(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', TEXT))

    def test_no_draft_wording_on_the_rendered_page(self):
        for word in ('draft', 'todo', 'tbd', 'lorem', 'placeholder'):
            self.assertNotIn(word, TEXT.lower())

    def test_no_google_form_references(self):
        for needle in ('docs.google.com', 'forms.gle', '1FAIpQLS', 'Google Form'):
            self.assertNotIn(needle, PAGE)

    def test_covers_what_the_site_actually_does(self):
        shipped = inquiry_form.read_config()
        # The policy restates the approved contact-v1 notice; fail if the notice changes and the policy does not.
        self.assertEqual(shipped['notice_version'], 'contact-v1')
        for phrase in ('never sold', 'mailing list', 'until you ask us to delete them'):
            self.assertIn(phrase, shipped['privacy_notice'])
        for needle in ('Google Analytics 4', 'Google Fonts', 'Amazon Web Services', 'contact form', 'utm_campaign',
                       'about six months', 'Cookie settings', 'supervisory authority', 'withdraw your consent',
                       'We never sell them', 'kept until you ask us to delete them'):
            self.assertIn(needle, TEXT)

    def test_advertising_is_described_as_possible_future_use_only_with_consent(self):
        self.assertIn('We do not currently run advertising', TEXT)
        self.assertIn('only after you accept advertising cookies', TEXT)

    def test_metadata_is_registered(self):
        self.assertEqual(anthus_pages.PAGE_META['/privacy/']['title'], 'Privacy Policy | Anthus')
        self.assertTrue(anthus_pages.PAGE_META['/privacy/']['description'])

    def test_url_and_projection_ownership(self):
        self.assertIn('privacy', anthus_urls.STANDALONE_PAGES)
        self.assertIn('privacy', anthus_urls.RESERVED_SEGMENTS)
        projector_source = (Path(__file__).resolve().parents[1] / 'web' / 'projector.py').read_text()
        self.assertIn('"privacy"', projector_source)


class FooterLinkTests(unittest.TestCase):
    def test_footer_links_to_privacy_on_every_page(self):
        self.assertIn('<li><a href="/privacy/">Privacy</a></li>', anthus_dom.FOOTER_HTML)
        envelope = anthus_dom.render_envelope(fragment='<p>x</p>', route='/privacy/', scripts='')
        self.assertIn('href="/privacy/"', envelope)


@unittest.skipIf(build is None, f'build module unavailable: {BUILD_ERROR}')
class BuildRegistrationTests(unittest.TestCase):
    def test_build_generates_privacy_html_with_meta(self):
        from anthus_content import Collections
        build.GENERATED.clear()
        build._PAGE_META.clear()
        build._ARTICLE_LD.clear()
        build.generate_pages(Collections.from_nodes([]), object())
        title, fragment = build.GENERATED['privacy.html']
        self.assertEqual(title, 'Privacy Policy')
        self.assertIn('Privacy policy', fragment)
        self.assertIn('privacy.html', build._PAGE_META)


if __name__ == '__main__':
    unittest.main()
