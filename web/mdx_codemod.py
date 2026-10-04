#!/usr/bin/env python3
"""One-shot codemod: Gatsby MDX components -> native Papyrus/Markus markup.

Converts the three JSX constructs in ``AnthusAI/anthus-site-content`` into the
authoring syntax specified by ``Papyrus/docs/markus-content-markup.md``:

| Gatsby MDX                                        | Papyrus Markdown                       |
| ------------------------------------------------- | -------------------------------------- |
| ``<BlogImage images={…} name= className= alt=/>`` | ``::image{src= layout= alt=}``         |
| ``<Citation data={{…CSL…}} />``                   | front-matter ``citations:`` + ``[@key]``|
| ``<CitationsList citationFormat="apa" />``        | ``::citations{format="apa"}``          |

and drops the now-dead ``import`` lines for both components.

Everything else in the corpus is plain Markdown or raw HTML and is left
byte-identical; raw HTML normalization stays the reader site's job
(``web/anthus_mdx.py``), because the live Gatsby build still renders it.

Run it against a **clone** of the content repo on a branch. Never against
``main``: the live Gatsby site at anth.us builds from ``main`` and does not
understand this syntax.

    python3 web/mdx_codemod.py /path/to/anthus-site-content-clone
    python3 web/mdx_codemod.py --check /path/to/clone   # dry run

It is idempotent: a second run finds nothing to convert.

It is also a library. ``web/anthus_mdx.py`` imports the CSL reader, the key
generator and the front-matter emitter from here so that the build can still
render a content branch that has **not** been converted yet -- of which the
content repo has a couple of dozen. One implementation of the translation,
used both to migrate the corpus and to render un-migrated branches.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

SOURCE_SUFFIXES = {".mdx", ".md"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}

#: Longest single-line ``::image{…}`` before it is wrapped across lines.
IMAGE_LINE_BUDGET = 110

#: CSL field order in the emitted front matter. Mirrors the order the
#: authoring contract's example uses; unlisted fields follow, sorted.
CSL_FIELD_ORDER = (
    "type",
    "title",
    "author",
    "editor",
    "container-title",
    "publisher",
    "publisher-place",
    "volume",
    "issue",
    "page",
    "DOI",
    "ISBN",
    "URL",
    "issued",
    "accessed",
)


# ==========================================================================
# A tolerant parser for the JS object literals in `data={{ … }}`
# ==========================================================================


class JSParseError(ValueError):
    """The ``data={{…}}`` attribute was not a readable JS object literal."""


_WHITESPACE = " \t\r\n"
_NUMBER_RE = re.compile(r"-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
_IDENT_RE = re.compile(r"[A-Za-z_$][\w$-]*")
_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f",
    "\\": "\\", "/": "/", "'": "'", '"': '"', "`": "`", "\n": "",
}


class _JSReader:
    """Just enough of JS to read a CSL-JSON object literal.

    `json` cannot: keys are unquoted, strings are single-quoted, and trailing
    commas appear. `ast.literal_eval` cannot either, for the same reasons.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def fail(self, message: str) -> None:
        context = self.text[max(0, self.pos - 40) : self.pos + 40]
        raise JSParseError(f"{message} at offset {self.pos}: {context!r}")

    def skip(self) -> None:
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char in _WHITESPACE:
                self.pos += 1
            elif self.text.startswith("//", self.pos):
                end = self.text.find("\n", self.pos)
                self.pos = len(self.text) if end < 0 else end + 1
            elif self.text.startswith("/*", self.pos):
                end = self.text.find("*/", self.pos)
                if end < 0:
                    self.fail("unterminated comment")
                self.pos = end + 2
            else:
                return

    def value(self) -> Any:
        self.skip()
        if self.pos >= len(self.text):
            self.fail("unexpected end of input")
        char = self.text[self.pos]
        if char == "{":
            return self.obj()
        if char == "[":
            return self.arr()
        if char in "\"'`":
            return self.string()
        for word, literal in (("true", True), ("false", False), ("null", None)):
            if self.text.startswith(word, self.pos):
                self.pos += len(word)
                return literal
        match = _NUMBER_RE.match(self.text, self.pos)
        if match:
            self.pos = match.end()
            raw = match.group(0)
            return float(raw) if any(c in raw for c in ".eE") else int(raw)
        self.fail("unrecognised value")

    def string(self) -> str:
        quote = self.text[self.pos]
        self.pos += 1
        out: list[str] = []
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "\\":
                nxt = self.text[self.pos + 1]
                if nxt == "u":
                    out.append(chr(int(self.text[self.pos + 2 : self.pos + 6], 16)))
                    self.pos += 6
                    continue
                out.append(_ESCAPES.get(nxt, nxt))
                self.pos += 2
                continue
            if char == quote:
                self.pos += 1
                return "".join(out)
            out.append(char)
            self.pos += 1
        self.fail("unterminated string")
        return ""  # unreachable

    def key(self) -> str:
        self.skip()
        if self.text[self.pos] in "\"'`":
            return self.string()
        match = _IDENT_RE.match(self.text, self.pos)
        if not match:
            self.fail("expected an object key")
        self.pos = match.end()
        return match.group(0)

    def obj(self) -> dict:
        self.pos += 1
        out: dict[str, Any] = {}
        while True:
            self.skip()
            if self.pos >= len(self.text):
                self.fail("unterminated object")
            if self.text[self.pos] == "}":
                self.pos += 1
                return out
            name = self.key()
            self.skip()
            if self.text[self.pos] != ":":
                self.fail("expected ':'")
            self.pos += 1
            out[name] = self.value()
            self.skip()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1

    def arr(self) -> list:
        self.pos += 1
        out: list[Any] = []
        while True:
            self.skip()
            if self.pos >= len(self.text):
                self.fail("unterminated array")
            if self.text[self.pos] == "]":
                self.pos += 1
                return out
            out.append(self.value())
            self.skip()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1


def parse_citation_data(inner: str) -> dict:
    """Read the CSL object out of a ``<Citation data={{ … }} />`` attribute list."""
    match = re.search(r"\bdata\s*=\s*\{", inner)
    if not match:
        raise JSParseError("no data= attribute")
    reader = _JSReader(inner)
    reader.pos = match.end()  # just past the JSX expression's opening brace
    value = reader.value()
    reader.skip()
    if reader.pos >= len(inner) or inner[reader.pos] != "}":
        raise JSParseError("unterminated data={…}")
    if not isinstance(value, dict):
        raise JSParseError(f"data= is {type(value).__name__}, expected an object")
    return value


# ==========================================================================
# JSX element scanning
# ==========================================================================


def find_self_closing(text: str, start: int, tag: str) -> tuple[int, int, str] | None:
    """Scan one self-closing JSX element at ``start``; return (start, end, inner).

    Regex cannot do this: ``data={{ … }}`` nests braces, quotes and ``>``
    inside an attribute value.
    """
    pos = start + 1 + len(tag)
    depth = 0
    quote: str | None = None
    while pos < len(text):
        char = text[pos]
        if quote:
            if char == "\\":
                pos += 2
                continue
            if char == quote:
                quote = None
            pos += 1
            continue
        if char in "\"'`":
            quote = char
            pos += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0 and char == "/" and text.startswith("/>", pos):
            return start, pos + 2, text[start + 1 + len(tag) : pos]
        elif depth == 0 and char == ">":
            return None  # a container element; nothing in this corpus uses one
        pos += 1
    return None


def scan_elements(text: str, tag: str) -> list[tuple[int, int, str]]:
    """Every self-closing ``<tag … />`` in ``text``, in document order."""
    found: list[tuple[int, int, str]] = []
    pos = 0
    while pos < len(text):
        if text.startswith("<" + tag, pos):
            after = pos + 1 + len(tag)
            if after >= len(text) or not (text[after].isalnum() or text[after] == "_"):
                element = find_self_closing(text, pos, tag)
                if element:
                    found.append(element)
                    pos = element[1]
                    continue
        pos += 1
    return found


def jsx_string_attr(inner: str, name: str) -> str | None:
    """A string-literal JSX attribute value (``x="y"``, ``x='y'``, ``x={"y"}``)."""
    match = re.search(
        rf'\b{re.escape(name)}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|'
        rf'\{{\s*"([^"]*)"\s*\}}|\{{\s*\'([^\']*)\'\s*\}})',
        inner,
    )
    if not match:
        return None
    return next(group for group in match.groups() if group is not None)


_FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})", re.M)


def mask_code(text: str) -> tuple[str, list[str]]:
    """Park fenced code blocks behind sentinels.

    Several articles print ``<BlogImage …/>`` and ``<Citation …/>`` inside
    code samples as documentation. Those must survive verbatim.
    """
    blocks: list[str] = []
    out: list[str] = []
    fence: tuple[str, int] | None = None
    buffer: list[str] = []
    for line in text.split("\n"):
        match = _FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = (match.group("fence")[0], len(match.group("fence")))
                buffer = [line]
                continue
            out.append(line)
        else:
            buffer.append(line)
            if (
                match
                and match.group("fence")[0] == fence[0]
                and len(match.group("fence")) >= fence[1]
            ):
                blocks.append("\n".join(buffer))
                out.append(f"\x00CODE{len(blocks) - 1}\x00")
                fence = None
                buffer = []
    if fence is not None:
        blocks.append("\n".join(buffer))
        out.append(f"\x00CODE{len(blocks) - 1}\x00")
    return "\n".join(out), blocks


def unmask_code(text: str, blocks: list[str]) -> str:
    return re.sub(r"\x00CODE(\d+)\x00", lambda m: blocks[int(m.group(1))], text)


# ==========================================================================
# Citation keys
# ==========================================================================

_ARTICLES = {"a", "an", "the"}
_TAIL_STOP = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by",
    "with", "from", "is", "are", "was", "were", "be", "been", "as", "its",
    "it", "that", "this", "your", "our", "their", "my", "we", "must", "can",
    "will", "not", "how", "why", "what", "which", "who", "than", "so", "just",
    "have", "has", "had", "do", "does", "did", "up", "out", "about",
}
_CONTAINER_STOP = {"the", "a", "an", "of", "and"}
#: Words that mark an `author` string as an organization rather than a person,
#: so the whole name is used instead of a surname.
_ORG_WORDS = {
    "group", "inc", "inc.", "llc", "ltd", "corp", "corporation", "co", "co.",
    "lab", "labs", "laboratory", "team", "working", "institute", "foundation",
    "project", "committee", "press", "university", "college", "center",
    "centre", "society", "association", "council", "agency", "department",
    "ministry", "bureau", "office", "staff", "editors", "contributors",
}
#: Credentials and "et al." trailers that are not part of a name.
_NAME_TRAILERS = re.compile(
    r"(?:\s*,\s*|\s+)(?:et\.?\s*al\.?|ph\.?\s*d\.?|cfa\.?|m\.?\s*d\.?|"
    r"jr\.?|sr\.?|esq\.?|mba|phd)\s*$",
    re.I,
)
_HOST_NOISE = {"com", "org", "net", "io", "gov", "edu", "co", "uk", "ai", "dev"}

MAX_TITLE_WORDS = 6


def _fold(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _slug(value: Any) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", _fold(value).lower())).strip("-")


def _words(value: Any) -> list[str]:
    return [word for word in _slug(value).split("-") if word]


def _trim_tail(words: list[str], limit: int) -> list[str]:
    picked = words[:limit]
    while picked and picked[-1] in _TAIL_STOP:
        picked.pop()
    return picked


def _first_name_string(value: Any) -> str:
    """The first contributor out of whatever shape ``author`` happens to be.

    Much of this corpus puts several people in one string -- ``"Yue Zhang and
    Yafu Li and …"``, ``"Ilia Shumailov, Zakhar Shumaylov, …"``, ``"Dan Milmo
    and agency"``. The CSL stays as authored (see ``normalize_csl``); only the
    key derivation looks inside.
    """
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    if isinstance(value, dict):
        return str(value.get("family") or value.get("literal") or "").strip()
    text = _NAME_TRAILERS.sub("", str(value or "").strip())
    text = re.split(r"\s+and\s+|\s*;\s*|\s*,\s*", text)[0].strip()
    return text


def _surname_or_org(name: str) -> str:
    """``"Mark J. Nigrini"`` -> ``nigrini``; ``"CREW AI"`` -> ``crew-ai``."""
    words = name.split()
    if not words:
        return ""
    organizational = (
        len(words) == 1
        or any(word.lower().strip(".,") in _ORG_WORDS for word in words)
        or (len(words[-1]) >= 2 and words[-1].isupper())
    )
    if organizational:
        return "-".join(_words(name)[:4])
    return _slug(words[-1])


def _authority(csl: dict) -> str:
    """Whose work it is: first author/editor, else the container, else the host."""
    for field_name in ("author", "editor"):
        if csl.get(field_name):
            name = _surname_or_org(_first_name_string(csl[field_name]))
            if name:
                return name
    for field_name in ("container-title", "publisher"):
        if csl.get(field_name):
            words = [w for w in _words(csl[field_name]) if w not in _CONTAINER_STOP]
            if words:
                return "-".join(words[:4])
    url = str(csl.get("URL") or csl.get("url") or "")
    if url:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        parts = [part for part in host.split(".") if part not in _HOST_NOISE]
        if parts:
            return _slug(parts[0])
    return "anon"


def _year(csl: dict) -> str:
    for field_name in ("issued", "accessed"):
        value = csl.get(field_name)
        if isinstance(value, dict):
            parts = value.get("date-parts") or []
            if parts and isinstance(parts[0], (list, tuple)) and parts[0]:
                try:
                    return str(int(parts[0][0]))
                except (TypeError, ValueError):
                    pass
        elif value:
            match = re.search(r"\b(1\d{3}|2\d{3})\b", str(value))
            if match:
                return match.group(1)
    return "nd"


def _qualifier(csl: dict) -> str:
    """The trailing parenthetical the author used to tell two uses apart.

    ``gatsby-citation-manager`` numbered by *title*, so citing one page for two
    different claims meant giving each a distinct title -- hence entries like
    ``"Pentagon releases … strategy (responsible AI definition)"``. That
    parenthetical is the author's own disambiguator, so it is the first thing
    tried when two keys collide.
    """
    match = re.search(r"\(([^()]+)\)\s*$", str(csl.get("title") or "").strip())
    if not match:
        return ""
    return "-".join(_trim_tail(_words(match.group(1)), 3))


def _title_slug(csl: dict, limit: int = MAX_TITLE_WORDS) -> str:
    title = re.sub(r"\s*\([^()]*\)\s*$", "", str(csl.get("title") or "")).strip()
    head = title.split(":")[0]
    source = head if len(_words(head)) >= 3 else title
    words = _words(source)
    if len(words) > 1 and words[0] in _ARTICLES:
        words = words[1:]
    return "-".join(_trim_tail(words, limit)) or "untitled"


def base_key(csl: dict) -> str:
    return _slug("-".join(p for p in (_authority(csl), _year(csl), _title_slug(csl)) if p))


def _key_candidates(csl: dict):
    """Keys to try for one entry, most readable first."""
    head = _slug(f"{_authority(csl)}-{_year(csl)}")
    qualifier = _qualifier(csl)
    yield _slug(f"{head}-{_title_slug(csl)}")
    if qualifier:
        yield _slug(f"{head}-{_title_slug(csl)}-{qualifier}")
    for limit in range(MAX_TITLE_WORDS + 2, MAX_TITLE_WORDS + 9, 2):
        longer = _slug(f"{head}-{_title_slug(csl, limit)}")
        yield longer
        if qualifier:
            yield _slug(f"{longer}-{qualifier}")


def assign_keys(entries: list[dict]) -> list[str]:
    """Unique, readable keys for one page's entries, in first-use order."""
    taken: set[str] = set()
    keys: list[str] = []
    for csl in entries:
        chosen = None
        for candidate in _key_candidates(csl):
            if candidate not in taken:
                chosen = candidate
                break
        if chosen is None:
            base = base_key(csl)
            suffix = 2
            while f"{base}-{suffix}" in taken:
                suffix += 1
            chosen = f"{base}-{suffix}"
        taken.add(chosen)
        keys.append(chosen)
    return keys


# ==========================================================================
# Front-matter emission
# ==========================================================================


def _yaml_scalar(value: Any) -> str:
    """One YAML scalar, quoted by PyYAML exactly as much as it needs to be."""
    dumped = yaml.safe_dump(
        value, allow_unicode=True, default_flow_style=True, width=1 << 30
    )
    if dumped.endswith("\n...\n"):
        dumped = dumped[: -len("\n...\n")]
    return dumped.strip()


def _yaml_value(value: Any) -> str:
    """One CSL field value as inline YAML (flow style, one line)."""
    if isinstance(value, dict):
        inner = ", ".join(f"{key}: {_yaml_value(val)}" for key, val in value.items())
        return "{" + inner + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_yaml_value(item) for item in value) + "]"
    return _yaml_scalar(value)


def _ordered_fields(csl: dict) -> list[str]:
    known = [name for name in CSL_FIELD_ORDER if name in csl]
    return known + sorted(set(csl) - set(known))


def render_citations_block(entries: dict[str, dict], indent: str = "  ") -> str:
    """The front-matter ``citations:`` block, in cited order."""
    lines = ["citations:"]
    for key, csl in entries.items():
        lines.append(f"{indent}{_yaml_scalar(key)}:")
        for name in _ordered_fields(csl):
            lines.append(f"{indent * 2}{name}: {_yaml_value(csl[name])}")
    return "\n".join(lines)


_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(?P<yaml>.*?)\n(?:---|\.\.\.)[ \t]*\n", re.DOTALL)


def split_front_matter(text: str) -> tuple[str | None, str, str]:
    """``(yaml_text, closing_delimiter_line, body)``; ``None`` when absent."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return None, "", text
    closing = text[match.end() - 4 : match.end()]
    return match.group("yaml"), closing, text[match.end() :]


# ==========================================================================
# Image resolution
# ==========================================================================


@dataclass
class ImageIndex:
    """Resolve a ``BlogImage name=`` basename to a repo-relative path.

    Gatsby matched ``relativePath.endsWith(name)`` across every file in the
    graph. Two basenames in this corpus match more than one file, so the
    preference order is: exact basename first, then the shallowest path.
    """

    root: Path
    paths: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, root: Path) -> "ImageIndex":
        paths = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in IMAGE_SUFFIXES
            and ".git" not in path.parts
        )
        return cls(root=root, paths=paths)

    def candidates(self, name: str) -> list[str]:
        name = (name or "").strip()
        if not name:
            return []
        exact = [p for p in self.paths if p.rsplit("/", 1)[-1] == name.rsplit("/", 1)[-1]]
        pool = exact or [p for p in self.paths if p.endswith(name)]
        return sorted(pool, key=lambda p: (p.count("/"), len(p), p))

    def resolve(self, name: str) -> str | None:
        found = self.candidates(name)
        return found[0] if found else None


# ==========================================================================
# Directive emission
# ==========================================================================


def _attr(value: str) -> str:
    """One directive attribute value. Quotes and braces are absent from this
    corpus and unsupported by the directive grammar, so refuse them loudly."""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if '"' in text or "{" in text or "}" in text:
        raise ValueError(f"attribute value cannot contain a quote or brace: {text!r}")
    return text


def render_image_directive(
    *, src: str, alt: str = "", layout: str | None = None
) -> str:
    """``::image{…}``, wrapped across lines when a single line gets unwieldy."""
    pairs = [("src", _attr(src))]
    if layout:
        pairs.append(("layout", _attr(layout)))
    pairs.append(("alt", _attr(alt)))
    one_line = "::image{" + " ".join(f'{k}="{v}"' for k, v in pairs) + "}"
    if len(one_line) <= IMAGE_LINE_BUDGET:
        return one_line
    lines = ["::image{"]
    for key, value in pairs:
        chunk = f'  {key}="{value}"'
        if len(chunk) <= IMAGE_LINE_BUDGET:
            lines.append(chunk)
            continue
        # Wrap a long alt across lines; the renderer collapses the whitespace.
        words = value.split(" ")
        current = f'  {key}="'
        parts: list[str] = []
        for word in words:
            if current.strip() and len(current) + len(word) + 1 > IMAGE_LINE_BUDGET:
                parts.append(current.rstrip())
                current = "  " + word + " "
            else:
                current += word + " "
        parts.append(current.rstrip() + '"')
        lines.extend(parts)
    lines.append("}")
    return "\n".join(lines)


def render_citations_directive(fmt: str | None) -> str:
    return f'::citations{{format="{_attr(fmt)}"}}' if fmt else "::citations"


# ==========================================================================
# The codemod
# ==========================================================================

_DEAD_IMPORT_RE = re.compile(
    r"^[ \t]*import\s+(?:BlogImage\b[^\n]*?blog-image|"
    r"\{[^}\n]*\b(?:Citation|CitationsList)\b[^}\n]*\}[^\n]*?gatsby-citation-manager)"
    r"['\"]?;?[ \t]*\n",
    re.M,
)

_BLOCK_TOKEN_RE = re.compile(r"\x01BLOCK(\d+)\x01")


@dataclass
class FileResult:
    path: Path
    text: str
    images: int = 0
    images_dropped: list[str] = field(default_factory=list)
    multi_match: list[tuple[str, list[str]]] = field(default_factory=list)
    inline_images: list[str] = field(default_factory=list)
    citations: int = 0
    citation_entries: dict[str, dict] = field(default_factory=dict)
    repeated_uses: list[str] = field(default_factory=list)
    numeric_keys: list[str] = field(default_factory=list)
    citation_lists: int = 0
    changed: bool = False


def _place_blocks(text: str, blocks: dict[str, str]) -> str:
    """Put each block directive alone on its own line at column zero.

    Column zero matters: 27 ``<BlogImage>`` uses sit at four spaces of JSX
    indentation inside a ``<div>``, and a four-space-indented line is an
    indented code block in Markdown.
    """
    out: list[str] = []
    for line in text.split("\n"):
        if not _BLOCK_TOKEN_RE.search(line):
            out.append(line)
            continue
        cursor = 0
        pieces: list[tuple[str, bool]] = []
        for match in _BLOCK_TOKEN_RE.finditer(line):
            before = line[cursor : match.start()].strip()
            if before:
                pieces.append((before, False))
            pieces.append((blocks[match.group(0)], True))
            cursor = match.end()
        trailing = line[cursor:].strip()
        if trailing:
            pieces.append((trailing, False))
        for index, (piece, is_block) in enumerate(pieces):
            # A block directive needs a blank line on both sides, including
            # against the *previous* line: two directives on consecutive lines
            # are one paragraph to Markdown, and the renderer then nests both
            # <figure>s inside one <p>.
            if is_block or index:
                out.append("")
            out.extend(piece.split("\n"))
            if is_block:
                out.append("")
    return "\n".join(out)


def convert_text(text: str, path: Path, images: ImageIndex) -> FileResult:
    result = FileResult(path=path, text=text)
    front_matter, closing, body = split_front_matter(text)
    prefix = text[: len(text) - len(body)]

    masked, code_blocks = mask_code(body)

    elements: list[tuple[int, int, str, str]] = []
    for tag in ("BlogImage", "Citation", "CitationsList"):
        for start, end, inner in scan_elements(masked, tag):
            elements.append((start, end, tag, inner))
    elements.sort(key=lambda item: item[0])
    if not elements and not _DEAD_IMPORT_RE.search(masked):
        return result

    # --- citations: one key per distinct CSL object, in first-use order ----
    signatures: list[str] = []
    entries: list[dict] = []
    per_element_entry: dict[int, int] = {}
    for index, (start, _end, tag, inner) in enumerate(elements):
        if tag != "Citation":
            continue
        try:
            csl = parse_citation_data(inner)
        except JSParseError as exc:
            raise SystemExit(f"{path}: unreadable <Citation> at offset {start}: {exc}")
        signature = json.dumps(csl, sort_keys=True, ensure_ascii=False)
        if signature in signatures:
            slot = signatures.index(signature)
            result.repeated_uses.append(str(csl.get("title") or signature[:60]))
        else:
            signatures.append(signature)
            entries.append(csl)
            slot = len(entries) - 1
        per_element_entry[index] = slot
    keys = assign_keys(entries)
    for key, csl in zip(keys, entries):
        if re.search(r"-\d+$", key) and not re.search(r"-\d+$", base_key(csl)):
            result.numeric_keys.append(key)
    result.citation_entries = dict(zip(keys, entries))

    # --- rewrite, right to left so earlier offsets stay valid -------------
    blocks: dict[str, str] = {}
    pieces = list(masked)
    for index in range(len(elements) - 1, -1, -1):
        start, end, tag, inner = elements[index]
        if tag == "Citation":
            replacement = f"[@{keys[per_element_entry[index]]}]"
            result.citations += 1
        elif tag == "CitationsList":
            token = f"\x01BLOCK{len(blocks)}\x01"
            blocks[token] = render_citations_directive(
                jsx_string_attr(inner, "citationFormat")
            )
            replacement = token
            result.citation_lists += 1
        else:
            name = jsx_string_attr(inner, "name") or ""
            alt = jsx_string_attr(inner, "alt") or ""
            layout = jsx_string_attr(inner, "className")
            found = images.candidates(name)
            if not found:
                # Nothing in the repo matches the name. Gatsby rendered
                # "No image found for: <name>" here, so there is nothing to
                # preserve; the drop is reported instead.
                result.images_dropped.append(name)
                replacement = ""
            else:
                if len(found) > 1:
                    result.multi_match.append((name, found))
                line_end = masked.find("\n", end)
                tail = masked[end : line_end if line_end >= 0 else len(masked)]
                if tail.strip():
                    result.inline_images.append(name)
                token = f"\x01BLOCK{len(blocks)}\x01"
                blocks[token] = render_image_directive(
                    src=found[0], alt=alt, layout=layout
                )
                replacement = token
                result.images += 1
        pieces[start:end] = [replacement]
    masked = "".join(pieces)

    masked = _DEAD_IMPORT_RE.sub("", masked)
    masked = _place_blocks(masked, blocks)
    # A dropped image and a removed import both leave blank lines behind. Keep
    # the single blank line that separated the front matter from the body.
    lead = "\n" if body.startswith("\n") else ""
    masked = lead + re.sub(r"\n{3,}", "\n\n", masked).lstrip("\n")

    new_body = unmask_code(masked, code_blocks)

    if result.citation_entries:
        if front_matter is None:
            raise SystemExit(f"{path}: citations found but the file has no front matter")
        block = render_citations_block(result.citation_entries)
        prefix = f"---\n{front_matter}\n{block}\n{closing}"

    result.text = prefix + new_body
    result.changed = result.text != text
    return result


def collect(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and ".git" not in path.parts
    )


def verify_round_trip(result: FileResult) -> None:
    """The emitted front matter must parse back to the CSL we put in."""
    if not result.citation_entries:
        return
    front_matter, _, _ = split_front_matter(result.text)
    loaded = yaml.safe_load(front_matter or "") or {}
    got = loaded.get("citations")
    if got != result.citation_entries:
        for key, want in result.citation_entries.items():
            if not isinstance(got, dict) or got.get(key) != want:
                raise SystemExit(
                    f"{result.path}: citations front matter did not round-trip for "
                    f"{key!r}\n  wrote: {want!r}\n  read:  "
                    f"{(got or {}).get(key)!r}"
                )
        raise SystemExit(f"{result.path}: citations front matter did not round-trip")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="content repo clone to convert in place")
    parser.add_argument("--check", action="store_true", help="report, write nothing")
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    if not (root / "README.md").is_file():
        return int(bool(sys.stderr.write(f"Not a content checkout: {root}\n")))
    branch = (root / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    if branch.endswith("refs/heads/main") or branch.endswith("refs/heads/master"):
        sys.stderr.write(
            f"Refusing to run on {branch.rsplit('/', 1)[-1]}: the live Gatsby site "
            "builds from it. Check out a branch first.\n"
        )
        return 2

    images = ImageIndex.build(root)
    results = [convert_text(p.read_text(encoding="utf-8"), p, images) for p in collect(root)]
    for result in results:
        verify_round_trip(result)
        if result.changed and not args.check:
            result.path.write_text(result.text, encoding="utf-8")

    changed = [r for r in results if r.changed]
    print(f"files scanned {len(results)}, rewritten {len(changed)}")
    print(f"  ::image{{}}        {sum(r.images for r in results)}")
    print(f"  [@key]           {sum(r.citations for r in results)}")
    print(f"  ::citations{{}}    {sum(r.citation_lists for r in results)}")
    print(f"  citation entries {sum(len(r.citation_entries) for r in results)}")
    for label, rows in (
        ("BlogImage dropped (no such file)", [(r.path, n) for r in results for n in r.images_dropped]),
        ("basename matched >1 file", [(r.path, m) for r in results for m in r.multi_match]),
        ("image was mid-paragraph", [(r.path, n) for r in results for n in r.inline_images]),
        ("same CSL cited more than once", [(r.path, t) for r in results for t in r.repeated_uses]),
        ("key needed a numeric suffix", [(r.path, k) for r in results for k in r.numeric_keys]),
    ):
        if rows:
            print(f"\n{label} ({len(rows)}):")
            for path, detail in rows:
                print(f"  {Path(path).name}: {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
