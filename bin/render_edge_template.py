#!/usr/bin/env python3
"""Write the CloudFormation template of the edge stack.

The viewer-request function is Papyrus core's shared redirect and index function with the rules of
``web/projection.json`` (``redirects.patterns`` and ``urls.style``) compiled in by
``papyrus-infra compile-edge-function``; the viewer-response function is ``infra/edge/viewer-response.js``.

Usage: render_edge_template.py OUT_YAML
"""

import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
EDGE_DIRECTORY = REPOSITORY / "infra" / "edge"
PAPYRUS_INFRA = REPOSITORY / "node_modules" / "@anthusai" / "papyrus" / "bin" / "papyrus-infra.mjs"
INDENT = " " * 8


def indented_text(text):
    lines = text.rstrip("\n").split("\n")
    return "\n".join(INDENT + line if line else "" for line in lines)


def indented(path):
    return indented_text(path.read_text(encoding="utf-8"))


def compiled_viewer_request():
    return subprocess.run(
        ["node", str(PAPYRUS_INFRA), "compile-edge-function", "--static-dir", str(REPOSITORY / "web")],
        check=True, capture_output=True, text=True,
    ).stdout


def main():
    template = (EDGE_DIRECTORY / "anth-us-s3.template.yaml").read_text(encoding="utf-8")
    template = template.replace("{{VIEWER_REQUEST}}", indented_text(compiled_viewer_request()))
    template = template.replace("{{VIEWER_RESPONSE}}", indented(EDGE_DIRECTORY / "viewer-response.js"))
    Path(sys.argv[1]).write_text(template, encoding="utf-8")


if __name__ == "__main__":
    main()
