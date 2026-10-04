#!/usr/bin/env python3
"""Build the benchmark sites (benchmark-sites.json) into web/dist-papyrus/ after the Markus build.

Each benchmark site lives in its own repository and is an Astro site that reads
BASE_PATH and SITE_URL. It is built at its pinned commit and copied under its
anth.us path. The SITE_ENV switch applies to it like every other page: a guarded
build marks every benchmark page noindex, removes its analytics (the main site
sends none outside production), and leaves robots.txt alone, and a production
build publishes each benchmark's sitemap and robots rules and keeps the same GA4
property as the main site.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "web"))
import site_env  # noqa: E402

DIST_DIRECTORY = Path(os.environ.get("ANTHUS_BUILD_DIR", REPOSITORY_ROOT / "web" / "dist-papyrus"))
CHECKOUT_DIRECTORY = Path(
    os.environ.get(
        "BENCHMARK_SITES_WORK_DIRECTORY", REPOSITORY_ROOT / ".amplify-cache" / "benchmark-sites"
    )
)
SAFE_PUBLISHED_PATH = re.compile(r"^/[a-z0-9-]+/$")
HEAD_OPEN_TAG = re.compile(r"<head(\s[^>]*)?>", re.I)
REFRESH_OR_NOINDEX = re.compile(
    r'<meta http-equiv="refresh"|<meta name="robots" content="[^"]*noindex', re.I
)

SCRIPT_ELEMENT = re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S)
ANALYTICS_SCRIPT_MARKERS = ("googletagmanager.com", "gtag(", "anthus-no-analytics")


def run(command: list[str], working_directory: Path, extra_environment: dict | None = None) -> None:
    environment = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", **(extra_environment or {})}
    subprocess.run(command, cwd=working_directory, env=environment, check=True)


def check_out_pinned_commit(benchmark_site: dict) -> Path:
    checkout = CHECKOUT_DIRECTORY / benchmark_site["name"]
    if not (checkout / ".git").is_dir():
        checkout.mkdir(parents=True, exist_ok=True)
        run(["git", "init", "--quiet"], checkout)
        run(
            ["git", "remote", "add", "origin", f"https://github.com/{benchmark_site['repository']}.git"],
            checkout,
        )
    run(["git", "fetch", "--quiet", "--depth", "1", "origin", benchmark_site["commit"]], checkout)
    run(["git", "checkout", "--quiet", "--force", "FETCH_HEAD"], checkout)
    return checkout


def built_page_paths(output_directory: Path, robots_disallowed_paths: list[str]) -> list[str]:
    page_paths = []
    for page in sorted(output_directory.rglob("index.html")):
        if REFRESH_OR_NOINDEX.search(page.read_text(encoding="utf-8", errors="ignore")):
            continue
        relative_directory = page.parent.relative_to(output_directory).as_posix()
        page_path = "/" if relative_directory == "." else f"/{relative_directory}/"
        if any(page_path.startswith(disallowed) for disallowed in robots_disallowed_paths):
            continue
        page_paths.append(page_path)
    return page_paths


def mark_every_page_noindex(published_directory: Path) -> int:
    marked = 0
    for page in published_directory.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        if site_env.NOINDEX_META in text:
            continue
        opening = HEAD_OPEN_TAG.search(text)
        if opening is None:
            raise RuntimeError(f"{page}: no <head> to carry the noindex meta")
        text = text[: opening.end()] + site_env.NOINDEX_META + text[opening.end() :]
        page.write_text(text, encoding="utf-8")
        marked += 1
    return marked


def is_analytics_script(script_element: str) -> bool:
    return any(marker in script_element for marker in ANALYTICS_SCRIPT_MARKERS)


def remove_every_analytics_script(published_directory: Path) -> int:
    cleaned = 0
    for page in published_directory.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        without_analytics = SCRIPT_ELEMENT.sub(
            lambda script: "" if is_analytics_script(script.group(0)) else script.group(0), text
        )
        if "googletagmanager.com" in without_analytics:
            raise RuntimeError(f"{page}: analytics remain outside a <script> element")
        if without_analytics != text:
            page.write_text(without_analytics, encoding="utf-8")
            cleaned += 1
    return cleaned


def publish_sitemap_and_robots_rules(
    benchmark_site: dict, output_directory: Path, published_directory: Path, origin: str
) -> int:
    published_path = benchmark_site["publishedPath"]
    disallowed = benchmark_site.get("robotsDisallowedPaths", [])
    page_urls = [
        f"{origin}{published_path.rstrip('/')}{page_path}"
        for page_path in built_page_paths(output_directory, disallowed)
    ]
    (published_directory / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{site_env.SITEMAP_NS}">\n'
        + "\n".join(f"<url><loc>{url}</loc></url>" for url in page_urls)
        + "\n</urlset>\n",
        encoding="utf-8",
    )
    robots = DIST_DIRECTORY / "robots.txt"
    robots_lines = robots.read_text(encoding="utf-8").splitlines()
    for disallowed_path in disallowed:
        robots_lines.insert(
            robots_lines.index("Allow: /") + 1,
            f"Disallow: {published_path.rstrip('/')}{disallowed_path}",
        )
    robots_lines.append(f"Sitemap: {origin}{published_path}sitemap.xml")
    robots.write_text("\n".join(robots_lines) + "\n", encoding="utf-8")
    return len(page_urls)


def main() -> None:
    environment = site_env.resolve()
    site_url = site_env.PRODUCTION_ORIGIN if environment.production else environment.origin
    benchmark_sites = json.loads((REPOSITORY_ROOT / "benchmark-sites.json").read_text(encoding="utf-8"))
    for benchmark_site in benchmark_sites:
        published_path = benchmark_site["publishedPath"]
        if not SAFE_PUBLISHED_PATH.match(published_path):
            raise SystemExit(
                f"{benchmark_site['name']}: publishedPath must look like '/name/', got {published_path!r}"
            )
        print(
            f"Building {benchmark_site['title']} at {benchmark_site['repository']}@"
            f"{benchmark_site['commit'][:12]} for {published_path} ({environment.mode})"
        )
        site_directory = check_out_pinned_commit(benchmark_site) / benchmark_site["siteDirectory"]
        output_directory = site_directory / "dist"
        run(["npm", "ci", "--no-fund", "--no-audit"], site_directory)
        shutil.rmtree(output_directory, ignore_errors=True)
        run(
            ["npm", "run", "build"],
            site_directory,
            {"BASE_PATH": published_path, "SITE_URL": site_url},
        )
        published_directory = DIST_DIRECTORY / published_path.strip("/")
        shutil.rmtree(published_directory, ignore_errors=True)
        shutil.copytree(output_directory, published_directory)
        if environment.production:
            page_count = publish_sitemap_and_robots_rules(
                benchmark_site, output_directory, published_directory, site_url
            )
            print(f"Published {benchmark_site['title']} with {page_count} pages in its sitemap")
        else:
            marked = mark_every_page_noindex(published_directory)
            cleaned = remove_every_analytics_script(published_directory)
            print(
                f"Published {benchmark_site['title']} guarded: {marked} pages marked noindex, "
                f"analytics removed from {cleaned}"
            )


if __name__ == "__main__":
    main()
