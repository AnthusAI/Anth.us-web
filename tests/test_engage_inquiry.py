"""Visitor behavior for the Prospectus contact intake on the engage page.

The Google Form is retired. The form posts to the Prospectus intake endpoint with
privacy notice contact-v1, and fails closed (no form, honest message) unless the
endpoint, the exact notice version and an approved notice are all configured.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
import inquiry_form
import anthus_pages

ENDPOINT = 'https://intake.example.test/intake/demo'
READY = {
    'endpoint': ENDPOINT, 'notice_version': 'contact-v1',
    'privacy_notice': 'Synthetic test notice.', 'notice_approved': True,
    'fallback_email': 'hello@example.test',
}


def engage(config):
    with patch.object(inquiry_form, 'read_config', return_value=config):
        return anthus_pages.engage_page()


class InquiryTests(unittest.TestCase):
    def test_google_form_is_retired_in_every_state(self):
        for config in (READY, {}, {**READY, 'fallback_email': None}):
            page = engage(config)
            self.assertNotIn('docs.google.com', page)
            self.assertNotIn('1FAIpQLS', page)
            self.assertFalse(hasattr(anthus_pages, 'CONTACT_URL'))

    def test_ready_config_renders_the_intake_form(self):
        page = engage(READY)
        self.assertIn('id="engage-inquiry"', page)
        self.assertIn('method="post"', page)
        self.assertIn('data-endpoint="' + ENDPOINT + '"', page)
        self.assertIn('data-notice-version="contact-v1"', page)
        self.assertIn('Synthetic test notice.', page)
        self.assertIn('/engage-inquiry.js', page)
        self.assertIn('mailto:hello@example.test', page)
        self.assertIn('href="#tell-us"', page)

    def test_shipped_config_opens_the_form_against_production_intake_with_the_approved_notice(self):
        shipped = json.loads((Path(inquiry_form.__file__).with_name('inquiry-config.json')).read_text())
        self.assertEqual(shipped['endpoint'], 'https://icc3xlwlxe.execute-api.us-east-1.amazonaws.com/intake/demo')
        self.assertIs(shipped['notice_approved'], True)
        self.assertEqual(shipped['notice_version'], 'contact-v1')
        self.assertEqual(shipped['fallback_email'], 'info@anth.us')
        page = inquiry_form.render()
        self.assertIn('id="engage-inquiry"', page)
        self.assertIn('data-endpoint="' + shipped['endpoint'] + '"', page)
        self.assertIn(shipped['privacy_notice'], page)
        self.assertIn('data-fallback-email="info@anth.us"', page)
        self.assertIn('mailto:info@anth.us', page)

    def test_unconfigured_state_hides_the_form_and_says_so(self):
        page = engage({})
        self.assertNotIn('id="engage-inquiry"', page)
        self.assertIn('id="engage-inquiry-unavailable"', page)
        self.assertNotIn('mailto:', page)

    def test_unconfigured_state_offers_email_when_an_address_is_configured(self):
        page = engage({'fallback_email': 'hello@example.test'})
        self.assertNotIn('id="engage-inquiry"', page)
        self.assertIn('mailto:hello@example.test', page)

    def test_every_gate_fails_closed(self):
        bad = (
            {**READY, 'endpoint': None},
            {**READY, 'endpoint': 'http://intake.example.test/intake/demo'},
            {**READY, 'endpoint': 'javascript:alert(1)'},
            {**READY, 'endpoint': 'https://user:pw@intake.example.test/x'},
            {**READY, 'endpoint': 'https://intake.example.test/x#frag'},
            {**READY, 'notice_version': 'contact-v2'},
            {**READY, 'notice_version': 'synthetic-demo-v1'},
            {**READY, 'privacy_notice': ''},
            {**READY, 'notice_approved': False},
            {**READY, 'notice_approved': 'yes'},
        )
        for config in bad:
            with patch.object(inquiry_form, 'read_config', return_value=config):
                self.assertNotIn('id="engage-inquiry"', inquiry_form.render(), config)

    def test_bad_fallback_email_is_ignored(self):
        for address in ('not an address', 'a@b', 'x@y.test"><script>', 123):
            html = engage({**READY, 'fallback_email': address})
            self.assertNotIn('mailto:', html)

    def test_form_fields_match_the_prospectus_request_schema(self):
        html = engage(READY)
        for name in ('name', 'email', 'company', 'message', 'website'):
            self.assertIn(f'name="{name}"', html)
        self.assertIn('maxlength="150"', html)
        self.assertIn('maxlength="3000"', html)
        self.assertIn('maxlength="254"', html)

    def test_guidance_comes_before_the_form_and_agrees_with_the_prefill(self):
        page = engage(READY)
        guide, form = page.index('inquiry-guide'), page.index('id="engage-inquiry"')
        self.assertLess(guide, form)
        self.assertNotIn('The form has one open question', page)
        self.assertIn('Four things that help us reply', page)
        self.assertIn('I don’t know yet', page)
        for needle in ('Which solution or problem?', 'Rough volume or scale', 'Do you have an AWS account', 'Timeline'):
            self.assertIn(needle, page[guide:form])
        self.assertEqual(len(anthus_pages.FORM_TEMPLATE.strip().splitlines()), 4)

    def test_honeypot_stays_hidden_and_out_of_tab_order(self):
        page = engage(READY)
        trap = page[page.index('inquiry__trap'):]
        trap = trap[:trap.index('</div>')]
        self.assertIn('hidden', trap.split('>')[0])
        self.assertIn('aria-hidden="true"', trap)
        self.assertIn('tabindex="-1"', trap)
        self.assertIn('autocomplete="off"', trap)
        css = (Path(inquiry_form.__file__).parent / 'css' / 'arcade.css').read_text()
        self.assertIn('.inquiry [hidden]', css)
        self.assertIn('display: none !important', css)

    def test_every_field_has_a_label_bound_by_id(self):
        page = engage(READY)
        for name in ('name', 'email', 'company', 'message'):
            self.assertIn(f'<label for="inquiry-{name}"', page)
            self.assertIn(f'id="inquiry-{name}"', page)


if __name__ == '__main__':
    unittest.main()
