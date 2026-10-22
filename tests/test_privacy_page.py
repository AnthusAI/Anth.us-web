"""The /privacy/ page and the consent banner ship together (anthus-web43f).

The policy describes the banner as live, so these tests pin the two to each other: the page text, the footer
links, the Papyrus ``consent_mode`` configuration and the order of the gtag consent defaults in the page head.
"""
import json
import re
import unittest
from pathlib import Path

import inquiry_form
import support

WEB = Path(__file__).resolve().parents[1] / "web"
PROJECTION = json.loads((WEB / "projection.json").read_text())
CONSENT = PROJECTION["chrome"]["consent_mode"]

PRODUCTION = support.project_fixture("production")
GUARDED = support.project_fixture("guarded")
PAGE = PRODUCTION.page("/privacy/")
BODY = re.search(r"<main.*?</main>", PAGE, re.S).group(0)
TEXT = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", BODY))


class PrivacyPageTests(unittest.TestCase):
    def test_page_has_one_h1_and_the_expected_sections(self):
        self.assertEqual(BODY.count("<h1>"), 1)
        self.assertIn("Privacy policy", BODY)
        for heading in ("Who we are", "What we collect", "Cookies and similar technologies", "How long we keep it",
                        "Sharing and service providers", "International transfers", "Your rights", "Children",
                        "Changes to this policy"):
            self.assertIn(heading, BODY)

    def test_names_the_operator_and_its_privacy_contact(self):
        self.assertIn("Endymion Corporation, PO Box 398795, Miami Beach, FL 33139", TEXT)
        self.assertIn('<a href="mailto:info@anth.us">info@anth.us</a>', BODY)
        self.assertEqual(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", TEXT)), {"info@anth.us"})

    def test_no_draft_wording_and_no_google_form(self):
        for word in ("draft", "todo", "tbd", "lorem", "placeholder"):
            self.assertNotIn(word, TEXT.lower())
        for needle in ("docs.google.com", "forms.gle", "1FAIpQLS", "Google Form"):
            self.assertNotIn(needle, PAGE)

    def test_describes_the_banner_and_the_stored_choice(self):
        for needle in ("G-31SC26SDGX", "Cookies and analytics", "Reject all", "Accept all", "Cookie settings",
                       "about six months", "European Economic Area, the United Kingdom or Switzerland",
                       "advertising stays off until you accept it", "We do not currently run advertising"):
            self.assertIn(needle, TEXT)
        # about six months is the stored choice: keep the page and the Papyrus setting in step (183 days)
        self.assertEqual(CONSENT.get("retention_days", 183), 183)

    def test_scope_covers_the_product_sites_that_link_here(self):
        for needle in ("Anthus product sites whose pages link to this policy: currently cyclotron.anth.us",
                       "The same Google Analytics property is used on anth.us and on the product sites",
                       "tell the sites apart by hostname", "on each site covered by this policy",
                       "covered by that policy instead"):
            self.assertIn(needle, TEXT)

    def test_describes_the_contact_form_as_it_works(self):
        shipped = inquiry_form.read_config()
        self.assertEqual(shipped["notice_version"], "contact-v1")  # the policy restates this notice
        for phrase in ("never sold", "mailing list", "until you ask us to delete them"):
            self.assertIn(phrase, shipped["privacy_notice"])
        for needle in ("We never sell them", "kept until you ask us to delete them", "utm_campaign",
                       "hidden field", "how long the form was open", "scores it for spam",
                       "Prospectus", "Amazon Web Services", "Google Fonts"):
            self.assertIn(needle, TEXT)

    def test_page_is_registered_and_linked(self):
        page = next(entry for entry in PROJECTION["pages"] if entry["id"] == "privacy")
        self.assertEqual(page["path"], "privacy")
        self.assertEqual(page["source"], "pages/privacy.md")
        self.assertTrue(PRODUCTION.has_page("/privacy/"))
        self.assertIn("<title>Privacy Policy | Anthus</title>", PAGE)


class ConsentBannerTests(unittest.TestCase):
    def test_banner_wording_is_the_approved_wording(self):
        self.assertEqual(CONSENT["privacy_policy_url"], "/privacy/")
        self.assertIn('<h2 id="papyrus-consent-heading">Cookies and analytics</h2>', PAGE)
        self.assertIn("We use cookies to measure how this site is used and, if you agree, for advertising. "
                      "You can accept all, reject all, and change your choice at any time.", PAGE)
        self.assertRegex(PAGE, r'data-papyrus-consent-choice="reject">Reject all</button>')
        self.assertRegex(PAGE, r'data-papyrus-consent-choice="accept">Accept all</button>')
        self.assertIn('href="/privacy/"', re.search(r'id="papyrus-consent-message">.*?</p>', PAGE, re.S).group(0))

    def test_consent_defaults_come_before_the_tag_loads_and_before_config(self):
        # An EEA, UK or Swiss visitor starts denied; everyone else starts with analytics only; both before gtag.js.
        strict = PAGE.index("gtag('consent','default',{ad_storage:'denied'")
        self.assertIn("region:[", PAGE[strict:strict + 600])
        self.assertIn('"DE"', PAGE[strict:strict + 600])
        self.assertIn('"GB"', PAGE[strict:strict + 600])
        self.assertIn('"CH"', PAGE[strict:strict + 600])
        elsewhere = PAGE.index("analytics_storage:'granted'")
        for name in ("ad_storage", "ad_user_data", "ad_personalization"):
            self.assertIn(f"{name}:'denied'", PAGE[elsewhere - 120:elsewhere + 30])
        loads = PAGE.index("googletagmanager.com/gtag/js?id=G-31SC26SDGX")
        configures = PAGE.index("gtag('config'")
        self.assertLess(strict, elsewhere)
        self.assertLess(elsewhere, loads)
        self.assertLess(loads, configures)

    def test_every_page_has_the_banner_and_the_footer_links(self):
        for path in ("/", "/engage/", "/privacy/", "/about/"):
            page = PRODUCTION.page(path)
            self.assertEqual(page.count('id="papyrus-consent-banner"'), 1, path)
            footer = re.search(r'<footer class="site-footer".*?</footer>', page, re.S).group(0)
            self.assertIn('<li><a href="/privacy/">Privacy</a></li>', footer, path)
            self.assertIn('<a href="#" data-papyrus-consent-reopen hidden>Cookie settings</a>', footer, path)

    def test_a_guarded_build_loads_no_analytics_and_no_banner(self):
        page = GUARDED.page("/privacy/")
        self.assertNotIn("googletagmanager", page)
        self.assertNotIn("papyrus-consent-banner", page)


if __name__ == "__main__":
    unittest.main()
