#!/usr/bin/env python3
"""Assert a deployed site returns a REAL 404 (custom page body, HTTP 404, no
redirect) for a missing path, and 200 for a known page. Read-only GETs.

    python3 bin/check-404.py https://staging.AMPLIFY_APP_ID.amplifyapp.com [/known/page/]
"""
import sys
import urllib.error
import urllib.request
import uuid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def get(url):
    try:
        with OPENER.open(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    base = argv[0].rstrip("/")
    known = argv[1] if len(argv) > 1 else "/"
    _, page = get(base + "/404.html")
    missing = f"/missing-{uuid.uuid4().hex[:8]}/"
    ok = True
    for path, want in ((known, 200), (missing, 404)):
        code, body = get(base + path)
        good = code == want and (want != 404 or bool(page and body == page))
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {path} -> {code} (want {want}"
              + (", custom 404 body" if want == 404 else "") + ")")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
