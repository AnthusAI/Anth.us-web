"""Visitor behavior for the gated Prospectus inquiry path."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
import inquiry_form
import anthus_pages

class InquiryTests(unittest.TestCase):
    def test_unapproved_intake_keeps_working_contact(self):
        with patch.object(inquiry_form, 'read_config', return_value={}):
            page = anthus_pages.engage_page()
        self.assertIn('docs.google.com/forms/', page)
        self.assertNotIn('id="engage-inquiry"', page)

    def test_approved_intake_offers_form_and_fallback(self):
        with patch.object(inquiry_form, 'read_config', return_value={
            'endpoint': 'https://intake.example.test/contact',
            'notice_version': 'contact-v1', 'privacy_notice': 'Approved notice.'
        }):
            page = anthus_pages.engage_page()
        self.assertIn('id="engage-inquiry"', page)
        self.assertIn('Approved notice.', page)
        self.assertIn('docs.google.com/forms/', page)
        self.assertIn('/engage-inquiry.js', page)

    def test_partial_or_unsafe_config_fails_closed(self):
        for config in ({'endpoint': 'https://example.test'},
                       {'endpoint': 'javascript:alert(1)', 'notice_version': 'v1', 'privacy_notice': 'x'}):
            with patch.object(inquiry_form, 'read_config', return_value=config):
                self.assertEqual(inquiry_form.render(), '')

if __name__ == '__main__':
    unittest.main()
