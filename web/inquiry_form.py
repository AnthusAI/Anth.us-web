"""Inquiry configuration travels with web/ into the S3 projector Lambda.

Intentionally disabled until Prospectus real-contact intake and notice are
approved. Gatsby/Next build environment variables do not reach this renderer.
"""
import json
from html import escape
from pathlib import Path
from urllib.parse import urlsplit


def read_config():
    return json.loads(Path(__file__).with_name('inquiry-config.json').read_text())


def render():
    config = read_config()
    endpoint = config.get('endpoint') or ''
    parsed = urlsplit(endpoint)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or not config.get('notice_version') or not config.get('privacy_notice')):
        return ''
    return (
        '<form id="engage-inquiry" class="prose" data-endpoint="' + escape(endpoint, quote=True)
        + '" data-notice-version="' + escape(config['notice_version'], quote=True) + '">'
        '<label>Name <input name="name" required maxlength="150" autocomplete="name"></label><br>'
        '<label>Email <input name="email" type="email" required maxlength="254" autocomplete="email"></label><br>'
        '<label>Company (optional) <input name="company" maxlength="150" autocomplete="organization"></label><br>'
        '<label>What’s the problem? <textarea name="message" required maxlength="3000" rows="5"></textarea></label>'
        '<div hidden aria-hidden="true"><label>Website <input name="website" tabindex="-1" autocomplete="off"></label></div>'
        '<p>' + escape(config['privacy_notice']) + '</p>'
        '<p data-error role="alert"></p><div data-receipt role="status" aria-live="polite"></div>'
        '<button type="submit" class="button" disabled>Start an engagement</button>'
        '<noscript><p>Use the contact form link below to send your inquiry.</p></noscript>'
        '</form><script src="/engage-inquiry.js" defer></script>'
    )
