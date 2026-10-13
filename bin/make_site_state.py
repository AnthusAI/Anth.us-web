"""Write the static image state the Anth.us projector needs, from a Papyrus export (deploy time).

Usage: make_site_state.py EXPORT_DIR CONTENT_ROOT OUT_JSON
CONTENT_ROOT is the root `cms_content_root.materialize_content_root` builds from the export.
"""

import json
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
sys.path.insert(0, str(WEB_DIR))

from PIL import Image, ImageOps  # noqa: E402

from anthus_content import ImageIndex  # noqa: E402
from papyrus_content.markus_renderer.images import _svg_dimensions, image_has_alpha  # noqa: E402

content_root = Path(sys.argv[2]).resolve()
out_path = Path(sys.argv[3])
site_assets = WEB_DIR / "assets" / "site"
index = ImageIndex.build(content_root, site_assets)

dimensions = {}
gatsby = {}
passthrough = {}
for relative, path in index.by_relpath.items():
    try:
        with Image.open(path) as opened:
            dimensions["/assets/content/" + relative] = list(opened.size)
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".avif"}:
                upright = ImageOps.exif_transpose(opened)
                upright.load()
                gatsby[relative] = {"size": list(upright.size), "alpha": image_has_alpha(upright)}
    except Exception:
        pass
    if relative not in gatsby:
        size = _svg_dimensions(path) if path.suffix.lower() == ".svg" else None
        raster = dimensions.get("/assets/content/" + relative)
        passthrough[relative] = list(size) if size else raster
for path in index.site_by_name.values():
    with Image.open(path) as opened:
        dimensions["/assets/site/" + path.relative_to(site_assets).as_posix()] = list(opened.size)

state = {
    "images": {
        "by_relpath": sorted(index.by_relpath),
        "by_basename": {name: path.relative_to(content_root).as_posix() for name, path in index.by_basename.items()},
        "site_by_name": {name: path.relative_to(site_assets).as_posix() for name, path in index.site_by_name.items()},
    },
    "dimensions": dimensions,
    "gatsby": gatsby,
    "passthrough": passthrough,
}
out_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
print(len(gatsby), "images", out_path.stat().st_size, "bytes")
