"""What the source hook does to an item's text before Markus converts it: the arcade heading, the closing call to action,
the pictogram shorthand, and the clean-up of editor leftovers."""

from __future__ import annotations

import re

import arcade_pictograms
from papyrus_content.markus_renderer.transforms import block_sentinel

FRONT_MATTER = re.compile(r"\A---[ \t]*\n(?P<yaml>.*?)\n(?:---|\.\.\.)[ \t]*\n", re.S)
CODE_FENCE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})", re.M)
JSX_COMMENT = re.compile(r"[ \t]*\{/\*.*?\*/\}[ \t]*\n?", re.S)
PICTOGRAM = re.compile(r"^[ \t]*\{\{pictogram ([a-z0-9-]+)\}\}[ \t]*$", re.M)


def split(text: str) -> tuple[str, str]:
    """``(front matter block, body)``; the block keeps its delimiters and is empty when the text has none."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = FRONT_MATTER.match(text)
    return (text[: match.end()], text[match.end():]) if match else ("", text)


def protect_code(text: str) -> tuple[str, list[str]]:
    """Lift fenced code out as opaque tokens, so no rewrite touches a code sample."""
    blocks: list[str] = []
    out: list[str] = []
    fence: tuple[str, int] | None = None
    buf: list[str] = []
    for line in text.split("\n"):
        match = CODE_FENCE.match(line)
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
        blocks.append("\n".join(buf))
        out.append(f"\x00CODE{len(blocks) - 1}\x00")
    return "\n".join(out), blocks


def restore_code(text: str, blocks: list[str]) -> str:
    return re.sub(r"\x00CODE(\d+)\x00", lambda match: blocks[int(match.group(1))], text)


def clean(body: str) -> str:
    """Drop JSX comments, turn ``{{pictogram name}}`` into the animated pictogram, trim trailing blanks."""
    text, blocks = protect_code(body)
    text = JSX_COMMENT.sub("", text)
    text = PICTOGRAM.sub(
        lambda match: "\n\n" + block_sentinel('<div class="body-px">' + arcade_pictograms.render(match.group(1)) + "</div>") + "\n\n",
        text,
    )
    text = restore_code(text, blocks)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
