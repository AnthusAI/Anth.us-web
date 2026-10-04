#!/usr/bin/env python3
"""Local development server for the Anth.us Papyrus/Markus staging site.

Serves the built site from ``web/dist-papyrus``, with live fallbacks so a CSS
or chrome-script edit shows up on reload without a full rebuild:

* ``/css/site-theme.css`` falls back to ``web/css/anthus-theme.css``
* ``/assets/site-nav.js`` and ``/assets/site/*`` fall back to ``web/assets/``

Article HTML still requires a rebuild — the Markdown is normalized from the
content submodule at build time, so there is nothing to serve live:

    PAPYRUS_ROOT=/path/to/Papyrus python3 web/build_via_papyrus.py
    python3 bin/dev-server.py --port 8080

**Do not try to preview from a cloud session.** Nothing bound inside a Claude
Code cloud container is reachable from a browser — no port forwarding, no
preview URL. Run this on a local machine.
"""

from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "web" / "dist-papyrus"
WEB_CSS_DIR = REPO_ROOT / "web" / "css"
WEB_ASSETS_DIR = REPO_ROOT / "web" / "assets"


class AnthusDevHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def end_headers(self) -> None:
        # The build fingerprints CSS and JS URLs with a content hash, so a
        # stale cached copy looks like "my fix did nothing". Disable caching
        # outright in development.
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/css/"):
            rel = clean[len("/css/") :]
            candidate = WEB_CSS_DIR / rel
            if candidate.is_file():
                return str(candidate)
            if rel == "site-theme.css" and (WEB_CSS_DIR / "anthus-theme.css").is_file():
                return str(WEB_CSS_DIR / "anthus-theme.css")
        if clean.startswith("/assets/"):
            candidate = WEB_ASSETS_DIR / clean[len("/assets/") :]
            if candidate.is_file():
                return str(candidate)
        return super().translate_path(path)

    def send_error(self, code, message=None, explain=None):
        # Serve the built 404 page so the staging site behaves like Amplify,
        # which is configured with 404.html as its not-found document.
        if code == 404:
            page = DIST_DIR / "404.html"
            if page.is_file():
                body = page.read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        super().send_error(code, message, explain)


def main() -> int:
    parser = argparse.ArgumentParser(description="Anth.us Papyrus dev server")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind (default: 8080)")
    parser.add_argument("--bind", type=str, default="127.0.0.1", help="Address to bind")
    args = parser.parse_args()

    if not DIST_DIR.is_dir():
        print(f"Error: {DIST_DIR} not found. Build the site first:")
        print("  PAPYRUS_ROOT=/path/to/Papyrus python3 web/build_via_papyrus.py")
        return 1

    # One thread per connection: the single-threaded HTTPServer lets one slow
    # image request block every other page on the site.
    httpd = ThreadingHTTPServer((args.bind, args.port), AnthusDevHandler)
    httpd.daemon_threads = True
    print(f"Anth.us (Papyrus staging) dev server: http://{args.bind}:{args.port}/")
    print(f"Serving from: {DIST_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dev server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
