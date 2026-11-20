"""Biased-Decisions lives on its own subdomain: the benchmarks page links there and every old path redirects there."""
import json
import re
from pathlib import Path

import anthus_urls
import support
from papyrus_content.projection.standard.redirects import rule_from_mapping

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
INTERNAL_BENCHMARK_LINK = re.compile(r'href="/biased-decisions/')
SUBDOMAIN = "https://biased-decisions.anth.us"


def test_benchmarks_page_links_to_the_subdomain_not_an_internal_path():
    benchmarks_html = support.project_fixture().page("/benchmarks/")
    assert not INTERNAL_BENCHMARK_LINK.search(benchmarks_html)
    assert 'href="https://biased-decisions.anth.us/"' in benchmarks_html


def test_every_biased_decisions_path_redirects_to_the_same_path_on_the_subdomain():
    rules_by_source = {rule["source"]: rule for rule in anthus_urls.BENCHMARK_SUBDOMAIN_REDIRECT_RULES}
    assert set(rules_by_source) == {"/biased-decisions", "/biased-decisions/", "/biased-decisions/<*>"}
    assert rules_by_source["/biased-decisions/<*>"]["target"] == "https://biased-decisions.anth.us/<*>"
    assert all(rule["status"] == "301" for rule in rules_by_source.values())


def test_the_projection_redirects_the_two_exact_paths_and_the_pattern_covers_the_rest():
    redirects = support.project_fixture().redirects
    assert redirects["/biased-decisions"] == f"{SUBDOMAIN}/"
    assert redirects["/biased-decisions/"] == f"{SUBDOMAIN}/"
    raw = json.loads((REPOSITORY_ROOT / "web" / "projection.json").read_text(encoding="utf-8"))["redirects"]["patterns"]
    rules = [rule_from_mapping(entry) for entry in raw]
    rule = next(rule for rule in rules if "biased-decisions" in rule.pattern)
    assert rule.status == 301
    assert rule.apply("/biased-decisions") == f"{SUBDOMAIN}/"
    assert rule.apply("/biased-decisions/") == f"{SUBDOMAIN}/"
    assert rule.apply("/biased-decisions/results/2026") == f"{SUBDOMAIN}/results/2026"
    assert rule.apply("/biased-decisionsx") is None  # only the path itself and what is below it


def test_the_old_path_is_never_a_page_of_this_site_so_the_redirect_cannot_hide_one():
    projection = support.project_fixture()
    assert not any(key.startswith("biased-decisions") for key in projection.files)
    assert not any("<" in source or "<" in target for source, target in projection.redirects.items())

