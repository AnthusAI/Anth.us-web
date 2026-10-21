#!/usr/bin/env python3
"""Serve a local projection of anth.us (the folder `bin/project_export_locally.py` writes) the way CloudFront does.

    python3 bin/dev-server.py OUT --port 8080

A directory URL serves its index.html; a missing path answers 404 with the 404.html body. The redirects (the key-value
store and the pattern rules) are not simulated: `bin/parity.py` does that. `/css/site-theme.css`, `/assets/*.js` and
`/assets/site/*` are read from `web/` on every request, so an edit to the stylesheet or a chrome script shows on reload.

Nothing bound inside a Claude Code cloud container is reachable from a browser: run this on a local machine.
"""

from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
LIVE = {"/css/site-theme.css": WEB / "css" / "site-theme.css"}


class Handler(SimpleHTTPRequestHandler):
    out: Path

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean in LIVE:
            return str(LIVE[clean])
        for prefix in ("/assets/site/", "/assets/"):
            candidate = WEB / clean.lstrip("/")
            if clean.startswith(prefix) and candidate.is_file():
                return str(candidate)
        return super().translate_path(path)

    def send_error(self, code, message=None, explain=None):
        page = self.out / "404.html"
        if code == 404 and page.is_file():
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path, help="the projection folder")
    parser.add_argument("--port", type=int, default=8080)
    arguments = parser.parse_args()
    if not (arguments.out / "index.html").is_file():
        print(f"{arguments.out} has no index.html: project the site first", file=sys.stderr)
        return 1
    Handler.out = arguments.out.resolve()
    handler = lambda *args, **kwargs: Handler(*args, directory=str(Handler.out), **kwargs)  # noqa: E731
    with ThreadingHTTPServer(("127.0.0.1", arguments.port), handler) as server:
        print(f"http://127.0.0.1:{arguments.port}/  (serving {Handler.out})")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
