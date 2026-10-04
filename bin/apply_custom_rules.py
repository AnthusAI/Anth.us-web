#!/usr/bin/env python3
"""Apply the generated Amplify ``customRules`` to the staging app.

Amplify Hosting's redirects are **app configuration**, not a repo file: there
is no ``amplify.yml`` key and no ``_redirects``-style artifact for a ``WEB``
app, so the rules `web/build_via_papyrus.py` generates into
``web/custom-rules.json`` have to be pushed with ``amplify update-app``. This
script is that step, kept in the repo so the rules are reproducible rather than
hand-edited in the console.

Usage:
    AWS_PROFILE=legacy python3 bin/apply_custom_rules.py            # dry run
    AWS_PROFILE=legacy python3 bin/apply_custom_rules.py --apply

STAGING ONLY. ``APP_ID`` is pinned to the staging app and checked against the
app's name before anything is written, because the same account holds the two
production Anth.us apps (``AMPLIFY_APP_ID``, ``AMPLIFY_APP_ID``) and an
``update-app`` against either of those would reconfigure the live site.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = REPO_ROOT / "web" / "custom-rules.json"

#: The staging app, and the name it must report. Both are checked: an app id
#: can be mistyped, and a name-only check could match a renamed app.
APP_ID = "AMPLIFY_APP_ID"
APP_NAME = "anthus-papyrus-staging"
REGION = "us-east-1"


def aws(*args: str) -> str:
    result = subprocess.run(
        ["aws", "amplify", *args, "--region", REGION],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"aws amplify {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the rules; without it, only the diff is printed",
    )
    args = parser.parse_args()

    if not RULES_FILE.is_file():
        sys.exit(f"{RULES_FILE} not found. Run web/build_via_papyrus.py first.")
    desired = json.loads(RULES_FILE.read_text(encoding="utf-8"))

    app = json.loads(aws("get-app", "--app-id", APP_ID))["app"]
    if app["name"] != APP_NAME:
        sys.exit(
            f"refusing to write: app {APP_ID} is named {app['name']!r}, "
            f"expected {APP_NAME!r}. This script is staging-only."
        )
    if app.get("customDomains") or app.get("domains"):
        sys.exit(f"refusing to write: app {APP_ID} has a custom domain attached.")

    current = app.get("customRules") or []
    print(f"app {APP_ID} ({app['name']}) at {app['defaultDomain']}")
    print(f"  current rules: {len(current)}")
    print(f"  desired rules: {len(desired)}")
    if current == desired:
        print("  already up to date")
        return 0

    current_sources = {rule["source"] for rule in current}
    desired_sources = {rule["source"] for rule in desired}
    for source in sorted(desired_sources - current_sources):
        print(f"  + {source}")
    for source in sorted(current_sources - desired_sources):
        print(f"  - {source}")

    if not args.apply:
        print("\ndry run; re-run with --apply to write these rules")
        return 0

    aws(
        "update-app",
        "--app-id",
        APP_ID,
        "--custom-rules",
        f"file://{RULES_FILE}",
    )
    written = json.loads(aws("get-app", "--app-id", APP_ID))["app"]["customRules"]
    if written != desired:
        sys.exit(f"wrote {len(desired)} rules but the app reports {len(written)}")
    print(f"\napplied {len(written)} rules to {APP_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
