"""Biased-Decisions lives on its own subdomain: python3 -m pytest -q tests/test_benchmark_subdomain.py"""
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "web"))
import anthus_page_html  # noqa: E402
import anthus_urls  # noqa: E402

INTERNAL_BENCHMARK_LINK = re.compile(r'href="/biased-decisions/')


def test_benchmarks_page_links_to_the_subdomain_not_an_internal_path():
    benchmarks_html = anthus_page_html.benchmarks_html()
    assert not INTERNAL_BENCHMARK_LINK.search(benchmarks_html)
    assert 'href="https://biased-decisions.anth.us/"' in benchmarks_html


def test_every_biased_decisions_path_redirects_to_the_same_path_on_the_subdomain():
    rules_by_source = {
        rule["source"]: rule for rule in anthus_urls.BENCHMARK_SUBDOMAIN_REDIRECT_RULES
    }
    assert set(rules_by_source) == {
        "/biased-decisions",
        "/biased-decisions/",
        "/biased-decisions/<*>",
    }
    assert rules_by_source["/biased-decisions/<*>"]["target"] == "https://biased-decisions.anth.us/<*>"
    assert all(rule["status"] == "301" for rule in rules_by_source.values())


def test_subdomain_redirects_precede_the_catch_all_rule():
    rule_sources = [rule["source"] for rule in anthus_urls.BENCHMARK_SUBDOMAIN_REDIRECT_RULES]
    assert rule_sources
    assert anthus_urls.CATCH_ALL_RULE["source"] == "/<*>"
