"""Normalize Anth.us Gatsby MDX into Markus-safe Markdown.

Why this module exists
----------------------
The Anth.us content repo (``content/anthus-site-content``, mounted as a git
submodule and treated as **read-only**) is authored for Gatsby MDX. It contains
three classes of construct a Markus static build cannot consume as-is:

1. **MDX imports and JSX components** — ``<BlogImage>``, ``<Citation>``,
   ``<CitationsList>``, ``<MDXCode>``.
2. **Raw HTML** — ``<div>``, ``<p class=…>``, ``<table>``, ``<mark>``,
   ``<figure>``, inline ``<svg>``. Markus static builds run
   ``markus convert`` **without** ``--allow-html`` (a build-time security
   invariant enforced by ``papyrus_content.markus_renderer.security``), so raw
   HTML is escaped into visible angle brackets rather than rendered.
3. **Gatsby-absolute links** — ``/blog/<slug>/``, ``/platform/<slug>``,
   ``/assets/images/…``. Link rewriting happens later, on rendered HTML, in
   ``build_via_papyrus.py``; this module leaves hrefs alone.

Everything here writes into the gitignored ``web/staging/`` tree. The content
submodule is never written to.

Images and citations: real Papyrus markup
-----------------------------------------
Responsive images and inline citations are Papyrus capabilities now (Papyrus
``docs/markus-content-markup.md``), so this module emits the real authoring
syntax rather than the flattened stand-ins it used to:

* ``render_image_directive()`` — ``::image{src= layout= alt= …}``. Resolved by
  ``ImagePipeline`` into a ``<picture>`` with ``srcset``/``sizes`` and the
  source's intrinsic dimensions.
* ``render_citation_marker()`` / ``render_citations_directive()`` — ``[@key]``
  and ``::citations{format="apa"}``, backed by a front-matter ``citations:``
  block of CSL-JSON that ``staged_markdown()`` re-emits.
* ``render_static_figure()`` — plain ``:::figure{}`` for the one class of image
  the pipeline cannot own: **site chrome** vendored in this repo under
  ``web/assets/site/``. ``::image{}`` resolves ``src`` relative to the image
  pipeline's source root (the content submodule) and rejects absolute paths,
  so an asset that does not live in the submodule has no relative ``src``.

The content corpus is now authored in this syntax directly
(``AnthusAI/anthus-site-content``, branch ``content/markus-native-markup``), so
for that branch the MDX conversion below is a no-op pass-through. It is kept
working because the content repo has two dozen live feature branches that are
still Gatsby MDX, and a build that silently dropped their citations would be
worse than one that renders them. The translation is implemented once, in
``mdx_codemod``, and used both to migrate the corpus and to render
un-migrated branches.

Nothing else in the build knows how images or citations are spelled.
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from mdx_codemod import (
    JSParseError,
    assign_keys,
    parse_citation_data,
    render_citations_block,
)

# --------------------------------------------------------------------------
# Front matter
# --------------------------------------------------------------------------

_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n(?:---|\.\.\.)[ \t]*\n?", re.DOTALL)


def split_front_matter(text: str) -> tuple[dict, str]:
    """Return ``(front_matter, body)``. Missing/blank front matter yields ``{}``.

    Uses PyYAML rather than a hand-rolled scanner because Anth.us front matter
    uses real YAML structures the Pilobol.us-style scalar reader cannot express:
    ``authors:`` is a list of maps, ``tags:`` is a list, ``images:`` is a list,
    and ``excerpt:`` is frequently a block scalar containing HTML.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        data = None
    if not isinstance(data, dict):
        data = {}
    return data, body


def html_to_text(value: str | None) -> str:
    """Flatten an HTML-bearing scalar (``excerpt``, ``author``) to plain text.

    Anth.us excerpts are stored as HTML (``<p>``, ``<ul>``, ``<a>``, ``<mark>``)
    because Gatsby injected them with ``dangerouslySetInnerHTML``. Card blurbs
    and ``<meta>`` descriptions need the text, not the markup.
    """
    if not value:
        return ""
    text = re.sub(r"<li\b[^>]*>", " • ", value)
    text = re.sub(r"</(p|div|ul|ol|li|h[1-6])>", " ", text)
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = _html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def html_to_inline_markdown(value: str | None) -> str:
    """Convert a small HTML scalar to inline Markdown (links and emphasis kept).

    Used for ``authors[].author``, which is authored as
    ``<a href="/ryan">Ryan Porter</a>``.
    """
    if not value:
        return ""
    text = str(value)
    text = _convert_inline_html(text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


# --------------------------------------------------------------------------
# Papyrus content markup: images and citations
# --------------------------------------------------------------------------


def render_image_directive(
    *,
    src: str,
    alt: str = "",
    layout: str | None = None,
    caption: str | None = None,
    credit: str | None = None,
) -> str:
    """Emit Papyrus's responsive-image directive for one image.

    ``src`` must be **relative to the image pipeline's source root**, which
    this build points at the content submodule, because
    ``ImagePipeline`` rejects absolute paths and ``..`` traversal
    (``images.assert_safe_asset_src``). ``layout`` is the Gatsby
    ``className`` -- ``full``, ``centered``, ``right``,
    ``center-small-image``, ``center-full-image``, ``right-aligned`` -- every
    one of which is a known layout in ``DEFAULT_LAYOUT_SIZES``, so it carries
    straight across and drives the CSS class and the ``sizes`` attribute.

    Emitted on one line: the staging tree is generated, never read by a human.
    """
    attrs = [f'src="{_attr(src)}"']
    if layout:
        attrs.append(f'layout="{_attr(layout)}"')
    attrs.append(f'alt="{_attr(alt)}"')
    if caption:
        attrs.append(f'caption="{_attr(caption)}"')
    if credit:
        attrs.append(f'credit="{_attr(credit)}"')
    return "::image{" + " ".join(attrs) + "}"


def render_static_figure(
    *, src: str, alt: str = "", caption: str | None = None
) -> str:
    """Markus's own figure, for an image the responsive pipeline cannot own.

    Site chrome (``/assets/site/…``) is vendored in **this** repo, not in the
    content submodule, so it has no path relative to the pipeline's source
    root and no responsive renditions. It is also already sized for its slot,
    which is why this is a parity note rather than a parity gap.
    """
    attrs = [f'src="{_attr(src)}"', f'alt="{_attr(alt)}"']
    if caption:
        attrs.append(f'caption="{_attr(caption)}"')
    return ":::figure{" + " ".join(attrs) + "}\n:::"


def render_citation_marker(key: str) -> str:
    """Emit the inline citation marker for one citation key.

    Papyrus numbers these by order of first appearance and links each to the
    matching ``::citations{}`` entry, which is what ``gatsby-citation-manager``
    did -- except that it keyed on the entry's *title* and so mis-numbered two
    entries that shared one. See ``mdx_codemod.assign_keys``.
    """
    return f"[@{key}]"


def render_citations_directive(citation_format: str | None) -> str:
    """Emit the end-of-article bibliography directive for ``<CitationsList>``."""
    if not citation_format:
        return "::citations"
    return f'::citations{{format="{_attr(citation_format)}"}}'


# --------------------------------------------------------------------------
# Conversion report
# --------------------------------------------------------------------------


@dataclass
class ConversionReport:
    """What the normalizer had to approximate or drop, per source file.

    Surfaced by the build so parity gaps are counted rather than discovered
    later by a reader. ``dropped_svg`` and ``dropped_html`` are the honest
    failure channels: nothing silently disappears without landing here.
    """

    images: int = 0
    static_figures: int = 0
    citations: int = 0
    citation_lists: int = 0
    tables: int = 0
    marks: int = 0
    dropped_svg: int = 0
    dropped_html: list[str] = field(default_factory=list)
    #: CSL-JSON lifted out of legacy ``<Citation>`` elements on **this page**,
    #: key -> entry, in first-use order. Deliberately *not* merged by
    #: ``merge()``: citation keys only have to be unique within a page, and a
    #: site-wide union would be meaningless. ``stage_nodes`` reads it off the
    #: per-file report before merging.
    citation_entries: dict = field(default_factory=dict)

    def merge(self, other: "ConversionReport") -> None:
        self.images += other.images
        self.static_figures += other.static_figures
        self.citations += other.citations
        self.citation_lists += other.citation_lists
        self.tables += other.tables
        self.marks += other.marks
        self.dropped_svg += other.dropped_svg
        self.dropped_html.extend(other.dropped_html)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _attr(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


_CODE_FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})", re.M)


def _protect_code(text: str) -> tuple[str, list[str]]:
    """Replace fenced code blocks with opaque tokens.

    Every HTML/JSX rewrite below is textual. Code samples in these articles
    contain literal ``<div>``, ``<Citation>`` and ``|`` characters that must
    survive verbatim, so fenced regions are lifted out first and restored last.
    """
    blocks: list[str] = []
    out: list[str] = []
    fence: tuple[str, int] | None = None
    buf: list[str] = []
    for line in text.split("\n"):
        match = _CODE_FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = (match.group("fence")[0], len(match.group("fence")))
                buf = [line]
                continue
            out.append(line)
        else:
            buf.append(line)
            if match and match.group("fence")[0] == fence[0] and len(match.group("fence")) >= fence[1]:
                blocks.append("\n".join(buf))
                out.append(f"\x00CODE{len(blocks) - 1}\x00")
                fence = None
                buf = []
    if fence is not None:
        # Unterminated fence: keep the text rather than lose it.
        blocks.append("\n".join(buf))
        out.append(f"\x00CODE{len(blocks) - 1}\x00")
    return "\n".join(out), blocks


def _restore_code(text: str, blocks: list[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        return blocks[int(match.group(1))]

    return re.sub(r"\x00CODE(\d+)\x00", repl, text)


def _find_jsx_element(text: str, start: int, tag: str) -> tuple[int, int, str] | None:
    """Scan one self-closing JSX element starting at ``start``.

    Regex cannot do this: ``<Citation data={{ … }} />`` nests braces, quotes,
    and ``>`` inside attribute values. Returns ``(start, end, inner)`` where
    ``inner`` is everything between the tag name and the closing ``/>``.
    """
    i = start + 1 + len(tag)
    depth = 0
    quote: str | None = None
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0 and ch == "/" and i + 1 < n and text[i + 1] == ">":
            return start, i + 2, text[start + 1 + len(tag) : i]
        elif depth == 0 and ch == ">":
            # A non-self-closing component. Not used in this corpus; bail so
            # the caller leaves the text alone rather than mangling it.
            return None
        i += 1
    return None


def _jsx_attr(inner: str, name: str) -> str | None:
    """Pull a string-literal JSX attribute value out of an element's attributes."""
    match = re.search(
        rf'\b{re.escape(name)}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|\{{\s*"([^"]*)"\s*\}}|\{{\s*\'([^\']*)\'\s*\}})',
        inner,
    )
    if not match:
        return None
    for group in match.groups():
        if group is not None:
            return group
    return None


# --------------------------------------------------------------------------
# Citations
# --------------------------------------------------------------------------

def _convert_citations(text: str, report: ConversionReport) -> str:
    """Rewrite legacy ``<Citation>``/``<CitationsList>`` to Papyrus markup.

    A no-op on the converted corpus, which already carries ``[@key]`` and
    ``::citations{}``. It exists for the content repo's un-migrated feature
    branches: ``<Citation data={{…CSL…}} />`` becomes an inline ``[@key]`` plus
    an entry in ``report.citation_entries``, which ``staged_markdown()`` writes
    into the page's front-matter ``citations:`` block.

    Keys are assigned by ``mdx_codemod.assign_keys`` -- the same function that
    migrated the corpus -- so a branch rendered here gets byte-identical keys
    to the same branch once it is codemodded.
    """
    elements: list[tuple[int, int, str, str]] = []
    for tag in ("Citation", "CitationsList"):
        pos = 0
        while pos < len(text):
            if text.startswith("<" + tag, pos):
                after = pos + 1 + len(tag)
                if after >= len(text) or not (text[after].isalnum() or text[after] == "_"):
                    found = _find_jsx_element(text, pos, tag)
                    if found:
                        elements.append((found[0], found[1], tag, found[2]))
                        pos = found[1]
                        continue
            pos += 1
    if not elements:
        return text
    elements.sort(key=lambda item: item[0])

    # One key per distinct CSL object, numbered by first use -- the divergence
    # from gatsby-citation-manager that fixes its duplicate-title bug.
    signatures: list[str] = []
    entries: list[dict] = []
    slots: dict[int, int] = {}
    for index, (start, _end, tag, inner) in enumerate(elements):
        if tag != "Citation":
            continue
        try:
            csl = parse_citation_data(inner)
        except JSParseError as exc:
            report.dropped_html.append(f"<Citation> unreadable ({exc})")
            continue
        signature = json.dumps(csl, sort_keys=True, ensure_ascii=False)
        if signature in signatures:
            slots[index] = signatures.index(signature)
        else:
            signatures.append(signature)
            entries.append(csl)
            slots[index] = len(entries) - 1
    keys = assign_keys(entries)
    report.citation_entries = dict(zip(keys, entries))

    pieces = list(text)
    for index in range(len(elements) - 1, -1, -1):
        start, end, tag, inner = elements[index]
        if tag == "CitationsList":
            replacement = "\n\n" + render_citations_directive(
                _jsx_attr(inner, "citationFormat")
            ) + "\n\n"
            report.citation_lists += 1
        elif index in slots:
            replacement = render_citation_marker(keys[slots[index]])
            report.citations += 1
        else:
            replacement = ""
        pieces[start:end] = [replacement]
    return "".join(pieces)


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------


def _emit_image(
    report: ConversionReport,
    *,
    src: str,
    alt: str = "",
    layout: str | None = None,
    caption: str | None = None,
) -> str:
    """Pick the responsive directive or the plain figure, by what ``src`` is.

    A relative ``src`` lives under the image pipeline's source root (the
    content submodule) and gets ``::image{}`` -- renditions, ``srcset``,
    intrinsic dimensions. A site-absolute ``/assets/site/…`` or ``data:`` src
    does not, and gets Markus's own ``:::figure``. See ``render_static_figure``.
    """
    if src.startswith("/") or src.startswith("data:"):
        report.static_figures += 1
        return render_static_figure(src=src, alt=alt, caption=caption)
    report.images += 1
    return render_image_directive(
        src=src, alt=alt, layout=layout, caption=caption
    )


def _convert_blog_images(
    text: str,
    report: ConversionReport,
    resolve: Callable[[str], str | None],
) -> str:
    """Rewrite legacy ``<BlogImage … />`` into ``::image{}``.

    A no-op on the converted corpus. Kept for the content repo's un-migrated
    branches; ``className`` carries across as ``layout`` unchanged, because
    every class this corpus uses is a known Papyrus layout name.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("<BlogImage", i):
            found = _find_jsx_element(text, i, "BlogImage")
            if found:
                _, end, inner = found
                name = _jsx_attr(inner, "name") or ""
                alt = _jsx_attr(inner, "alt") or ""
                layout = _jsx_attr(inner, "className")
                src = resolve(name)
                if src:
                    out.append(
                        "\n\n"
                        + _emit_image(report, src=src, alt=alt, layout=layout)
                        + "\n\n"
                    )
                else:
                    report.dropped_html.append(f"BlogImage name={name!r} (no file found)")
                i = end
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


_IMG_RE = re.compile(r"<img\b([^>]*?)/?>", re.I)
_FIGURE_RE = re.compile(r"<figure\b[^>]*>(.*?)</figure>", re.I | re.S)


def _convert_figures(
    text: str, report: ConversionReport, resolve_path: Callable[[str], str | None]
) -> str:
    """Collapse ``<figure><img><figcaption>`` into one Markus figure directive."""

    def figure_repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        img = _IMG_RE.search(inner)
        if not img:
            # A <figure> wrapping something other than a bare <img> — in this
            # corpus, almost always a <BlogImage> that the previous pass already
            # turned into a :::figure directive. Unwrap it: returning "" here
            # deleted the directive that had just been generated.
            cap = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", inner, re.I | re.S)
            body = re.sub(r"<figcaption\b[^>]*>.*?</figcaption>", "", inner, flags=re.I | re.S)
            out = "\n\n" + body.strip() + "\n\n"
            if cap:
                caption = html_to_text(cap.group(1))
                if caption:
                    out += f"*{caption}*\n\n"
            return out
        attrs = img.group(1)
        src = _html_attr(attrs, "src") or ""
        alt = _html_attr(attrs, "alt") or ""
        cap = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", inner, re.I | re.S)
        caption = html_to_text(cap.group(1)) if cap else None
        resolved = resolve_path(src)
        if not resolved:
            report.dropped_html.append(f"<figure> src={src!r} (unresolved)")
            return ""
        return (
            "\n\n"
            + _emit_image(report, src=resolved, alt=alt, caption=caption)
            + "\n\n"
        )

    text = _FIGURE_RE.sub(figure_repl, text)

    def img_repl(match: re.Match[str]) -> str:
        attrs = match.group(1)
        src = _html_attr(attrs, "src") or ""
        alt = _html_attr(attrs, "alt") or ""
        resolved = resolve_path(src)
        if not resolved:
            report.dropped_html.append(f"<img> src={src!r} (unresolved)")
            return ""
        return "\n\n" + _emit_image(report, src=resolved, alt=alt) + "\n\n"

    return _IMG_RE.sub(img_repl, text)


def _html_attr(attrs: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}\s*=\s*"([^"]*)"', attrs, re.I)
    if match:
        return match.group(1)
    match = re.search(rf"\b{re.escape(name)}\s*=\s*'([^']*)'", attrs, re.I)
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

_TABLE_RE = re.compile(r"<table\b[^>]*>(.*?)</table>", re.I | re.S)
_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL_RE = re.compile(r"<(t[hd])\b([^>]*)>(.*?)</\1>", re.I | re.S)


def _convert_tables(text: str, report: ConversionReport) -> str:
    """Convert raw HTML tables to GFM pipe tables.

    ``colspan``/``rowspan`` have no GFM equivalent; those cells are emitted in
    their first column and the span is recorded as a dropped construct so the
    loss is counted rather than invisible.
    """

    def repl(match: re.Match[str]) -> str:
        body = match.group(1)
        rows: list[list[str]] = []
        for row_match in _ROW_RE.finditer(body):
            cells: list[str] = []
            for cell in _CELL_RE.finditer(row_match.group(1)):
                if re.search(r"\b(colspan|rowspan)\s*=", cell.group(2), re.I):
                    report.dropped_html.append("<table> cell span (no GFM equivalent)")
                inline = _convert_inline_html(cell.group(3))
                inline = re.sub(r"<[^>]+>", "", inline)
                inline = re.sub(r"\s+", " ", _html.unescape(inline)).strip()
                cells.append(inline.replace("|", "\\|"))
            if cells:
                rows.append(cells)
        if not rows:
            report.dropped_html.append("<table> with no parseable rows")
            return ""
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        report.tables += 1
        lines = ["", "| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        return "\n".join(lines)

    return _TABLE_RE.sub(repl, text)


# --------------------------------------------------------------------------
# Inline and block HTML
# --------------------------------------------------------------------------

_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.I | re.S)


def _convert_inline_html(text: str) -> str:
    """Rewrite inline HTML to Markdown equivalents.

    ``<mark>`` becomes ``**bold**``: Markus 0.5.1 enables neither an inline
    ``==highlight==`` plugin nor any inline-span directive, so the Anth.us
    brand highlight (a pink gradient wash behind the phrase) has no faithful
    target. Bold is the closest structural stand-in; the count is reported.
    """
    text = re.sub(
        r'<a\b[^>]*?\bhref\s*=\s*"([^"]*)"[^>]*>(.*?)</a>',
        lambda m: f"[{m.group(2).strip()}]({m.group(1)})",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r"<a\b[^>]*?\bhref\s*=\s*'([^']*)'[^>]*>(.*?)</a>",
        lambda m: f"[{m.group(2).strip()}]({m.group(1)})",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"<code\b[^>]*>(.*?)</code>", lambda m: f"`{m.group(1)}`", text, flags=re.I | re.S)
    text = re.sub(r"</?(strong|b)\b[^>]*>", "**", text, flags=re.I)
    text = re.sub(r"</?(em|i)\b[^>]*>", "*", text, flags=re.I)
    text = re.sub(r"</?mark\b[^>]*>", "**", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "  \n", text, flags=re.I)
    return text


_BLOCK_UNWRAP = ("p", "div", "span", "section", "article", "small", "u", "sup", "sub", "center")

# Real HTML element names. Used to decide whether a leftover ``<thing>`` is
# markup to strip or prose to leave for Markus to escape.
_KNOWN_HTML_TAGS = frozenset(
    """a abbr address area article aside audio b base bdi bdo blockquote body br
    button canvas caption cite code col colgroup data datalist dd del details dfn
    dialog div dl dt em embed fieldset figcaption figure footer form h1 h2 h3 h4
    h5 h6 head header hgroup hr html i iframe img input ins kbd label legend li
    link main map mark menu meta meter nav noscript object ol optgroup option
    output p param picture pre progress q rp rt ruby s samp script section select
    slot small source span strong style sub summary sup table tbody td template
    textarea tfoot th thead time title tr track u ul var video wbr""".split()
)


def _convert_block_html(text: str, report: ConversionReport) -> str:
    report.marks += len(re.findall(r"<mark\b", text, re.I))

    svg_count = len(_SVG_RE.findall(text))
    if svg_count:
        report.dropped_svg += svg_count
        report.dropped_html.append(f"{svg_count} inline <svg> diagram(s) dropped")
        text = _SVG_RE.sub("", text)

    # <picture>/<source> negotiation has no Markus equivalent; keep whatever
    # <img> the element wraps and let _convert_figures resolve it.
    text = re.sub(r"</?picture\b[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<source\b[^>]*/?>", "", text, flags=re.I)

    text = _convert_tables(text, report)
    text = _convert_inline_html(text)

    # List markup -> Markdown bullets. Done after inline conversion so link and
    # emphasis text inside list items survives.
    text = re.sub(r"<li\b[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"</li>", "", text, flags=re.I)
    text = re.sub(r"</?(ul|ol)\b[^>]*>", "\n", text, flags=re.I)

    for tag in _BLOCK_UNWRAP:
        text = re.sub(rf"</?{tag}\b[^>]*>", "\n", text, flags=re.I)

    text = re.sub(r"</?(figcaption|thead|tbody|tfoot|caption|iframe|noscript)\b[^>]*>", "", text, flags=re.I)

    # Headings carry structure, so they become Markdown headings rather than
    # losing their level.
    def heading(match: re.Match[str]) -> str:
        level = int(match.group(1))
        return "\n" + "#" * level + " " + match.group(2).strip() + "\n"

    text = re.sub(
        r"<h([1-6])\b[^>]*>(.*?)</h\1>", heading, text, flags=re.I | re.S
    )

    text = re.sub(
        r"<pre\b[^>]*>(.*?)</pre>",
        lambda m: "\n```\n" + _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip("\n") + "\n```\n",
        text,
        flags=re.I | re.S,
    )

    # Strip the remaining *known* HTML tags, keeping their text. Anything that
    # merely looks tag-shaped (`<N>`, `<arm>`, `<QUERY>` — placeholders in
    # prose, not markup) is deliberately left alone: Markus escapes it, which
    # is what the author meant the reader to see. Stripping those silently ate
    # characters out of sentences.
    leftovers = sorted(
        {tag.lower() for tag in re.findall(r"</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>", text)}
        & _KNOWN_HTML_TAGS
    )
    for tag in leftovers:
        report.dropped_html.append(f"<{tag}> tag stripped (no Markus equivalent)")
    if leftovers:
        pattern = "|".join(re.escape(tag) for tag in leftovers)
        text = re.sub(rf"</?(?:{pattern})\b[^>]*>", "", text, flags=re.I)
    return text


# --------------------------------------------------------------------------
# Top-level entry point
# --------------------------------------------------------------------------

_IMPORT_RE = re.compile(r"^\s*(?:import|export)\s+.*?(?:;|$)\n?", re.M)
_JSX_EXPR_RE = re.compile(r"\{\s*props\.pageContext[^}]*\}")


def normalize_body(
    body: str,
    *,
    resolve_image_name: Callable[[str], str | None],
    resolve_image_path: Callable[[str], str | None],
) -> tuple[str, ConversionReport]:
    """Convert one MDX body to Markus-safe Markdown.

    ``resolve_image_name`` maps a bare ``BlogImage name=`` basename to an
    ``::image{src=}`` value; ``resolve_image_path`` maps an authored ``src``
    (relative or site-absolute) to the same. Both return ``None`` when nothing
    matches, which is recorded as a drop. See ``ImageIndex.content_src``.

    Papyrus markup already in the body -- ``::image{}``, ``[@key]``,
    ``::citations{}``, which is how the corpus is authored now -- passes
    through untouched. ``_protect_code`` keeps it out of code samples, and
    none of the HTML passes below match a directive line.
    """
    report = ConversionReport()
    text, code_blocks = _protect_code(body)

    text = _IMPORT_RE.sub("", text)
    text = _JSX_EXPR_RE.sub("", text)

    text = _convert_citations(text, report)
    text = _convert_blog_images(text, report, resolve_image_name)
    text = _convert_figures(text, report, resolve_image_path)
    text = _convert_block_html(text, report)
    text = _restore_code(text, code_blocks)

    # Collapse the blank-line churn the unwrapping above leaves behind.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n", report


def staged_markdown(front_matter: dict, body: str) -> str:
    """Wrap a normalized body in the front matter Markus/Papyrus reads.

    Only the keys the renderer and this build use are re-emitted, as quoted
    scalars. Re-serializing the original Gatsby front matter wholesale would
    hand Markus YAML it has no schema for (and HTML-bearing excerpts it would
    then have to escape).

    ``citations`` is the exception to "quoted scalars": it is a mapping of key
    -> CSL-JSON that ``CitationRendering`` reads directly off the staged page,
    so it is re-emitted as structured YAML by ``mdx_codemod``'s emitter -- the
    same one that wrote it into the content repo, which is what keeps the two
    byte-identical.
    """
    lines = ["---"]
    for key in ("title", "date", "description", "byline", "slug"):
        value = front_matter.get(key)
        if value in (None, ""):
            continue
        lines.append(f'{key}: "{str(value).replace(chr(34), chr(39))}"')
    citations = front_matter.get("citations")
    if citations:
        lines.append(render_citations_block(citations))
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


def write_if_changed(path: Path, text: str) -> None:
    """Write only on change so dev-server rebuilds do not churn mtimes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")
