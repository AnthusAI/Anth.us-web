"""Solution marks: each in-house solution's own logo, ported as a static inline SVG string.

Sources (read-only, ported faithfully; animation is CSS in css/arcade.css, "Solution marks"):

* Cyclotron: the "cycle mark" (``RefreshCwWide``, 42 x 24, 2px round stroke) from the cyclotron package's
  ``trace-ui/src/components/ui/cycle-mark.tsx`` / ``refresh-cw-wide.tsx``. It adapts through ``currentColor``.
* Chatticus: the bot avatar mark from ``Chattic.us-web/public/favicon.svg`` / ``components/Wordmark.tsx``
  (``anthus-vultus`` ``BotAvatar``, neutral state). Brand clay body and paper eyes stay fixed; the shadow bubble
  flips with the light/dark pair the Chatticus site itself uses (see ``.sm-chat-shadow`` in arcade.css).
* Papyrus: the papyrus plant from ``p.apyr.us-cut2/public/papyrus-plant.png`` (the p.apyr.us header mark),
  traced to a single vector path; filled with ``currentColor``.
* Primus: the Primus logo, a grid of cells drifting through the brand gradient with the pixel-font P over it
  (``Primus/dashboard/components/logo-square.tsx``, narrow 2 x 2 variant). Gradient colors are the brand's own.

Every mark is ``aria-hidden`` by default because the card title names the solution; pass ``label=True`` for a
standalone ``role="img"`` mark.
"""

from __future__ import annotations

#: Cyclotron: the racetrack loop the animation rides, and the logo pose (the four RefreshCwWide strokes).
_CYCLOTRON_LOOP = (
    "M3 12a9 9 0 0 1 9-9h18a9.75 9.75 0 0 1 6.74 2.74L39 8V12a9 9 0 0 1-9 9H12"
    "a9.75 9.75 0 0 1-6.74-2.74L3 16Z"
)
_CYCLOTRON_STATIC = (
    '<path d="M3 12a9 9 0 0 1 9-9h18a9.75 9.75 0 0 1 6.74 2.74L39 8"/>'
    '<path d="M39 3v5h-5"/>'
    '<path d="M39 12a9 9 0 0 1-9 9H12a9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
    '<path d="M8 16H3v5"/>'
)
#: One arrow (a dashed run along the loop plus its riding arrowhead); arrow 2 is arrow 1 turned half a turn.
_CYCLOTRON_ARROW = (
    f'<path class="sm-cyc-run" d="{_CYCLOTRON_LOOP}"/>'
    '<path class="sm-cyc-head" d="M-3.536 -3.536L0 0L-3.536 3.536"/>'
)

_PAPYRUS_PLANT = (
    "M149.8 0.5 151.1 13.0 152.7 45.5 153.5 119.0 160.4 81.5 164.4 65.5 168.9 50.5 174.9 35.0 180.4 23.0 187.4 10.5 189.8 6.5 190.5 5.7 190.8 6.0 179.4 37.5 171.9 63.5 164.9 95.5 160.5 124.1 166.9 105.0 172.9 89.5 178.3 77.5 186.4 62.5 194.3 50.0 203.9 37.0 213.9 26.0 222.0 18.3 222.5 18.5 204.4 44.5 196.9 57.0 190.5 69.0 184.9 80.5 176.4 100.5 169.9 118.5 166.9 127.5 167.0 128.5 174.8 113.5 184.9 97.0 195.8 82.0 204.4 72.0 214.0 62.3 227.0 51.4 238.5 43.3 249.7 37.0 223.6 61.0 212.8 72.5 204.4 82.5 196.8 92.5 186.9 107.5 176.4 126.0 172.9 132.5 173.0 133.4 181.9 121.5 191.4 110.5 205.3 97.0 217.0 87.3 229.5 78.9 245.0 70.3 260.5 63.9 270.0 60.9 271.5 61.0 254.0 70.4 242.5 77.4 229.5 86.4 218.5 94.9 207.7 104.5 196.3 116.0 186.4 127.5 178.9 137.0 178.2 138.0 178.5 138.3 190.0 127.9 205.0 116.4 219.5 107.4 231.5 101.4 246.5 95.4 259.0 91.9 276.0 88.9 287.7 88.5 268.0 93.8 259.0 96.9 243.0 103.4 231.5 109.0 218.5 116.4 204.5 125.8 192.5 135.3 183.0 143.9 182.5 144.9 200.0 134.5 215.0 127.4 226.0 123.3 238.5 119.8 254.0 116.9 267.0 115.8 285.0 116.4 296.0 117.9 297.1 118.5 280.0 119.4 266.0 120.9 249.5 123.9 236.0 127.4 222.0 132.4 208.5 138.3 198.0 143.9 183.0 153.7 197.0 147.8 211.5 143.3 226.0 140.4 240.5 138.9 255.5 138.9 272.5 140.9 287.5 144.4 295.0 146.9 299.4 149.0 277.5 145.8 258.0 144.9 238.0 145.9 219.5 148.9 199.0 154.9 182.0 162.3 166.5 171.4 158.0 177.9 154.8 181.5 154.3 183.0 154.2 191.5 154.1 305.0 154.5 307.9 157.3 289.0 161.4 269.5 166.4 251.0 172.9 232.0 179.4 216.5 187.8 199.5 197.3 183.5 205.9 171.0 206.7 170.5 196.4 192.5 186.0 218.5 177.4 245.0 170.9 271.0 166.3 297.0 163.3 323.5 162.4 342.0 162.3 358.0 162.7 363.5 163.9 366.0 167.5 371.3 178.5 366.4 187.0 363.4 198.0 360.4 211.0 357.9 219.5 356.9 234.0 356.2 245.5 356.4 255.9 357.5 249.5 365.3 229.0 364.9 209.5 366.8 199.0 368.9 188.5 371.9 173.5 378.0 173.2 378.5 180.5 385.7 195.5 380.4 208.5 377.4 226.5 375.4 238.7 375.5 228.5 384.0 221.5 384.4 210.0 385.9 197.0 388.9 188.0 391.8 190.5 394.1 200.0 400.5 199.5 401.1 190.5 404.6 179.5 396.6 172.7 390.5 165.5 382.8 164.5 382.9 157.0 388.0 156.9 388.5 166.7 399.0 172.9 408.5 172.5 409.1 164.5 410.3 156.7 400.5 150.0 393.7 142.9 400.5 135.5 410.1 126.9 409.0 126.8 408.5 128.9 405.0 133.5 398.5 142.7 388.5 142.5 387.9 134.5 382.6 120.5 396.2 109.5 404.5 100.0 401.1 99.6 400.5 110.5 393.1 111.8 392.0 111.5 391.7 102.5 388.9 91.5 386.3 82.5 384.9 71.0 383.9 66.0 380.2 61.0 375.4 73.5 375.4 91.0 377.4 104.0 380.4 119.0 385.6 124.6 380.5 126.4 378.5 126.1 378.0 116.5 373.8 108.0 370.8 90.5 366.8 70.5 364.9 50.0 365.2 43.6 357.5 53.5 356.4 65.0 356.1 75.0 356.4 88.5 357.9 99.5 359.9 111.0 362.8 122.5 366.9 132.0 371.3 135.2 367.0 137.2 363.0 136.2 351.5 132.6 335.5 127.6 319.5 122.1 306.0 114.6 291.0 106.2 277.0 96.2 263.0 96.5 262.7 103.0 268.4 111.6 277.0 118.6 285.5 125.6 295.5 131.1 305.0 136.1 315.5 140.6 327.0 144.7 340.0 145.4 326.5 145.4 200.5 145.3 184.5 144.6 181.5 140.9 177.5 133.0 171.4 116.0 161.5 99.0 154.3 80.0 148.9 60.5 145.8 39.5 144.9 22.5 145.8 0.0 149.0 12.0 144.4 27.0 140.9 43.5 138.9 59.5 138.9 73.5 140.4 88.0 143.4 102.5 147.8 116.3 153.5 104.0 145.4 91.0 138.3 77.5 132.3 63.5 127.4 50.0 123.9 33.0 120.8 19.0 119.4 2.5 118.5 4.0 117.8 14.5 116.4 32.5 115.8 45.5 116.8 59.0 119.4 72.0 122.9 87.0 128.4 102.0 135.8 117.0 144.8 106.5 134.9 95.0 125.8 83.5 117.8 71.5 110.8 59.0 104.4 44.5 98.4 31.5 93.9 12.0 88.3 23.5 88.9 40.5 91.9 54.5 96.0 69.0 101.8 81.0 107.9 96.0 117.4 111.5 129.4 121.5 138.7 113.6 128.0 103.8 116.5 93.4 106.0 80.5 94.4 58.5 78.4 44.5 69.9 28.2 61.0 29.5 60.9 39.0 63.9 54.5 70.4 70.0 78.9 82.0 86.9 93.0 95.8 106.8 109.0 118.1 122.0 127.0 133.9 121.1 122.0 111.1 105.0 104.2 94.5 95.2 82.5 85.1 70.5 76.6 61.5 49.9 37.0 59.5 42.4 71.5 50.4 84.7 61.5 95.5 72.1 106.6 85.5 114.7 97.0 123.1 110.5 132.5 128.2 132.7 127.0 130.7 121.0 122.1 97.5 116.7 84.5 109.7 70.0 95.6 45.0 77.2 18.5 77.5 18.2 86.3 26.5 96.2 37.5 106.1 51.0 113.7 63.0 121.1 77.0 127.6 91.5 132.6 104.5 139.0 124.1 139.2 122.5 135.1 97.5 128.6 66.5 119.1 34.0 108.8 6.0 109.0 5.7 110.1 7.0 114.1 13.5 122.1 29.0 128.6 44.5 132.7 56.5 140.1 85.0 146.0 119.5 146.9 47.0 148.4 15.0ZM150.0 355.8 145.7 366.0 140.1 375.5 150.0 382.6 159.7 375.5 154.0 366.0Z"
)

#: Primus pixel-font P over a 2 x 2 grid, in a 40 x 40 box.
_PRIMUS_P = "M12 8h13v3h3v9h-3v3h-8v9h-5zM17 13v7h6v-7z"

#: viewBox, extra svg class, inner markup. Chatticus paths are the favicon's, scaled into a 28 x 28 box.
_MARKS: dict[str, tuple[str, str, str]] = {
    "Cyclotron": (
        "0 0 42 24", "sm--cyclotron",
        f'<g class="sm-cyc-static" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{_CYCLOTRON_STATIC}</g>'
        '<g class="sm-cyc-live" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{_CYCLOTRON_ARROW}<g transform="rotate(180 21 12)">{_CYCLOTRON_ARROW}</g></g>',
    ),
    "Chatticus": (
        "0 0 28 28", "sm--chatticus",
        '<path class="sm-chat-shadow" d="M16 4L20 4A8 8 0 0 1 28 12L28 18.15A1.85 1.85 0 0 1 26.15 20L16 20'
        'A8 8 0 0 1 8 12L8 12A8 8 0 0 1 16 4Z"/>'
        '<path class="sm-chat-body" d="M8 8L12 8A8 8 0 0 1 20 16L20 16A8 8 0 0 1 12 24L1.85 24'
        'A1.85 1.85 0 0 1 0 22.15L0 16A8 8 0 0 1 8 8Z"/>'
        '<g class="sm-chat-eyes"><g class="sm-chat-lids">'
        '<circle cx="10" cy="14" r="2"/><circle cx="18" cy="14" r="2"/></g></g>',
    ),
    "Papyrus": (
        "0 0 300 411", "sm--papyrus",
        f'<path fill="currentColor" fill-rule="evenodd" d="{_PAPYRUS_PLANT}"/>',
    ),
    "Primus": (
        "0 0 40 40", "sm--primus",
        '<rect class="sm-pri-cell sm-pri-c1" x="0" y="0" width="20" height="20"/>'
        '<rect class="sm-pri-cell sm-pri-c2" x="20" y="0" width="20" height="20"/>'
        '<rect class="sm-pri-cell sm-pri-c3" x="0" y="20" width="20" height="20"/>'
        '<rect class="sm-pri-cell sm-pri-c4" x="20" y="20" width="20" height="20"/>'
        f'<path class="sm-pri-p" d="{_PRIMUS_P}"/>',
    ),
}


def mark(name: str, *, label: bool = False) -> str:
    """The inline SVG for solution ``name`` ("" for a solution without a mark)."""
    if name not in _MARKS:
        return ""
    viewbox, cls, inner = _MARKS[name]
    a11y = f'role="img" aria-label="{name} logo"' if label else 'aria-hidden="true" focusable="false"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="sm {cls}" viewBox="{viewbox}" {a11y}>{inner}</svg>'
    )
