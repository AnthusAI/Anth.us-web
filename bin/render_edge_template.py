#!/usr/bin/env python3
"""Write the CloudFormation template of the edge stack with the functions of infra/edge inlined.

Usage: render_edge_template.py OUT_YAML
"""

import sys
from pathlib import Path

EDGE_DIRECTORY = Path(__file__).resolve().parent.parent / "infra" / "edge"
INDENT = " " * 8


def indented(path):
    lines = path.read_text(encoding="utf-8").rstrip("\n").split("\n")
    return "\n".join(INDENT + line if line else "" for line in lines)


def main():
    template = (EDGE_DIRECTORY / "anth-us-s3.template.yaml").read_text(encoding="utf-8")
    template = template.replace("{{VIEWER_REQUEST}}", indented(EDGE_DIRECTORY / "viewer-request.js"))
    template = template.replace("{{VIEWER_RESPONSE}}", indented(EDGE_DIRECTORY / "viewer-response.js"))
    Path(sys.argv[1]).write_text(template, encoding="utf-8")


if __name__ == "__main__":
    main()
