"""Environment of the Python tests: the web modules read these before they are imported."""
import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
WEB = REPOSITORY / "web"

os.environ["PAPYRUS_SITE_STATIC_DIR"] = str(WEB)
if "ANTHUS_BUILD_DIR" not in os.environ:  # projections are written here (20 MB of assets each); removed at exit
    os.environ["ANTHUS_BUILD_DIR"] = tempfile.mkdtemp(prefix="anthus-tests-build-")
    atexit.register(shutil.rmtree, os.environ["ANTHUS_BUILD_DIR"], ignore_errors=True)
for name in ("PAPYRUS_SITE_ENV", "PAPYRUS_SITE_PUBLIC_URL"):
    os.environ.pop(name, None)  # every projection sets its own environment (tests/support.py)
for path in (str(WEB), str(REPOSITORY)):
    if path not in sys.path:
        sys.path.insert(0, path)
