"""Projecting the synthetic fixture corpus (tests/fixtures/content) through the real site configuration.

``project_fixture()`` runs ``web/projection.json`` and the hooks of ``web/hooks.py`` over the fixture items with
Papyrus's ``StandardMarkusProjector`` and returns a ``Projection``: every file written, the redirects stored, and the
projection report. Projections are memoised per environment, so the whole suite projects a handful of times.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from papyrus_content.markus_renderer.images import PASSTHROUGH_SUFFIXES, ImagePipeline, gatsby_widths
from papyrus_content.projection.directory_source import DirectoryContentSource
from papyrus_content.projection.engine import ProjectionContext, project_all
from papyrus_content.projection.projector import MarkusSiteProjector
from papyrus_content.projection.writers import LocalDirectoryWriter
from papyrus_content.renditions import meta_key

REPOSITORY = Path(__file__).resolve().parent.parent
WEB = REPOSITORY / "web"
FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"
PRODUCTION = "https://anth.us"
GUARDED_ORIGIN = "https://staging.example.com"

#: The images the fixture items reference: source path -> (width, height) of the (imaginary) original.
FIXTURE_IMAGES = {
    "solutions/images/call-criteria-logo.png": (1200, 630),
    "images/venue-driver-logo.png": (800, 400),
    "images/wide.png": (1400, 700),
    "images/small.png": (300, 200),
}
_FORMATS = ("avif", "webp")
_SUFFIX = {"avif": ".avif", "webp": ".webp", "jpeg": ".jpg", "png": ".png"}


def rendition_record(source: str, size: tuple[int, int] | None, pipeline: ImagePipeline) -> dict:
    """A rendition record shaped like the ones the upload-time function writes, made of plain data.

    A raster image is ``kind: gatsby`` (the site's ``images.gatsby_parity``); a GIF or an SVG is a passthrough.
    """
    if Path(source).suffix.lower() in PASSTHROUGH_SUFFIXES:
        return {"version": 1, "source": source, "kind": "passthrough", "href": f"{pipeline.out_subdir}/{source}", "size": list(size) if size else None}
    width, height = size
    widths, display = gatsby_widths(width, max_width=pipeline.max_width)
    directory = f"{pipeline.out_subdir}/{Path(source).parent.as_posix()}".rstrip("/.") + "/"
    formats = list(pipeline.resolved_formats())
    return {
        "version": 1,
        "source": source,
        "kind": "gatsby",
        "size": [width, height],
        "displayWidth": display,
        "fallbackFormat": "png",
        "placeholder": None,
        "renditions": [
            {
                "width": w,
                "height": max(1, round(height * w / width)),
                "href": f"{directory}{Path(source).stem}-{w}{_SUFFIX[image_format]}",
                "format": image_format,
            }
            for w in widths
            for image_format in dict.fromkeys([*formats, "png"])
        ],
    }


class FakeRenditionStore:
    """A rendition store held in a dict: ``meta.json`` records for the images the corpus references.

    ``images`` maps source -> size. With ``anything=True`` any source asked for gets a plausible record (the real
    export has images this suite has no list of); ``keys`` then answers for the known sources only.
    """

    def __init__(self, images: dict[str, tuple[int, int]] | None = None, *, anything: bool = False) -> None:
        self.pipeline = ImagePipeline(gatsby_parity=True, placeholder=None)
        self.anything = anything
        self.objects: dict[str, bytes] = {}
        for source, size in (FIXTURE_IMAGES if images is None else images).items():
            self.add(source, size)

    def add(self, source: str, size: tuple[int, int] | None) -> None:
        record = rendition_record(source, size, self.pipeline)
        self.objects[meta_key(self.pipeline, source)] = json.dumps(record).encode("utf-8")

    def get(self, key: str) -> bytes | None:
        if key in self.objects:
            return self.objects[key]
        if self.anything and key.endswith(".meta.json"):
            prefix = f"{self.pipeline.out_subdir}/"
            stem = key[len(prefix) : -len(".meta.json")]
            source = stem.rpartition("/")[0] + "/" + stem.rpartition("/")[2] + ".png" if "/" in stem else stem + ".png"
            return json.dumps(rendition_record(source, (1000, 600), self.pipeline)).encode("utf-8")
        return None

    def keys(self, prefix: str) -> list[str]:
        return sorted(key for key in self.objects if key.startswith(prefix))

    def put(self, key: str, body: bytes, *, cache_control: str) -> None:
        self.objects[key] = body


class MemoryRedirectStore:
    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}

    def put_all(self, redirects):
        self.mapping.update(redirects)

    def delete_all(self, sources):
        for source in sources:
            self.mapping.pop(source, None)

    def list_all(self):
        return dict(self.mapping)

    def get(self, source):
        return self.mapping.get(source)


@contextmanager
def site_environment(mode: str = "production"):
    """Set the variables the projector reads: ``production`` (anth.us) or ``guarded`` (a staging origin)."""
    saved = {name: os.environ.get(name) for name in ("PAPYRUS_SITE_ENV", "PAPYRUS_SITE_PUBLIC_URL")}
    try:
        if mode == "production":
            os.environ["PAPYRUS_SITE_ENV"] = "production"
            os.environ["PAPYRUS_SITE_PUBLIC_URL"] = PRODUCTION
        else:
            os.environ["PAPYRUS_SITE_ENV"] = "guarded"
            os.environ["PAPYRUS_SITE_PUBLIC_URL"] = GUARDED_ORIGIN
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def make_projector(store: FakeRenditionStore | None = None, mode: str = "production") -> MarkusSiteProjector:
    with site_environment(mode):
        return MarkusSiteProjector.from_static_directory(WEB, renditions=store or FakeRenditionStore())


def make_context(content: Path, out: Path, *, mode: str = "production", store=None, redirects=None, writer=None, keep_state=False):
    return ProjectionContext(
        source=DirectoryContentSource(content),
        projector=make_projector(store, mode),
        writer=writer or LocalDirectoryWriter(out),
        redirect_store=redirects if redirects is not None else MemoryRedirectStore(),
        keep_state=keep_state,
    )


@dataclass
class Projection:
    out: Path
    redirects: dict[str, str]
    report: object
    files: dict[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.files = {p.relative_to(self.out).as_posix(): p.read_bytes() for p in sorted(self.out.rglob("*")) if p.is_file()}

    def text(self, key: str) -> str:
        return self.files[key].decode("utf-8")

    def page(self, path: str) -> str:
        """The HTML of a site path such as ``/about/`` or ``/``."""
        key = path.strip("/") + "/index.html" if path.strip("/") else "index.html"
        return self.text(key)

    def has_page(self, path: str) -> bool:
        key = path.strip("/") + "/index.html" if path.strip("/") else "index.html"
        return key in self.files

    def main(self, path: str) -> str:
        html = self.page(path)
        return html[html.index("<main") : html.index("</main>")]


_CACHE: dict[tuple, Projection] = {}


def project_directory(content: Path, *, mode: str = "production", store=None) -> Projection:
    out = Path(tempfile.mkdtemp(prefix="anthus-projection-", dir=os.environ.get("ANTHUS_BUILD_DIR")))
    context = make_context(content, out, mode=mode, store=store)
    report = project_all(context)
    assert report.ok, report.errors
    return Projection(out=out, redirects=dict(context.redirect_store.mapping), report=report)


def project_fixture(mode: str = "production") -> Projection:
    key = ("fixture", mode)
    if key not in _CACHE:
        _CACHE[key] = project_directory(FIXTURE_CONTENT, mode=mode)
    return _CACHE[key]


def anchors(html: str) -> list[str]:
    return re.findall(r'<a\b[^>]*href="([^"]*)"', html)


def corpus_with(extra: dict[str, str], *, without: tuple[str, ...] = ()) -> Path:
    """A copy of the fixture corpus plus the given files (``{"articles/x.md": text}``), minus the files in ``without``."""
    import shutil

    path = Path(tempfile.mkdtemp(prefix="anthus-corpus-", dir=os.environ.get("ANTHUS_BUILD_DIR"))) / "content"
    shutil.copytree(FIXTURE_CONTENT, path)
    for name in without:
        (path / name).unlink()
    for name, text in extra.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text, encoding="utf-8")
    return path


def article_text(title: str, *, date: str = "2025-01-01", tags=("AI",), state: str = "published", extra: str = "") -> str:
    """The text of a synthetic article file."""
    return (
        f"---\ntitle: {title}\ndate: '{date}'\ntags: [{', '.join(tags)}]\nstate: {state}\n"
        f"excerpt: <p>About {title}.</p>\n{extra}---\nBody of {title}.\n"
    )


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg"}
_NAMED_IMAGE = re.compile(r"[A-Za-z0-9_./%-]+\.(?:png|jpe?g|gif|webp|avif|svg)\b", re.I)


def store_for_directory(root: Path) -> FakeRenditionStore:
    """A rendition store with a record for every image under ``root`` (sizes read from the files).

    An image an item names but the directory does not ship gets a plausible record, so a corpus export without all
    of its media still projects.
    """
    from PIL import Image

    store = FakeRenditionStore({}, anything=True)
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES:
            source = path.relative_to(root).as_posix()
            try:
                with Image.open(path) as image:
                    store.add(source, image.size)
            except Exception:  # noqa: BLE001 - an SVG, or an unreadable file: a record without a size
                store.add(source, None if path.suffix.lower() in PASSTHROUGH_SUFFIXES else (1000, 600))
    for path in sorted(Path(root).rglob("*.md")):
        for source in _NAMED_IMAGE.findall(path.read_text(encoding="utf-8")):
            source = source.lstrip("/")
            if not source.startswith(("http", "assets/")) and meta_key(store.pipeline, source) not in store.objects:
                store.add(source, None if Path(source).suffix.lower() in PASSTHROUGH_SUFFIXES else (1000, 600))
    return store
