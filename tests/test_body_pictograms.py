"""{{pictogram <name>}} in an article body embeds the animated pictogram (web/source_text.py, the ``source`` hook)."""
import re

import pytest

import arcade_pictograms
import source_text
import support
from papyrus_content.markus_renderer.transforms import block_sentinel


def _clean(body):
    return source_text.clean(body)


def test_token_becomes_a_sentinel_not_text():
    out = _clean("Intro.\n\n{{pictogram relocate}}\n\nAfter.\n")
    assert "{{pictogram" not in out
    assert "Intro." in out and "After." in out
    expected = block_sentinel('<div class="body-px">' + arcade_pictograms.render("relocate") + "</div>")
    assert expected in out


def test_unknown_name_fails():
    with pytest.raises(KeyError):
        _clean("{{pictogram no-such-thing}}\n")


def test_token_inside_code_is_left_alone():
    out = _clean("```\n{{pictogram relocate}}\n```\n")
    assert "{{pictogram relocate}}" in out


def test_the_projected_article_carries_the_figure_once_and_the_code_sample_verbatim():
    page = support.project_fixture().page("/articles/pictured-article/")
    assert page.count('data-px="relocate"') == 1
    assert '<div class="body-px">' in page
    assert "{{pictogram relocate}}" in page  # the fenced sample
    assert "{{pictogram" not in re.sub(r"<code.*?</code>|<pre.*?</pre>", "", page, flags=re.S)


def test_a_venue_article_embeds_its_system_pictogram():
    page = support.project_fixture().page("/articles/venue-driver/")
    assert 'data-px="venue-system"' in page
