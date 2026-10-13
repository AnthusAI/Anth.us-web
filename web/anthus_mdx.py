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

from papyrus_content.markus_renderer.transforms import block_sentinel, inline_sentinel
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
    span_tables: int = 0
    marks: int = 0
    svgs: int = 0
    diagrams: int = 0
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
        self.span_tables += other.span_tables
        self.svgs += other.svgs
        self.diagrams += other.diagrams
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


_WRAPPER_RE = re.compile(
    r"<(?P<tag>div|figure|p)\b(?P<attrs>[^>]*)>\s*"
    r"(?P<image>::image\{[^}]*\})\s*"
    r"(?:<figcaption\b[^>]*>(?P<caption>.*?)</figcaption>\s*)?"
    r"</(?P=tag)>",
    re.S,
)
#: Authored `style={{ ... }}` wrappers around an image, as the CSS they render
#: to (see `_jsx_style_to_css`), mapped to `anthus_dom.IMAGE_WRAPPERS` keys.
#: An unknown style raises: guessing would silently drop layout.
_STYLE_WRAPPERS = {
    "float:right;width:260px;max-width:40%;margin-left:24px;margin-bottom:16px": "float-260",
    "float:right;width:300px;margin-left:20px;margin-bottom:20px": "float-300",
    "max-width:420px;margin:0 auto var(--base-line-height)": "box-420",
    "max-width:26rem;margin:0 auto var(--base-line-height)": "box-26rem",
}


def _wrapper_key(tag: str, attrs: str) -> str | None:
    """Which production wrapper an authored element is, or ``None``.

    ``None`` leaves the element for the generic unwrap.
    """
    cls = re.search(r'class(?:Name)?\s*=\s*"([^"]*)"', attrs)
    classes = cls.group(1).split() if cls else []
    if tag == "div" and "center-full-image" in classes:
        return "div-cfi"
    if tag == "figure" and "center-full-image" in classes:
        return "figure-cfi"
    if tag == "p" and "center-full-image" in classes:
        return "p-cfi"
    if tag == "div" and "center-small-image" in classes:
        return "div-csi"
    if tag == "div" and "style=" in attrs:
        css = _JSX_STYLE_RE.search(attrs)
        css = _jsx_style_to_css(css)[len('style="') : -1] if css else ""
        key = _STYLE_WRAPPERS.get(css)
        if key is None:
            raise ValueError(f"unrecognised styled image wrapper: {attrs!r}")
        return key
    return None


def _convert_image_wrappers(text: str) -> str:
    """Carry an authored wrapper around ``::image{}`` into its ``layout``.

    ``<div className="center-full-image">::image{...}</div>`` is DOM the
    production stylesheet targets, and the wrapper is otherwise lost to the
    generic div/figure unwrap. It is encoded as ``layout="<layout>@<key>"`` --
    ``::image{}`` has no other channel -- and a ``<figcaption>`` becomes the
    ``caption`` attribute. ``anthus_dom.anthus_image_wrap`` decodes both.
    """

    def repl(match: re.Match[str]) -> str:
        key = _wrapper_key(match.group("tag"), match.group("attrs"))
        if key is None:
            return match.group(0)
        directive = match.group("image")
        layout = re.search(r'layout="([^"]*)"', directive)
        base = layout.group(1) if layout else "full"
        if layout:
            directive = directive.replace(layout.group(0), f'layout="{base}@{key}"')
        else:
            directive = directive[:-1] + f' layout="{base}@{key}"}}'
        caption = match.group("caption")
        if caption:
            caption = re.sub(r"\s+", " ", html_to_text(caption)).replace('"', "'")
            directive = directive[:-1].rstrip() + f' caption="{_attr(caption)}"}}'
        return directive

    return _WRAPPER_RE.sub(repl, text)


# --------------------------------------------------------------------------
# JSX comments and hand-authored JSX diagrams
# --------------------------------------------------------------------------

_JSX_COMMENT_RE = re.compile(r"[ \t]*\{/\*.*?\*/\}[ \t]*\n?", re.S)
_DIAGRAM_OPEN_RE = re.compile(
    r'^<div\s+class(?:Name)?="[^"]*\b(?:blockDiagram|comparisonChart)\b[^"]*"[^>]*>', re.M
)
_DIV_TAG_RE = re.compile(r"<(/?)div\b[^>]*>")
_JSX_STYLE_RE = re.compile(r"style=\{\{(.*?)\}\}", re.S)
_JSX_STYLE_ENTRY_RE = re.compile(r"""(\w+)\s*:\s*(?:"([^"]*)"|'([^']*)'|`([^`]*)`|([\d.]+))""")
_JSX_MAP_RE = re.compile(
    r"\{\[(?P<rows>.*?)\]\.map\(\(\[(?P<names>[^\]]*)\]\)\s*=>\s*\((?P<body>.*?)\)\)\}",
    re.S,
)
_JSX_ROW_RE = re.compile(r"\[([^\[\]]*)\]")


def _jsx_style_to_css(match: re.Match[str]) -> str:
    entries = []
    for name, dq, sq, tpl, num in _JSX_STYLE_ENTRY_RE.findall(match.group(1)):
        value = dq or sq or tpl or num
        prop = re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), name)
        entries.append(f"{prop}:{value}")
    return 'style="' + ";".join(entries) + '"'


_TAG_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)\b[^<>]*?(/?)>")
#: A line that opens with one of these continues the paragraph above it (a
#: `<b>` after a text line is the same Markdown paragraph, not new JSX flow).
_INLINE_START_RE = re.compile(r"</?(?:b|i|em|strong|a|code|span|mark|br|sup|sub|small|u)\b", re.I)
_VOID_TAGS = frozenset("br hr img input meta link source col wbr area base embed param track".split())


def _mdx_flow_paragraphs(markup: str) -> str:
    """MDX wraps a line of text inside a *flow* JSX element in ``<p>``.

    An element whose opening tag is alone on its line holds flow content: a run
    of lines that starts with text is Markdown and renders as a paragraph (live
    production shows ``<div class="title"><p>...</p></div>``). An element whose
    opening tag is followed by text on the same line is inline, and its
    children are not wrapped. A line that starts with ``<`` is JSX and is left
    alone. The paragraph's margin is part of the block's height, so this
    matters to layout.
    """
    out: list[str] = []
    buffer: list[str] = []
    stack: list[tuple[bool, bool]] = []  # (content is flow, `<p>` rewritten to `<div>`)

    def flush() -> None:
        # Markdown flow: text lines become a paragraph; `1. ` / `- ` lines
        # become a list (one item per line), as MDX renders them.
        paragraph: list[str] = []
        items: list[str] = []
        kind = ""

        def close_paragraph() -> None:
            if paragraph:
                out.append("<p>" + " ".join(paragraph) + "</p>")
                paragraph.clear()

        def close_list() -> None:
            nonlocal kind
            if items:
                out.append(f"<{kind}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{kind}>")
                items.clear()
                kind = ""

        for text in buffer:
            ordered = re.match(r"\d+\.\s+(.*)", text)
            bullet = re.match(r"[-*]\s+(.*)", text)
            if ordered or bullet:
                close_paragraph()
                want = "ol" if ordered else "ul"
                if kind and kind != want:
                    close_list()
                kind = want
                items.append((ordered or bullet).group(1))
            else:
                close_list()
                paragraph.append(text)
        close_paragraph()
        close_list()
        buffer.clear()

    for line in markup.split("\n"):
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        in_flow = bool(stack and stack[-1][0])
        if not stripped.startswith(("<", "\x01")) or (
            _INLINE_START_RE.match(stripped) and buffer
        ):
            if in_flow:
                buffer.append(stripped)
            else:
                flush()
                out.append(line)
            continue
        flush()
        tags = list(_TAG_RE.finditer(stripped))
        alone = len(tags) == 1 and tags[0].group(0) == stripped
        # `<p style=..>` alone on its line is a flow container whose text MDX
        # wraps in a paragraph again; a browser parser cannot nest `<p>` in
        # `<p>`, so the outer one is emitted as a `<div>` carrying the same
        # inline style (the `p` margin/size rules are all overridden or equal).
        convert = (
            alone
            and tags[0].group(1) == ""
            and tags[0].group(2).lower() == "p"
            and not tags[0].group(3)
        )
        if convert:
            line = line.replace("<p", "<pconv", 1)
        elif (
            alone
            and tags[0].group(1)
            and tags[0].group(2).lower() == "p"
            and stack
            and stack[-1][1]
        ):
            line = line.replace("</p>", "</pconv>")
        out.append(line)
        for tag in tags:
            closing, name, selfclosing = tag.group(1), tag.group(2).lower(), tag.group(3)
            if name in _VOID_TAGS or selfclosing:
                continue
            if closing:
                if stack:
                    stack.pop()
            else:
                stack.append((tag.end() == len(stripped), convert))
    flush()
    text = "\n".join(out)

    def settle(m: re.Match[str]) -> str:
        # Only a `<p>` that really ended up holding a paragraph becomes a `<div>`.
        tag = "div" if "<p>" in m.group(2) else "p"
        return f"<{tag}{m.group(1)}>{m.group(2)}</{tag}>"

    return re.sub(r"<pconv\b([^>]*)>(.*?)</pconv>", settle, text, flags=re.S)


#: JSX camelCase props that are kebab-case in SVG/HTML attributes. Others that
#: are camelCase in SVG itself (`viewBox`, `preserveAspectRatio`, ...) are not here.
_KEBAB_ATTRS = (
    "strokeWidth strokeDasharray strokeDashoffset strokeLinecap strokeLinejoin "
    "strokeOpacity strokeMiterlimit fillOpacity fillRule clipRule fontSize "
    "fontWeight fontStyle fontFamily textAnchor dominantBaseline alignmentBaseline "
    "markerEnd markerStart markerMid stopColor stopOpacity letterSpacing "
    "textDecoration clipPath vectorEffect"
).split()
_KEBAB_RE = re.compile(r"(?<=[\s\"'])(" + "|".join(_KEBAB_ATTRS) + r")(?==)")


def _svg_attribute_names(markup: str) -> str:
    return _KEBAB_RE.sub(
        lambda m: re.sub(r"([A-Z])", lambda c: "-" + c.group(1).lower(), m.group(1)),
        markup,
    )


def _jsx_to_html(markup: str) -> str:
    """JSX attribute spellings -> HTML: ``className``, ``style={{}}``, quotes."""
    markup = _JSX_STYLE_RE.sub(_jsx_style_to_css, markup)
    markup = re.sub(r"\bclassName\s*=\s*'([^']*)'", r'class="\1"', markup)
    markup = re.sub(r"\bclassName\s*=", "class=", markup)
    markup = re.sub(r"(\bclass)=\'([^\']*)\'", r'\1="\2"', markup)
    # A tag's attributes may continue on following lines (a long `aria-label`);
    # fold each tag onto one line so those continuations are not read as text.
    markup = re.sub(
        r"<[A-Za-z][^<>]*>",
        lambda m: re.sub(r"\s*\n\s*", " ", m.group(0)),
        markup,
    )
    markup = _svg_attribute_names(markup)
    markup = _mdx_flow_paragraphs(markup)
    # JSX whitespace: a newline (with its indentation) next to a tag is
    # dropped; one inside text collapses to a single space. HTML would keep
    # both as text nodes, which shows up as stray inline gaps.
    markup = re.sub(r">\s*\n\s*", ">", markup)
    markup = re.sub(r"\s*\n\s*<", "<", markup)
    markup = re.sub(r"\s*\n\s*", " ", markup)
    return markup.replace("\x01", "")


def _expand_jsx_map(match: re.Match[str]) -> str:
    """Expand ``{[[...], ...].map(([a, b]) => ( <jsx/> ))}`` into its rows.

    The corpus has exactly one of these (the "Context Snowball" bars), so this
    handles that shape -- array-of-literal-rows, a destructured parameter list,
    ``{name}`` and ``${name}`` substitutions, ``key=`` -- and refuses anything
    else rather than guessing at JavaScript.
    """
    names = [n.strip() for n in match.group("names").split(",")]
    out = []
    for row in _JSX_ROW_RE.findall(match.group("rows")):
        values = [v.strip().strip("\"'") for v in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", row)]
        if len(values) != len(names):
            raise ValueError(f"cannot expand JSX map row {row!r}")
        body = re.sub(r"\s+key=\{\w+\}", "", match.group("body"))
        for name, value in zip(names, values):
            # \x01 marks text that came from a JSX expression: it is not
            # Markdown, so `_mdx_flow_paragraphs` must not wrap it in a <p>.
            body = body.replace("${" + name + "}", value).replace("{" + name + "}", "\x01" + value)
        out.append(body.strip())
    return "\n".join(out)


_PRE_RE = re.compile(r"^<pre>\s*\n<code>\n(.*?)\n</code>\s*\n</pre>[ \t]*$", re.M | re.S)


def _convert_pre_blocks(text: str) -> str:
    """`<pre>` / `<code>` on their own lines, as MDX renders them.

    MDX reads the text between the two tags as a Markdown paragraph, so
    production's DOM is `<pre><code><p>text</p></code></pre>` (the paragraph's
    margin is part of the block's height). Re-emitted verbatim as a block
    sentinel instead of letting the generic HTML pass turn it into a fenced
    block with stray backticks.
    """
    return _PRE_RE.sub(
        lambda m: "\n\n"
        + block_sentinel(f"<pre><code><p>{_html.escape(m.group(1), quote=False)}</p></code></pre>")
        + "\n\n",
        text,
    )


_PICTURE_RE = re.compile(
    r"<picture>.*?</picture>|<p\s+style=\{\{[^}]*\}\}>\s*<img\b[^>]*?/>\s*</p>", re.S
)


def _convert_picture_blocks(text: str) -> str:
    """Hand-authored `<picture>` and `<p style=..><img/></p>` (dark/light `<source>`s + a styled `<img>`).

    Re-emitted as written, JSX spellings translated, with the site-static
    `/images/<name>` references pointed at the copies committed under
    `web/assets/site/` (the images live in the Anth.us repo's `static/`, not in
    the content submodule). The responsive pipeline cannot express either the
    `prefers-color-scheme` sources or the inline `style`.
    """

    def repl(match: re.Match[str]) -> str:
        markup = _jsx_to_html(match.group(0))
        markup = re.sub(r"\bsrcSet=", "srcset=", markup)
        markup = re.sub(r"\s*/>", ">", markup)
        markup = re.sub(r">\s+<", "><", markup)
        markup = re.sub(r'(src|srcset)="/images/([^"]+)"', r'\1="/assets/site/\2"', markup)
        return "\n\n" + block_sentinel(markup) + "\n\n"

    return _PICTURE_RE.sub(repl, text)


_STYLED_P_RE = re.compile(
    r"^<p\s+style=\{\{(?P<style>[^}]*)\}\}\s*>(?P<text>[^<{}]*?)</p>[ \t]*$", re.M | re.S
)


def _convert_styled_paragraphs(text: str) -> str:
    """`<p style={{...}}>plain text</p>` (the italic captions under diagrams).

    The inline style is the layout (`margin-top:-1em` pulls the caption up under
    its figure); the generic unwrap used to drop it. Plain text only: anything
    with markup or an expression is left to the generic path.
    """

    def repl(m: re.Match[str]) -> str:
        css = _JSX_STYLE_RE.sub(_jsx_style_to_css, "style={{" + m.group("style") + "}}")
        body = _html.escape(re.sub(r"\s+", " ", m.group("text")).strip(), quote=False)
        return "\n\n" + block_sentinel(f"<p {css}>{body}</p>") + "\n\n"

    return _STYLED_P_RE.sub(repl, text)


def _convert_jsx_diagrams(text: str, report: ConversionReport) -> str:
    """Re-emit hand-authored JSX diagram blocks as the HTML they render to.

    `<div className="blockDiagram ...">` trees (about 45 across the corpus:
    stacked-box diagrams, request/response transcripts) are raw markup the
    production stylesheet targets. Markus runs without ``--allow-html``, so
    they go through as Papyrus block sentinels. Only the JSX spellings are
    translated: ``className`` -> ``class`` and ``style={{ a: 'b' }}`` -> CSS.
    The closing tag is found by counting ``<div>`` depth, which is exact here
    because these trees contain no ``<div>`` inside text or code.
    """
    text = _JSX_COMMENT_RE.sub("", text)
    out: list[str] = []
    pos = 0
    while True:
        match = _DIAGRAM_OPEN_RE.search(text, pos)
        if not match:
            out.append(text[pos:])
            break
        depth = 0
        end = None
        for tag in _DIV_TAG_RE.finditer(text, match.start()):
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                end = tag.end()
                break
        if end is None:
            raise ValueError("unbalanced <div> in a blockDiagram")
        markup = text[match.start() : end]
        markup = _JSX_MAP_RE.sub(_expand_jsx_map, markup)
        markup = re.sub(r"<(span|div|p|b|i|br)\b([^>]*?)\s*/>", lambda m: f"<{m.group(1)}{m.group(2)}></{m.group(1)}>" if m.group(1) != "br" else "<br>", markup)
        markup = _jsx_to_html(markup)
        if "{" in markup.replace("var(", ""):
            raise ValueError(f"JSX expression left in diagram markup: {markup[:200]!r}")
        out.append(text[pos : match.start()])
        out.append("\n\n" + block_sentinel(markup) + "\n\n")
        report.diagrams += 1
        report.svgs += len(re.findall(r"<svg\b", markup, re.I))
        pos = end
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
    """Pass authored HTML tables through as block sentinels, verbatim.

    Production renders an MDX ``<table className='data'>`` as that exact
    element, with its ``class`` on the table and on cells (``td.number``), and
    ``colspan``/``rowspan`` where used. A GFM pipe table has no way to carry any
    of that, so converting (which this did before) changed both the markup the
    stylesheet targets and the table's shape. Only the JSX spellings are
    translated (``_jsx_to_html``). Markdown pipe tables are not touched here;
    Markus renders those as production's MDX does.
    """

    def repl(match: re.Match[str]) -> str:
        markup = _jsx_to_html(match.group(0))
        if re.search(r"\b(colspan|rowspan)\s*=", markup, re.I):
            report.span_tables += 1
        else:
            report.tables += 1
        return "\n\n" + block_sentinel(markup) + "\n\n"

    return _TABLE_RE.sub(repl, text)


# --------------------------------------------------------------------------
# Inline and block HTML
# --------------------------------------------------------------------------

_MARK_PAIR_RE = re.compile(r"<mark\b[^>]*>(.*?)</mark\s*>", re.I | re.S)
_MARK_TAG_RE = re.compile(r"</?mark\b[^>]*>", re.I)
_SENTINEL_CHARS_RE = re.compile("[\ue010-\ue01f]")


def _convert_marks(text: str, report: "ConversionReport | None") -> str:
    """``<mark>x</mark>`` -> Papyrus ``inline_sentinel("mark", "x")``.

    Pairs are matched non-greedily, so a nested ``<mark>`` inside a mark keeps
    only the outermost element (the inner tags are stripped). A ``<mark>`` or
    ``</mark>`` left without a partner is dropped and recorded rather than
    emitted unbalanced; an inline sentinel cannot contain another sentinel, so
    a pair whose text already holds one (a block sentinel) is also unwrapped.
    """

    def pair(match: re.Match[str]) -> str:
        inner = _MARK_TAG_RE.sub("", match.group(1))
        if not inner.strip() or _SENTINEL_CHARS_RE.search(inner):
            if report is not None:
                report.dropped_html.append("<mark> unwrapped (empty or holds a sentinel)")
            return inner
        return inline_sentinel("mark", inner)

    text = _MARK_PAIR_RE.sub(pair, text)
    stray = len(_MARK_TAG_RE.findall(text))
    if stray:
        if report is not None:
            report.dropped_html.extend(["<mark> unbalanced tag dropped"] * stray)
        text = _MARK_TAG_RE.sub("", text)
    return text


_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.I | re.S)


def _convert_inline_html(text: str, report: "ConversionReport | None" = None) -> str:
    """Rewrite inline HTML to Markdown equivalents.

    ``<mark>`` becomes a Papyrus inline sentinel (``_convert_marks``), which
    ``FragmentTransform`` decodes back into a real ``<mark>`` after conversion.
    Markus 0.5.1 has neither an ``==highlight==`` plugin nor an inline-span
    directive and raw HTML is disabled; this is how the Anth.us brand
    highlight (204 uses) survives.
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
    # Hug the text with the marker: `<em>\n  text\n</em>` would otherwise
    # become a line starting with `*` and be parsed as a list bullet.
    def _hug(marker: str):
        return lambda m: marker + re.sub(r"\s+", " ", m.group(2)).strip() + marker

    text = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1\s*>", _hug("**"), text, flags=re.I | re.S)
    text = re.sub(r"<(em|i)\b[^>]*>(.*?)</\1\s*>", _hug("*"), text, flags=re.I | re.S)
    text = re.sub(r"</?(strong|b|em|i)\b[^>]*>", "", text, flags=re.I)
    text = _convert_marks(text, report)
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

    # Inline <svg> diagrams survive as a raw sentinel. They are hand-authored
    # vector diagrams with no raster fallback anywhere in the repo, so dropping
    # them left a hole in the article where a diagram belongs. The markup is
    # author-written and never user-supplied, and it is round-tripped verbatim
    # rather than being re-parsed, so this does not reintroduce the raw-HTML
    # injection surface that `--allow-html` would.
    svg_count = len(_SVG_RE.findall(text))
    if svg_count:
        report.svgs += svg_count
        text = _SVG_RE.sub(
            lambda m: "\n\n" + block_sentinel(m.group(0)) + "\n\n", text
        )

    # <picture>/<source> negotiation has no Markus equivalent; keep whatever
    # <img> the element wraps and let _convert_figures resolve it.
    text = re.sub(r"</?picture\b[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<source\b[^>]*/?>", "", text, flags=re.I)

    text = _convert_tables(text, report)
    text = _convert_inline_html(text, report)

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


_PICTOGRAM_RE = re.compile(r"^[ \t]*\{\{pictogram ([a-z0-9-]+)\}\}[ \t]*$", re.M)


def _convert_pictograms(text: str) -> str:
    """``{{pictogram <name>}}`` on its own line embeds an animated pictogram.

    Plain text rather than a directive, so the CMS saves it whatever Markus version it
    validates with; an unknown name fails the build (``arcade_pictograms.render``).
    """
    import arcade_pictograms

    return _PICTOGRAM_RE.sub(
        lambda m: "\n\n" + block_sentinel(
            '<div class="body-px">' + arcade_pictograms.render(m.group(1)) + "</div>"
        ) + "\n\n",
        text,
    )


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

    text = _convert_styled_paragraphs(text)
    text = _convert_pre_blocks(text)
    text = _convert_picture_blocks(text)
    text = _convert_jsx_diagrams(text, report)
    text = _convert_citations(text, report)
    text = _convert_blog_images(text, report, resolve_image_name)
    text = _convert_image_wrappers(text)
    text = _convert_figures(text, report, resolve_image_path)
    text = _convert_block_html(text, report)
    text = _convert_pictograms(text)
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
