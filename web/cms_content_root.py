"""Turn a Papyrus ``export-published`` directory into the content-root layout.

``papyrus ops content export-published --out content-export`` writes the CMS's
published items as ``articles/<slug>.md`` and ``platform/<slug>.md`` plus the
media they reference (every other folder: ``images/``, ``diagrams/``, ``solutions/images/``). The Anth.us build reads a
content root shaped like the former ``anthus-site-content`` submodule: one
``<slug>.mdx`` per article, ``platform/<slug>.mdx`` per platform page, the
media folders, and the retired-name ``redirects/`` stubs. This module builds
that root from the export, so the same renderer serves CMS content unchanged.
"""

from __future__ import annotations

import shutil
from pathlib import Path

EXPORT_CONTENT_SECTIONS = {"articles": "", "platform": "platform"}
NON_MEDIA_FOLDERS = frozenset({"articles", "platform", "_papyrus"})


def materialize_content_root(export_dir: Path, target_dir: Path, redirects_dir: Path) -> Path:
    """Write the content root for ``export_dir`` into ``target_dir`` and return it."""
    if not (export_dir / "_papyrus" / "manifest.json").is_file():
        raise SystemExit(f"{export_dir} is not a papyrus export (no _papyrus/manifest.json).")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)
    (target_dir / "README.md").write_text(
        "Content root derived from a Papyrus export. Generated; never edit.\n", encoding="utf-8"
    )
    for section, destination in EXPORT_CONTENT_SECTIONS.items():
        section_dir = export_dir / section
        if not section_dir.is_dir():
            continue
        destination_dir = target_dir / destination if destination else target_dir
        destination_dir.mkdir(parents=True, exist_ok=True)
        for markdown_file in sorted(section_dir.glob("*.md")):
            shutil.copyfile(markdown_file, destination_dir / f"{markdown_file.stem}.mdx")
    for media_folder in sorted(export_dir.iterdir()):
        if media_folder.is_dir() and media_folder.name not in NON_MEDIA_FOLDERS:
            shutil.copytree(media_folder, target_dir / media_folder.name)
    if redirects_dir.is_dir():
        shutil.copytree(redirects_dir, target_dir / "redirects")
    return target_dir
