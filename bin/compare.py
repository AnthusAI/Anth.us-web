#!/usr/bin/env python3
"""compare.py -- diff two directories of shoot.cjs output.

Pairs up every ``<name>@<width>.png`` / ``<name>@<width>.json`` that exists in
BOTH directories and reports how far apart they are, both pixel-wise and
structurally (CSS class names, document height).

USAGE
    python3 bin/compare.py /tmp/shots/old /tmp/shots/new
    python3 bin/compare.py OLD NEW --diff-out /tmp/shots/diff --threshold 16

PIXEL METRICS
    mean abs diff   mean |old - new| across all R, G and B samples, 0-255.
                    0 means byte-identical, higher means more different.
    pct > T         percentage of pixels that differ by more than --threshold
                    (default 16) in *any* single channel. This ignores
                    imperceptible antialiasing noise and highlights real
                    layout / colour changes.

    Images of unequal height are bottom-padded with white up to the taller
    height (and right-padded to the wider width) before comparing, so a page
    that merely grew longer only shows a diff in the region that changed.

ARTEFACTS (written to --diff-out, default /tmp/shots/diff)
    <name>@<width>.side.png   old | new side by side, with a divider
    <name>@<width>.diff.png   heatmap: black = identical, blue -> yellow ->
                              red = increasingly different

STRUCTURAL METRICS (from the .json fingerprints)
    classes only in OLD / only in NEW (sorted), docHeight delta, plus any
    change to title or HTTP status.

REQUIREMENTS
    Python 3 stdlib, plus Pillow for the pixel half. If Pillow is missing the
    script says so and still performs the complete JSON/class-name diff.

EXIT CODE
    0  comparison completed (even if differences were found)
    1  no comparable pairs, bad arguments, or unreadable inputs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional Pillow
# ---------------------------------------------------------------------------

try:
    from PIL import Image, ImageChops, ImageDraw, ImageStat

    HAVE_PILLOW = True
    PILLOW_ERROR = ""
except Exception as exc:  # pragma: no cover - depends on environment
    HAVE_PILLOW = False
    PILLOW_ERROR = str(exc)

SHOT_RE = re.compile(r"^(?P<name>.+)@(?P<width>\d+)\.(?P<ext>png|json)$")
WHITE = (255, 255, 255)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def index_dir(path: str) -> Dict[str, Dict[str, str]]:
    """Return {"<name>@<width>": {"png": abspath, "json": abspath}}."""
    out: Dict[str, Dict[str, str]] = {}
    for entry in sorted(os.listdir(path)):
        match = SHOT_RE.match(entry)
        if not match:
            continue
        key = "%s@%s" % (match.group("name"), match.group("width"))
        out.setdefault(key, {})[match.group("ext")] = os.path.join(path, entry)
    return out


def sort_key(key: str) -> Tuple[str, int]:
    name, _, width = key.rpartition("@")
    try:
        return (name, int(width))
    except ValueError:
        return (key, 0)


# ---------------------------------------------------------------------------
# Pixel comparison
# ---------------------------------------------------------------------------

def pad_to(img, size: Tuple[int, int]):
    """Return img placed top-left on a white canvas of exactly ``size``."""
    if img.size == size:
        return img
    canvas = Image.new("RGB", size, WHITE)
    canvas.paste(img, (0, 0))
    return canvas


def max_channel(diff):
    """Collapse an RGB difference image to per-pixel max channel difference."""
    r, g, b = diff.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b)


def heatmap_lut() -> List[int]:
    """256*3 lookup table: black -> blue -> cyan -> yellow -> red.

    Small differences are amplified so that a 1/255 change is still visible.
    """
    stops = [
        (0, (0, 0, 0)),
        (1, (0, 0, 110)),
        (8, (0, 90, 220)),
        (24, (0, 220, 220)),
        (64, (255, 230, 0)),
        (128, (255, 120, 0)),
        (255, (255, 0, 0)),
    ]
    reds: List[int] = []
    greens: List[int] = []
    blues: List[int] = []
    for value in range(256):
        lo, hi = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= value <= stops[i + 1][0]:
                lo, hi = stops[i], stops[i + 1]
                break
        span = hi[0] - lo[0]
        t = 0.0 if span == 0 else (value - lo[0]) / span
        reds.append(int(round(lo[1][0] + t * (hi[1][0] - lo[1][0]))))
        greens.append(int(round(lo[1][1] + t * (hi[1][1] - lo[1][1]))))
        blues.append(int(round(lo[1][2] + t * (hi[1][2] - lo[1][2]))))
    return reds + greens + blues


_HEAT_LUT = heatmap_lut() if HAVE_PILLOW else None


def write_side_by_side(old_img, new_img, dest: str) -> None:
    gap = 16
    width = old_img.width + gap + new_img.width
    height = max(old_img.height, new_img.height)
    canvas = Image.new("RGB", (width, height), WHITE)
    canvas.paste(old_img, (0, 0))
    canvas.paste(new_img, (old_img.width + gap, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([old_img.width, 0, old_img.width + gap - 1, height], fill=(255, 0, 255))
    canvas.save(dest)


def write_heatmap(gray, dest: str) -> None:
    canvas = gray.convert("RGB").point(_HEAT_LUT)
    canvas.save(dest)


def compare_images(old_path: str, new_path: str, diff_out: str, key: str, threshold: int) -> dict:
    old_raw = Image.open(old_path)
    new_raw = Image.open(new_path)
    old_size, new_size = old_raw.size, new_raw.size
    old_img = old_raw.convert("RGB")
    new_img = new_raw.convert("RGB")

    # Side-by-side uses the originals, so each is shown at its true size.
    write_side_by_side(old_img, new_img, os.path.join(diff_out, key + ".side.png"))

    common = (max(old_size[0], new_size[0]), max(old_size[1], new_size[1]))
    old_pad = pad_to(old_img, common)
    new_pad = pad_to(new_img, common)

    diff = ImageChops.difference(old_pad, new_pad)
    mean_per_channel = ImageStat.Stat(diff).mean
    mean_abs = sum(mean_per_channel) / len(mean_per_channel)

    gray = max_channel(diff)
    histogram = gray.histogram()
    total = common[0] * common[1]
    over = sum(histogram[threshold + 1:])
    pct_over = 100.0 * over / total if total else 0.0
    max_diff = max((v for v, count in enumerate(histogram) if count), default=0)

    write_heatmap(gray, os.path.join(diff_out, key + ".diff.png"))

    return {
        "old_size": old_size,
        "new_size": new_size,
        "compare_size": common,
        "mean_abs": mean_abs,
        "pct_over": pct_over,
        "max_diff": max_diff,
        "pixels_over": over,
        "total_pixels": total,
    }


# ---------------------------------------------------------------------------
# JSON comparison
# ---------------------------------------------------------------------------

def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def compare_json(old_path: str, new_path: str) -> dict:
    old = read_json(old_path)
    new = read_json(new_path)
    old_classes = set(old.get("classNames") or [])
    new_classes = set(new.get("classNames") or [])
    old_h = old.get("docHeight")
    new_h = new.get("docHeight")
    delta = None
    if isinstance(old_h, (int, float)) and isinstance(new_h, (int, float)):
        delta = new_h - old_h
    return {
        "only_old": sorted(old_classes - new_classes),
        "only_new": sorted(new_classes - old_classes),
        "shared": len(old_classes & new_classes),
        "old_height": old_h,
        "new_height": new_h,
        "height_delta": delta,
        "old_title": old.get("title"),
        "new_title": new.get("title"),
        "old_status": old.get("status"),
        "new_status": new.get("status"),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_class_list(caption: str, items: List[str], limit: int) -> None:
    if not items:
        return
    print("    %s (%d):" % (caption, len(items)))
    shown = items if limit <= 0 else items[:limit]
    for item in shown:
        print("      %s" % item)
    if len(shown) < len(items):
        print("      ... %d more" % (len(items) - len(shown)))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compare.py",
        description="Diff two directories of shoot.cjs screenshots and fingerprints.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("old_dir", help="baseline directory (e.g. /tmp/shots/old)")
    parser.add_argument("new_dir", help="candidate directory (e.g. /tmp/shots/new)")
    parser.add_argument("--diff-out", default="/tmp/shots/diff",
                        help="where composites and heatmaps go (default: /tmp/shots/diff)")
    parser.add_argument("--threshold", type=int, default=16,
                        help="per-channel difference that counts as a changed pixel (default: 16)")
    parser.add_argument("--max-classes", type=int, default=40,
                        help="max class names to list per side, 0 for all (default: 40)")
    parser.add_argument("--no-images", action="store_true",
                        help="skip the pixel comparison entirely (JSON diff only)")
    args = parser.parse_args(argv)

    for label, path in (("old_dir", args.old_dir), ("new_dir", args.new_dir)):
        if not os.path.isdir(path):
            print("error: %s is not a directory: %s" % (label, path))
            return 1

    old_index = index_dir(args.old_dir)
    new_index = index_dir(args.new_dir)
    keys = sorted(set(old_index) & set(new_index), key=sort_key)

    do_images = not args.no_images and HAVE_PILLOW
    print("=" * 78)
    print("OLD : %s  (%d shot keys)" % (args.old_dir, len(old_index)))
    print("NEW : %s  (%d shot keys)" % (args.new_dir, len(new_index)))
    print("PAIRS: %d   threshold: >%d per channel" % (len(keys), args.threshold))
    if args.no_images:
        print("IMAGES: skipped (--no-images); reporting JSON/class-name diff only.")
    elif not HAVE_PILLOW:
        print("IMAGES: SKIPPED -- Pillow (PIL) is not importable: %s" % PILLOW_ERROR)
        print("        Install it with:  python3 -m pip install Pillow")
        print("        Reporting the JSON/class-name diff only.")
    else:
        print("DIFFS: %s" % args.diff_out)
    print("=" * 78)

    only_old = sorted(set(old_index) - set(new_index), key=sort_key)
    only_new = sorted(set(new_index) - set(old_index), key=sort_key)
    if only_old:
        print("Only in OLD: %s" % ", ".join(only_old))
    if only_new:
        print("Only in NEW: %s" % ", ".join(only_new))
    if only_old or only_new:
        print("")

    if not keys:
        print("error: no shot keys are present in both directories; nothing to compare.")
        return 1

    if do_images:
        os.makedirs(args.diff_out, exist_ok=True)

    rows: List[dict] = []
    errors: List[str] = []

    for key in keys:
        print("-" * 78)
        print(key)
        row = {"key": key, "mean_abs": None, "pct_over": None, "height_delta": None,
               "class_delta": None, "note": ""}

        old_files = old_index[key]
        new_files = new_index[key]

        # --- pixels ---------------------------------------------------------
        if "png" in old_files and "png" in new_files:
            if do_images:
                try:
                    img = compare_images(old_files["png"], new_files["png"],
                                         args.diff_out, key, args.threshold)
                    print("  image old : %dx%d  (%s)" % (img["old_size"][0], img["old_size"][1],
                                                         os.path.basename(old_files["png"])))
                    print("  image new : %dx%d  (%s)" % (img["new_size"][0], img["new_size"][1],
                                                         os.path.basename(new_files["png"])))
                    if img["old_size"] != img["new_size"]:
                        print("  padded to : %dx%d (white fill)" % img["compare_size"])
                    print("  mean abs diff : %.4f / 255" % img["mean_abs"])
                    print("  pct pixels >%d : %.4f%%  (%d of %d)" % (
                        args.threshold, img["pct_over"], img["pixels_over"], img["total_pixels"]))
                    print("  max channel diff : %d" % img["max_diff"])
                    row["mean_abs"] = img["mean_abs"]
                    row["pct_over"] = img["pct_over"]
                except Exception as exc:
                    message = "%s: image compare failed: %s" % (key, exc)
                    print("  ! " + message)
                    errors.append(message)
                    row["note"] = "img-error"
            else:
                row["note"] = "img-skipped"
        else:
            print("  (no PNG pair)")
            row["note"] = "no-png"

        # --- fingerprints ---------------------------------------------------
        if "json" in old_files and "json" in new_files:
            try:
                meta = compare_json(old_files["json"], new_files["json"])
                if meta["old_status"] != meta["new_status"]:
                    print("  status : %s -> %s" % (meta["old_status"], meta["new_status"]))
                if meta["old_title"] != meta["new_title"]:
                    print("  title  : %r -> %r" % (meta["old_title"], meta["new_title"]))
                if meta["height_delta"] is None:
                    print("  docHeight : %s -> %s" % (meta["old_height"], meta["new_height"]))
                else:
                    print("  docHeight : %s -> %s  (delta %+d)" % (
                        meta["old_height"], meta["new_height"], meta["height_delta"]))
                print("  classes : %d shared, %d only-old, %d only-new" % (
                    meta["shared"], len(meta["only_old"]), len(meta["only_new"])))
                print_class_list("only in OLD", meta["only_old"], args.max_classes)
                print_class_list("only in NEW", meta["only_new"], args.max_classes)
                row["height_delta"] = meta["height_delta"]
                row["class_delta"] = (len(meta["only_old"]), len(meta["only_new"]))
            except Exception as exc:
                message = "%s: json compare failed: %s" % (key, exc)
                print("  ! " + message)
                errors.append(message)
        else:
            print("  (no JSON pair)")

        rows.append(row)

    # --- summary ------------------------------------------------------------
    def worst_first(row: dict):
        return (-(row["mean_abs"] if row["mean_abs"] is not None else -1.0), sort_key(row["key"]))

    rows.sort(key=worst_first)

    header = "%-30s %12s %12s %10s %12s" % ("SHOT", "MEAN DIFF", "PCT>%d" % args.threshold,
                                            "dHEIGHT", "CLASSES -/+")
    print("")
    print("=" * 78)
    print("SUMMARY (worst mean pixel diff first)")
    print("=" * 78)
    print(header)
    print("-" * len(header))
    for row in rows:
        mean = "n/a" if row["mean_abs"] is None else "%.4f" % row["mean_abs"]
        pct = "n/a" if row["pct_over"] is None else "%.4f%%" % row["pct_over"]
        dh = "n/a" if row["height_delta"] is None else "%+d" % row["height_delta"]
        cd = "n/a" if row["class_delta"] is None else "%d / %d" % row["class_delta"]
        print("%-30s %12s %12s %10s %12s%s" % (
            row["key"][:30], mean, pct, dh, cd,
            ("  [" + row["note"] + "]") if row["note"] else ""))
    print("-" * len(header))

    scored = [r["mean_abs"] for r in rows if r["mean_abs"] is not None]
    if scored:
        print("pairs: %d   worst mean diff: %.4f   avg mean diff: %.4f" % (
            len(scored), max(scored), sum(scored) / len(scored)))
        if max(scored) == 0.0:
            print("verdict: pixel-identical")
        elif max(scored) < 0.1:
            print("verdict: near-identical (worst mean diff < 0.1/255)")
    else:
        print("pairs: %d   (no pixel metrics computed)" % len(rows))
    if errors:
        print("errors: %d" % len(errors))
        for message in errors:
            print("  - %s" % message)
    print("=" * 78)
    return 1 if not keys else 0


if __name__ == "__main__":
    sys.exit(main())
