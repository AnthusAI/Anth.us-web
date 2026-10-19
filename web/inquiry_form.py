"""Engage-page contact form for the Prospectus intake endpoint.

Configuration lives in web/inquiry-config.json, which travels with web/ into the
S3 projector Lambda (Gatsby/Next build environment variables do not reach this
renderer). The form is rendered only when every gate is satisfied; otherwise the
page says the form is unavailable and offers email if an address is configured.

  endpoint         https URL of the Prospectus intake route (POST /intake/demo,
                   the EvaluationIntakeUrl stack output). null until confirmed.
  notice_version   must be exactly contact-v1, the version Prospectus accepts.
  privacy_notice   the notice text shown next to the submit button.
  notice_approved  true only once the owner confirms the text is the approved
                   contact-v1 wording.
  fallback_email   optional address shown when the form is unavailable or fails.
"""
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

REQUIRED_NOTICE_VERSION = 'contact-v1'
_EMAIL = re.compile(r'^[^\s@<>"\']+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$')


def read_config():
    return json.loads(Path(__file__).with_name('inquiry-config.json').read_text())


def fallback_email(config):
    address = config.get('fallback_email')
    return address if isinstance(address, str) and _EMAIL.match(address) else None


def is_ready(config):
    endpoint = config.get('endpoint') or ''
    if not isinstance(endpoint, str):
        return False
    parsed = urlsplit(endpoint)
    return (
        parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username
        and not parsed.password and not parsed.fragment
        and config.get('notice_version') == REQUIRED_NOTICE_VERSION
        and isinstance(config.get('privacy_notice'), str) and bool(config['privacy_notice'].strip())
        and config.get('notice_approved') is True
    )


def _email_link(address):
    return '<a href="mailto:' + escape(address, quote=True) + '">' + escape(address) + '</a>'


def render_unavailable(config):
    address = fallback_email(config)
    contact = ' Email us at ' + _email_link(address) + '.' if address else ' Please check back soon.'
    return (
        '<div id="engage-inquiry-unavailable" class="prose"><p>The contact form is not available right now.'
        + contact + '</p></div>'
    )


def render():
    config = read_config()
    if not is_ready(config):
        return render_unavailable(config)
    endpoint = config['endpoint']
    address = fallback_email(config)
    email_note = '<p class="inquiry__alt" data-fallback>Prefer email? ' + _email_link(address) + '</p>' if address else ''
    fallback_attr = ' data-fallback-email="' + escape(address, quote=True) + '"' if address else ''
    return (
        '<form id="engage-inquiry" method="post" action="' + escape(endpoint, quote=True)
        + '" class="inquiry" data-endpoint="' + escape(endpoint, quote=True)
        + '" data-notice-version="' + escape(config['notice_version'], quote=True) + '"' + fallback_attr + '>'
        '<div class="inquiry__field"><label for="inquiry-name">Name</label>'
        '<input id="inquiry-name" name="name" required maxlength="150" autocomplete="name"></div>'
        '<div class="inquiry__field"><label for="inquiry-email">Email</label>'
        '<input id="inquiry-email" name="email" type="email" required maxlength="254" autocomplete="email"></div>'
        '<div class="inquiry__field"><label for="inquiry-company">Company <span class="inquiry__opt">(optional)</span></label>'
        '<input id="inquiry-company" name="company" maxlength="150" autocomplete="organization"></div>'
        '<div class="inquiry__field"><label for="inquiry-message">What’s the problem?</label>'
        '<textarea id="inquiry-message" name="message" required maxlength="3000" rows="9"></textarea></div>'
        '<div class="inquiry__trap" hidden aria-hidden="true"><label>Website <input name="website" tabindex="-1" autocomplete="off"></label></div>'
        '<p class="inquiry__notice" data-notice>' + escape(config['privacy_notice']) + '</p>'
        '<p class="inquiry__error" data-error role="alert"></p>'
        '<div class="inquiry__receipt" data-receipt role="status" aria-live="polite"></div>'
        '<div class="inquiry__actions"><button type="submit" class="btn" disabled>'
        '<span><span class="inquiry__idle">Start an engagement &rarr;</span>'
        '<span class="inquiry__busy">Sending&hellip;</span></span></button></div>'
        + email_note +
        '<noscript><p>This form needs JavaScript.'
        + (' Email us at ' + _email_link(address) + ' instead.' if address else '')
        + '</p></noscript>'
        '</form><script src="/engage-inquiry.js" defer></script>'
    )
