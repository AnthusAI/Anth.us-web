"""Animated pixel pictograms for the Anth.us arcade design (see DESIGN.md §6).

Public API (stable; page code depends on it):

    render(name: str) -> str
        Returns one self-contained ``<figure class="px" data-px="<name>">``
        string: inline SVG + figcaption with a drawn legend. Raises KeyError
        for an unknown name.

    NAMES: tuple[str, ...]
        Every pictogram name, in display order.

Styling lives in web/css/arcade-pictograms.css; the on-screen toggle is
web/assets/px-live.js.

Animation keyframes are generated from the same track definitions that place
the sprites, so they can never drift apart. After changing a track, run

    python3 web/arcade_pictograms.py --write-css

which rewrites the marked GENERATED block of arcade-pictograms.css.

Every coordinate is an integer on a one-unit pixel grid. Sprites are ASCII
bitmaps merged into rects. Colour only via CSS classes (pk ink, pp pink,
pb blue, pd dim, pg bg cutout) that map to --px-* variables.
"""

from __future__ import annotations

import sys
from pathlib import Path

NAMES: tuple[str, ...] = (
    "hero-loop",
    "knowledge-base",
    "self-aligning",
    "agent-harness",
    "confidence-gate",
    "scorecard",
    "relocate",
    "platform-stack",
    "engagement-path",
    "verdict-meter",
    "leaderboard",
    "timeline",
    "lost-sprite",
)

CSS_BEGIN = "/* BEGIN GENERATED KEYFRAMES */"
CSS_END = "/* END GENERATED KEYFRAMES */"

# --------------------------------------------------------------------------
# bitmaps (rows of '#', 'o' = bg cutout, other chars per palette)
# --------------------------------------------------------------------------
CHECK = ["....#", "...#.", "#.#..", ".#..."]
CROSS = ["#...#", ".#.#.", "..#..", ".#.#.", "#...#"]
QUEST = ["###", "..#", ".#.", "...", ".#."]
PERSON = [
    "..###..", ".#####.", ".#####.", "..###..", ".#####.", "#######",
    "#.###.#", "#.###.#", "..###..", "..#.#..", "..#.#..",
]
ROBOT_C = ["...#...", ".#####.", "##o#o##", "#######", ".#####.", ".#...#."]
ROBOT_L = ["...#...", ".#####.", "#o#o###", "#######", ".#####.", ".#...#."]
ROBOT_R = ["...#...", ".#####.", "###o#o#", "#######", ".#####.", ".#...#."]
RING = ["#####", "#...#", "#...#", "#...#", "#####"]
CROWN = ["#..#..#", "##.#.##", "#######", "#######"]
ARROW_R = ["#..", "##.", "###", "##.", "#.."]
ARROW_D = ["#####", ".###.", "..#.."]
ARROW_U = ["..#..", ".###.", "#####"]
CURSOR = ["#.....", "##....", "###...", "####..", "#####.", "###...", "#.##..", "..##.."]
K0 = ["#######"] * 7
K1 = ["#######"] + ["#.....#"] * 5 + ["#######"]
K2 = ["#######", ".......", "#######", ".......", "#######", ".......", "#######"]
D4 = ["#..#", "#..#", "####", "...#", "...#"]
D0 = ["####", "#..#", "#..#", "#..#", "####"]
FLAGHEAD = ["#####", "####.", "###..", "##..."]


def _n(v) -> str:
    if isinstance(v, float):
        v = round(v, 2)
        if v == int(v):
            v = int(v)
    return str(v)


def R(x, y, w, h, c=None) -> str:
    cl = f' class="p{c}"' if c else ""
    return f'<rect{cl} x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}"/>'


def G(c, *items) -> str:
    return f'<g class="p{c}">' + "".join(items) + "</g>"


def box(x, y, w, h, c, t=1) -> str:
    return G(c, R(x, y, w, t), R(x, y + h - t, w, t), R(x, y + t, t, h - 2 * t),
             R(x + w - t, y + t, t, h - 2 * t))


def bmp(rows, x, y, c="k", s=1, pal=None) -> str:
    groups: dict[str, list[str]] = {}
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            ch = row[i]
            if ch == ".":
                i += 1
                continue
            k = i
            while k < len(row) and row[k] == ch:
                k += 1
            col = c if ch == "#" else (pal or {"o": "g"})[ch]
            groups.setdefault(col, []).append(R(x + i * s, y + j * s, (k - i) * s, s))
            i = k
    return "".join(G(col, *rs) for col, rs in groups.items())


def dashv(x, y0, y1, c, on=2, off=2, w=1) -> str:
    return G(c, *[R(x, y, w, min(on, y1 - y)) for y in range(y0, y1, on + off)])


class Fig:
    def __init__(self, name, abbr, w, h, label, sentence, legend, L=8, t0=0.0, fs=5):
        self.name, self.abbr, self.w, self.h = name, abbr, w, h
        self.label, self.sentence, self.legend = label, sentence, legend
        self.L, self.t0, self.fs = L, t0, fs
        self.parts: list[str] = []
        self.kfs: dict[str, str] = {}
        self.defs = ""

    # -- text -------------------------------------------------------------
    def T(self, x, y, s, fs=None, anchor="start", c="k") -> str:
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        return (f'<text class="px__t p{c}" x="{_n(x)}" y="{_n(y)}" '
                f'font-size="{_n(fs or self.fs)}"{a}>{s}</text>')

    def add(self, *s):
        self.parts.extend(s)

    # -- keyframes --------------------------------------------------------
    def _kf(self, body: str) -> str:
        if body not in self.kfs:
            self.kfs[body] = f"px-{self.abbr}-{len(self.kfs) + 1}"
        return self.kfs[body]

    def A(self, inner, pose=None, mv=None, sc=None, vis=None, hop=4, rep=1, show=True):
        """Wrap ``inner`` in animation groups.

        mv:  [(pct, x, y), ...] stepped translate (hop = unit size of one step)
        sc:  ([(pct, sx, sy, steps), ...], (static_sx, static_sy)) stepped scale
        vis: (initial 0/1, [(pct, 0/1), ...]) hard toggles
        show: static (reduced-motion) visibility
        """
        s = inner
        if vis is not None:
            init, tg = vis
            kf, prev = [(0, init)], init
            for t, v in tg:
                kf += [(t - 0.01, prev), (t, v)]
                prev = v
            kf.append((100, prev))
            body = "".join(f"{_n(t)}%{{opacity:{v}}}" for t, v in kf)
            op = "" if show else ' opacity="0"'
            s = f'<g class="an {self._kf(body)}"{op}>{s}</g>'
        elif not show:
            s = f'<g opacity="0">{s}</g>'
        if sc is not None:
            pts, (ssx, ssy) = sc
            body = ""
            for i, (p, sx, sy, n) in enumerate(pts):
                body += (f"{_n(p)}%{{transform:scale({_n(sx)},{_n(sy)});"
                         f"animation-timing-function:steps({n},end)}}")
            tr = "" if (ssx, ssy) == (1, 1) else f' transform="scale({_n(ssx)} {_n(ssy)})"'
            s = f'<g class="an sx {self._kf(body)}"{tr}>{s}</g>'
        if mv is not None:
            pts = list(mv)
            if pts[0][0] > 0:
                pts.insert(0, (0, pts[0][1], pts[0][2]))
            if pts[-1][0] < 100:
                pts.append((100, pts[-1][1], pts[-1][2]))
            body = ""
            for i, (p, x, y) in enumerate(pts):
                if i + 1 < len(pts):
                    d = max(abs(pts[i + 1][1] - x), abs(pts[i + 1][2] - y))
                    n = max(1, round(d / hop))
                else:
                    n = 1
                body += (f"{_n(p)}%{{transform:translate({_n(x)}px,{_n(y)}px);"
                         f"animation-timing-function:steps({n},end)}}")
            rc = f" r{rep}" if rep > 1 else ""
            tr = f' transform="translate({_n(pose[0])} {_n(pose[1])})"' if pose else ""
            s = f'<g class="an{rc} {self._kf(body)}"{tr}>{s}</g>'
        elif pose is not None and pose != (0, 0):
            s = f'<g transform="translate({_n(pose[0])} {_n(pose[1])})">{s}</g>'
        return s

    # -- output -----------------------------------------------------------
    def css(self) -> str:
        out = [f'.px[data-px="{self.name}"]{{--px-L:{_n(self.L)}s;--px-t0:{_n(self.t0)}s}}']
        for body, nm in self.kfs.items():
            out.append(f".{nm}{{animation-name:{nm}}}@keyframes {nm}{{{body}}}")
        return "\n".join(out)

    def svg(self) -> str:
        d = f"<defs>{self.defs}</defs>" if self.defs else ""
        return (f'<svg class="px__svg" viewBox="0 0 {self.w} {self.h}" role="img" '
                f'aria-label="{self.label}" shape-rendering="crispEdges" focusable="false">'
                f'{d}{"".join(self.parts)}</svg>')

    def figure(self) -> str:
        lg = "".join(f'<li>{_lg_glyph(k)}<span>{t}</span></li>' for k, t in self.legend)
        ul = f'<ul class="px__lg">{lg}</ul>' if lg else ""
        return (f'<figure class="px px--{self.abbr}" data-px="{self.name}">{self.svg()}'
                f'<figcaption class="px__cap">{ul}<p>{self.sentence}</p></figcaption></figure>')


# --------------------------------------------------------------------------
# legend glyphs
# --------------------------------------------------------------------------
_LG = {
    "check": (CHECK, "b"), "cross": (CROSS, "p"), "q": (QUEST, "k"),
    "item": (["#####"] * 5, "b"), "corr": (["###"] * 3, "p"),
    "person": (PERSON, "k"), "robot": (ROBOT_C, "b"), "ring": (RING, "p"),
    "crown": (CROWN, "p"), "block": (["#####"] * 5, "b"),
    "k0": (K0, "b"), "k1": (K1, "b"), "k2": (K2, "b"),
    "rule": (["#######", "#.....#", "#.....#", "#.....#"], "p"),
    "limit": (["#######", "#######", "#######", "#######", "#######"], "p"),
    "layer": (["#######"] * 3, "b"),
    "flag": (["#####", "####.", "###..", "##...", "#...."], "p"),
}


def _lg_glyph(kind: str) -> str:
    rows, c = _LG[kind]
    w, h = max(len(r) for r in rows), len(rows)
    H = max(h, 7)
    inner = bmp(rows, 0, (H - h) // 2, c)
    if kind == "limit":
        inner += bmp(CROSS, 1, 1, "g")
    return (f'<svg class="px__g" viewBox="0 0 {w} {H}" aria-hidden="true" '
            f'shape-rendering="crispEdges" focusable="false">{inner}</svg>')


def _item(glyph=None, c="b"):
    """7x7 item block with an optional bg-coloured glyph."""
    s = R(0, 0, 7, 7, c)
    if glyph == "check":
        s += bmp(CHECK, 1, 2, "g")
    elif glyph == "q":
        s += bmp(QUEST, 2, 1, "g")
    elif glyph == "cross":
        s += bmp(CROSS, 1, 1, "g")
    return s


# --------------------------------------------------------------------------
# the pictograms
# --------------------------------------------------------------------------
def hero_loop() -> Fig:
    f = Fig(
        "hero-loop", "hl", 192, 96,
        "Animated diagram of a self-aligning loop. Three items enter a model one after "
        "another. Two are confident: each carries a check mark and goes straight to the "
        "automatic bin. One is uncertain: it carries a question mark and goes to a human "
        "reviewer, who marks it with a cross. A pink correction then travels back along the "
        "loop to the model, its confidence meter rises from two notches to three, and the "
        "next item goes straight through.",
        "Confident items go straight through. Uncertain ones go to a person, and every "
        "correction travels back to the model.",
        [("check", "Confident: auto"), ("q", "Uncertain: ask a person"),
         ("cross", "Reviewer says no"), ("corr", "Correction")],
        L=8, t0=-4.9, fs=7)
    # tracks
    f.add(G("d", R(0, 32, 48, 3), R(88, 32, 50, 3), R(101, 35, 3, 40), R(101, 73, 25, 3),
            R(66, 83, 81, 3), R(66, 62, 3, 22), R(144, 80, 3, 5)))
    f.add(bmp(ARROW_R, 131, 31, "k"), bmp(ARROW_R, 118, 72, "k"), bmp(ARROW_D, 100, 52, "k"))
    f.add(f.T(2, 25, "ITEMS"))
    # items (drawn before the model so they pass behind it)
    f.add(f.A(_item() + f.A(bmp(CHECK, 1, 2, "g"), vis=(0, [(26, 1)])), (179, 30),
              mv=[(0, -8, 30), (12, 42, 30), (16, 58, 30), (22, 58, 30), (27, 96, 30),
                  (38, 179, 30)]))
    i2 = (_item() + f.A(bmp(QUEST, 2, 1, "g"), vis=(0, [(37, 1), (58, 0)]), show=False)
          + f.A(bmp(CROSS, 1, 1, "g"), vis=(0, [(58, 1)])))
    f.add(f.A(i2, (124, 71), vis=(1, [(66, 0)]),
              mv=[(8, -8, 30), (20, 42, 30), (24, 58, 30), (33, 58, 30), (38, 99, 30),
                  (40, 99, 30), (49, 99, 71), (54, 124, 71)]))
    f.add(f.A(_item() + f.A(bmp(CHECK, 1, 2, "g"), vis=(0, [(86, 1)])), (169, 30),
              mv=[(0, -8, 30), (66, -8, 30), (77, 42, 30), (80, 58, 30), (85, 58, 30),
                  (88, 96, 30), (98, 169, 30)]))
    # model
    f.add(R(48, 16, 40, 42, "p"), R(50, 18, 36, 38, "g"), f.T(68, 30, "MODEL", anchor="middle"),
          f.T(68, 52, "TRUST", anchor="middle"))
    cells = [R(54 + 6 * i, 36, 5, 6) for i in range(5)]
    f.add(G("d", *cells))
    f.add(G("b", cells[0], cells[1]))
    f.add(f.A(G("b", cells[2]), vis=(0, [(82, 1)])))
    f.add(bmp(ARROW_U, 65, 59, "p"), f.T(74, 91, "CORRECTION", c="p"))
    # auto bin
    f.add(G("k", R(138, 26, 52, 2), R(138, 40, 52, 2), R(188, 28, 2, 12)))
    f.add(bmp(CHECK, 150, 19, "b"), f.T(158, 23, "AUTO"))
    # reviewer
    f.add(bmp(PERSON, 140, 68, "k"), f.T(154, 75, "REVIEW"),
          bmp(CHECK, 154, 79, "b"), bmp(CROSS, 164, 79, "p"))
    # correction pixel
    f.add(f.A(R(0, 0, 3, 3, "p"), (66, 62), vis=(0, [(60, 1), (81, 0)]), show=False,
              mv=[(0, 144, 76), (60, 144, 76), (63, 144, 83), (76, 66, 83), (81, 66, 62)]))
    return f


def knowledge_base() -> Fig:
    f = Fig(
        "knowledge-base", "kb", 128, 80,
        "Animated diagram of a knowledge base organising itself. Twelve scattered blocks of "
        "three kinds, striped docs, hollow rules and solid calls, move onto three labelled "
        "shelves of a tree, four on each. A query cursor then travels to one block on the "
        "middle shelf and a check mark confirms it was found.",
        "Scattered material sorts itself into a taxonomy, so a query lands on the right "
        "block.",
        [("k2", "Docs"), ("k0", "Calls"), ("k1", "Rules"), ("check", "Found")],
        L=8, t0=-6.4)
    bases = [24, 44, 64]
    names = ["DOCS", "CALLS", "RULES"]
    kinds = [K2, K0, K1]
    f.add(box(2, 30, 20, 14, "p"), f.T(12, 40, "KB", anchor="middle"))
    f.add(G("d", R(22, 37, 4, 1), R(26, 19, 1, 42)))
    for b, n in zip(bases, names):
        mid = b - 4
        f.add(G("d", R(26, mid, 4, 1), R(56, b, 68, 2)), box(30, mid - 5, 24, 11, "k"),
              f.T(42, mid + 2, n, anchor="middle"))
    scatter = [(70, 6), (110, 12), (96, 30), (60, 14), (118, 34), (64, 52), (84, 8),
               (104, 54), (74, 34), (92, 66), (112, 66), (58, 32)]
    k = 0
    for si, (b, kd) in enumerate(zip(bases, kinds)):
        for slot in range(4):
            tx, ty = 58 + 14 * slot, b - 7
            sx, sy = scatter[k]
            t = 10 + k * 3
            f.add(f.A(bmp(kd, 0, 0, "b"), (tx, ty),
                      mv=[(0, sx, sy), (t, sx, sy), (t + 12, tx, ty)], hop=5))
            k += 1
    f.add(box(2, 66, 38, 11, "k"), f.T(21, 74, "QUERY", anchor="middle"))
    f.add(f.A(bmp(CURSOR, 0, 0, "k"), (89, 41),
              mv=[(0, 34, 70), (58, 34, 70), (66, 118, 60), (72, 100, 48), (76, 89, 41)]))
    # found marker
    f.add(f.A(G("p", R(84, 35, 3, 1), R(84, 35, 1, 3), R(95, 35, 3, 1), R(97, 35, 1, 3),
                R(84, 46, 3, 1), R(84, 44, 1, 3), R(95, 46, 3, 1), R(97, 44, 1, 3))
              + bmp(CHECK, 88, 28, "b"), vis=(0, [(78, 1)])))
    return f


def self_aligning() -> Fig:
    f = Fig(
        "self-aligning", "sa", 128, 80,
        "Animated diagram of a rule being learned. A reviewer marks the first item on the "
        "conveyor with a cross. A pink correction travels to a gate, which becomes a rule. "
        "The next two similar items pass through the rule gate, each marked with a check, "
        "and land in the automatic bin, which holds two items.",
        "A reviewer says no once, and we write down why. After that, the rule handles the "
        "same case.",
        [("cross", "Reviewer says no"), ("rule", "Rule"), ("check", "Handled by rule")],
        L=8, t0=-7.4)
    f.add(G("d", R(0, 32, 100, 3)))
    # ghost arch (before the rule exists) and the real rule arch
    arch = lambda c: G(c, R(68, 20, 22, 3), R(68, 23, 3, 17), R(87, 23, 3, 17))
    f.add(arch("d"))
    f.add(f.A(arch("p") + f.T(79, 16, "RULE", anchor="middle"), vis=(0, [(42, 1)])))
    # bin
    f.add(G("k", R(100, 25, 26, 2), R(100, 39, 26, 2), R(124, 27, 2, 12)))
    f.add(bmp(CHECK, 103, 17, "b"), f.T(110, 22, "AUTO"))
    # reviewer
    f.add(bmp(PERSON, 27, 40, "k"), f.T(30, 62, "REVIEW", anchor="middle"))
    # item 1: stops at reviewer, gets a cross, leaves
    i1 = _item() + f.A(bmp(CROSS, 1, 1, "g"), vis=(0, [(18, 1)]))
    f.add(f.A(i1, (27, 29), vis=(1, [(30, 0)]),
              mv=[(0, -8, 29), (14, 27, 29), (30, 27, 29)]))
    # items 2, 3: pass the rule, get a check, land in the bin
    for st, en, bx, tc in ((36, 74, 115, 54), (52, 94, 107, 70)):
        it = _item() + f.A(bmp(CHECK, 1, 2, "g"), vis=(0, [(tc, 1)]))
        f.add(f.A(it, (bx, 29), mv=[(0, -8, 29), (st, -8, 29), (en, bx, 29)], hop=5))
    f.add(f.A(R(0, 0, 3, 3, "p"), (79, 24), vis=(0, [(30, 1), (42, 0)]), show=False,
              mv=[(0, 33, 47), (30, 33, 47), (36, 79, 47), (42, 79, 24)]))
    return f


def agent_harness() -> Fig:
    f = Fig(
        "agent-harness", "ah", 128, 80,
        "Animated diagram of an agent inside a harness. A small robot walks a three-lane "
        "corridor bounded by walls. It picks up three tool rings, one in each lane, and "
        "reaches a goal flag. At the end of the first lane it meets a pink limit wall marked "
        "with a cross and turns back instead of leaving the bounds.",
        "The harness bounds the agent: it can reach its tools and its goal, and nothing "
        "outside the limit.",
        [("robot", "Agent"), ("ring", "Tool"), ("limit", "Limit"), ("flag", "Goal")],
        L=8, t0=-7.6)
    f.add(f.T(2, 9, "HARNESS"))
    f.add(box(2, 12, 124, 56, "k", 2))
    f.add(G("k", R(4, 30, 92, 2), R(24, 48, 100, 2)))
    f.add(G("p", R(117, 14, 7, 16)), bmp(CROSS, 118, 19, "g"))
    # flag
    f.add(R(114, 52, 1, 12, "k"), bmp(FLAGHEAD, 115, 52, "p"))
    f.add(f.A(bmp(CHECK, 118, 58, "b"), vis=(0, [(91, 1)])))
    # tools + counters
    f.add(f.T(2, 77, "TOOLS"))
    for i, (tx, ty, tt) in enumerate(((56, 20, 15), (60, 38, 48), (64, 56, 81))):
        f.add(f.A(bmp(RING, tx, ty, "p"), vis=(1, [(tt, 0)]), show=False))
        f.add(box(24 + 8 * i, 71, 6, 6, "k"))
        f.add(f.A(R(26 + 8 * i, 73, 2, 2, "p"), vis=(0, [(tt, 1)])))
    # walls drawn; agent last
    f.add(f.A(bmp(ROBOT_C, 0, 0, "b", s=2), (98, 52),
              mv=[(0, 6, 16), (5, 6, 16), (26, 103, 16), (28, 103, 16), (31, 99, 16),
                  (36, 99, 34), (62, 6, 34), (68, 6, 52), (90, 98, 52)]))
    return f


def confidence_gate() -> Fig:
    f = Fig(
        "confidence-gate", "cg", 128, 80,
        "Animated diagram of a confidence threshold. Five items each get a confidence bar. "
        "Three bars reach past the pink threshold line and are marked with a check as "
        "automatic. Two bars fall short and are marked with a question mark to escalate to "
        "a person.",
        "A calibrated model knows when it is unsure: above the bar it decides, below it "
        "asks a person.",
        [("check", "Above the bar: auto"), ("q", "Below: escalate")],
        L=8, t0=-6.0)
    fills = [74, 44, 67, 24, 62]
    TH = 70
    f.add(dashv(TH, 2, 70, "p"))
    f.add(f.T(TH, 77, "THRESHOLD", anchor="middle"))
    for i, fl in enumerate(fills):
        y = 5 + 13 * i
        t = 4 + 10 * i
        ok = 14 + fl >= TH
        f.add(f.A(_item(), (2, y), mv=[(0, -9, y), (t, -9, y), (t + 4, 2, y)], hop=3))
        f.add(R(14, y + 1, 80, 5, "d"))
        f.add(f.A(R(14, y + 1, fl, 5, "b"),
                  sc=([(0, 0, 1, 1), (t + 4, 0, 1, 8), (t + 12, 1, 1, 1)], (1, 1))))
        if ok:
            g = bmp(CHECK, 98, y + 1, "b") + f.T(106, y + 6, "AUTO")
        else:
            g = bmp(QUEST, 98, y + 1, "p") + f.T(106, y + 6, "ESCALATE")
        f.add(f.A(g, vis=(0, [(t + 13, 1)])))
    return f


def scorecard() -> Fig:
    f = Fig(
        "scorecard", "sc", 128, 80,
        "Animated diagram of calls being scored. A scorecard lists six calls, each with a "
        "waveform, scored against four criteria. A scanner moves down the rows and each "
        "cell fills with a check or a cross: twenty cells in all are checks and four are "
        "crosses. The finished card joins a growing pile: hundreds of scorecards, "
        "millions of calls.",
        "Each call gets a scorecard and every criterion a pass or a miss. We run this over "
        "hundreds of scorecards and millions of calls.",
        [("check", "Pass"), ("cross", "Miss")],
        L=8, t0=-3.2)
    grid = ["1111", "1011", "1110", "0111", "1111", "1101"]  # 4 zeros -> 20 checks
    f.add(box(2, 2, 86, 76, "k"))
    f.add(f.T(6, 11, "CALL"), f.T(34, 11, "CRITERIA"))
    heights = [[2, 5, 3, 6, 2], [4, 2, 6, 3, 5], [3, 6, 4, 2, 5], [5, 3, 2, 6, 4],
               [2, 4, 6, 3, 2], [6, 2, 4, 5, 3]]
    for r in range(6):
        y = 15 + 10 * r
        wave = G("b", *[R(6 + 4 * i, y + 4 - h // 2, 2, h) for i, h in enumerate(heights[r])])
        cells = G("d", *[R(34 + 11 * j, y, 9, 8) for j in range(4)])
        for j in range(4):
            cells += (bmp(CHECK, 36 + 11 * j, y + 2, "b") if grid[r][j] == "1"
                      else bmp(CROSS, 36 + 11 * j, y + 1, "p"))
        t1, t2 = 6 + 5 * r, 49 + 5 * r
        f.add(f.A(wave + cells, vis=(0, [(t1, 1), (44, 0), (t2, 1)])))
    # scanner
    f.add(f.A(box(4, 0, 80, 10, "p"), vis=(1, []), show=False,
              mv=[(0, 0, 14), (6, 0, 14), (36, 0, 64), (44, 0, 64), (49, 0, 14), (79, 0, 64),
                  (100, 0, 64)], hop=5))
    # pile
    for i in range(4):
        x, y = 90 + 4 * i, 6 + 4 * i
        c = G("g", R(x, y, 22, 24)) + box(x, y, 22, 24, "k") + G("d", R(x + 3, y + 4, 12, 2),
                                                                R(x + 3, y + 9, 12, 2))
        if i < 2:
            f.add(c)
        else:
            f.add(f.A(c, vis=(0, [(44 + 45 * (i - 2), 1)])))
    f.add(f.T(94, 52, "HUNDREDS", c="p"), f.T(94, 58, "OF CARDS"),
          f.T(94, 68, "MILLIONS", c="b"), f.T(94, 74, "OF CALLS"))
    return f


def relocate() -> Fig:
    f = Fig(
        "relocate", "rl", 128, 80,
        "Animated diagram of a system surviving a failure. Site A, a rack of four blocks, "
        "fails and is marked with a cross. The four blocks hop one by one to Site B, which "
        "is then marked with a check. Throughout, a heartbeat line at the bottom keeps "
        "beating without a gap.",
        "A data center failed and we moved the system within hours. The heartbeat never "
        "stopped.",
        [("cross", "Site down"), ("check", "Still serving")],
        L=8, t0=-7.0)
    f.defs = '<clipPath id="px-rl-c"><rect x="34" y="60" width="90" height="20"/></clipPath>'
    f.add(f.A(box(6, 10, 36, 44, "k", 2), vis=(1, [(16, 0)]), show=False),
          f.A(box(6, 10, 36, 44, "d", 2), vis=(0, [(16, 1)])))
    f.add(f.A(box(86, 10, 36, 44, "d", 2), vis=(1, [(20, 0)]), show=False),
          f.A(box(86, 10, 36, 44, "k", 2), vis=(0, [(20, 1)])))
    f.add(f.T(22, 7, "SITE A", anchor="middle"), f.T(104, 7, "SITE B", anchor="middle"))
    f.add(f.A(bmp(CROSS, 33, 2, "p"), vis=(0, [(16, 1)])))
    f.add(f.A(bmp(CHECK, 114, 3, "b"), vis=(0, [(56, 1)])))
    for c in range(3):
        f.add(bmp(ARROW_R, 52 + 9 * c, 29, "d"))
    for i in range(4):
        y = 14 + 10 * i
        t = 22 + 7 * i
        f.add(f.A(R(0, 0, 28, 7, "b"), (90, y),
                  mv=[(0, 10, y), (t, 10, y), (t + 6, 50, y - 8), (t + 12, 90, y)], hop=5))
    f.add(f.T(2, 72, "UPTIME"), bmp(CHECK, 22, 68, "b"))
    ecg = G("p", R(0, 70, 7, 1), R(7, 69, 2, 1), R(9, 70, 3, 1), R(12, 62, 1, 9),
            R(13, 70, 1, 7), R(14, 70, 10, 1))
    tiles = "".join(f'<g transform="translate({24 * i} 0)">{ecg}</g>' for i in range(6))
    f.add(f'<g clip-path="url(#px-rl-c)" transform="translate(34 0)">'
          + f.A(tiles, mv=[(0, 0, 0), (100, -24, 0)], rep=4, hop=4) + "</g>")
    return f


def platform_stack() -> Fig:
    f = Fig(
        "platform-stack", "ps", 128, 80,
        "Animated diagram of a platform stacking up like falling blocks. Five layers drop "
        "in one at a time and lock into a stack: runtime at the bottom, then knowledge, "
        "agents, operations and media on top. A bracket then names the whole stack as one "
        "platform.",
        "Runtime, knowledge, agents, operations and media: five layers that fit together.",
        [("layer", "Platform layer")],
        L=8, t0=-7.0)
    layers = ["RUNTIME", "KNOWLEDGE", "AGENTS", "OPS", "MEDIA"]
    for i, nm in enumerate(layers):
        y = 66 - 12 * i
        cap = "b" if i % 2 == 0 else "p"
        cells = G(cap, *[R(4 + 8 * k, y, 7, 10) for k in range(2)])
        cells += G("d", *[R(4 + 8 * k, y, 7, 10) for k in range(2, 11)])
        s = cells + f.T(22, y + 7, nm)
        t = 4 + 15 * i
        f.add(f.A(s, mv=[(0, 0, -90), (t, 0, -90), (t + 11, 0, 0)], hop=6))
    br = G("p", R(95, 18, 1, 58), R(92, 18, 3, 1), R(92, 75, 3, 1))
    f.add(f.A(br + f.T(100, 44, "ONE") + f.T(100, 51, "PLATFORM"), vis=(0, [(82, 1)])))
    return f


def engagement_path() -> Fig:
    f = Fig(
        "engagement-path", "ep", 128, 80,
        "Animated diagram of a three-stage engagement path. A person walks a floor line "
        "past three stages in order: pilot, scorecard, decision. Each stage, once reached, "
        "is outlined and marked with a check. All three are done at the end.",
        "We start with a pilot, score the result, and then decide what to build or stop.",
        [("person", "Our team"), ("check", "Stage done")],
        L=8, t0=-7.0)
    nodes = [("PILOT", 4), ("SCORECARD", 48), ("DECISION", 92)]
    arrows = [bmp(ARROW_R, 40, 27, "d"), bmp(ARROW_R, 84, 27, "d")]
    f.add(*arrows)
    for i, (nm, x) in enumerate(nodes):
        t = (8, 36, 64)[i]
        f.add(f.T(x, 10, f"0{i + 1}", c="p"))
        f.add(box(x, 14, 32, 30, "d"))
        f.add(f.A(box(x, 14, 32, 30, "k"), vis=(0, [(t, 1)])))
        f.add(f.T(x + 16, 40, nm, anchor="middle"))
        f.add(f.A(bmp(CHECK, x + 25, 18, "b"), vis=(0, [(t + 2, 1)])))
    # icons
    f.add(G("b", R(10, 22, 5, 5), R(17, 22, 5, 5)))
    f.add(G("d", *[R(54 + 8 * c, 22 + 6 * r, 6, 4) for c in range(3) for r in range(2)]))
    f.add(bmp(CHECK, 105, 21, "b", s=2))
    f.add(G("d", R(4, 62, 120, 2)))
    for cx in (20, 64, 108):
        f.add(G("d", R(cx - 2, 59, 5, 3)))
    f.add(f.A(bmp(PERSON, 0, 0, "k"), (101, 51),
              mv=[(0, -10, 51), (8, 17, 51), (18, 17, 51), (36, 61, 51), (46, 61, 51),
                  (64, 105, 51), (100, 105, 51)]))
    return f


def verdict_meter() -> Fig:
    f = Fig(
        "verdict-meter", "vm", 128, 80,
        "Animated diagram of a decision model. A question block marked with a question mark "
        "enters the decision model. A verdict panel then shows a check and the word YES with "
        "a confidence bar of seven notches out of eight. A second question follows and "
        "comes out as a cross and the word NO with five notches out of eight.",
        "A question goes in. A verdict comes out, with a confidence we can check.",
        [("q", "Question"), ("check", "Yes"), ("cross", "No")],
        L=8, t0=-3.0)
    f.add(G("d", R(0, 37, 40, 3), R(72, 37, 12, 3)), bmp(ARROW_R, 76, 36, "k"))
    for st, en in ((0, 22), (50, 72)):
        q = R(0, 0, 9, 9, "b") + bmp(QUEST, 3, 2, "g")
        f.add(f.A(q, (31, 33), vis=(1, []), show=False,
                  mv=[(st, -10, 33), (st + 8, -10, 33), (en, 44, 33)]))
    f.add(R(40, 18, 32, 40, "p"), R(42, 20, 28, 36, "g"), f.T(56, 34, "DECISION", anchor="middle"),
          f.T(56, 41, "MODEL", anchor="middle"))
    f.add(box(86, 8, 38, 58, "k"), f.T(105, 74, "VERDICT", anchor="middle"))
    bar = G("d", R(90, 54, 30, 5))
    f.add(bar)

    def verdict(on, off, fillcells, glyph, word, c):
        gl = (bmp(CHECK, 97, 12, "b", s=3) if glyph == "check" else bmp(CROSS, 97, 12, "p", s=3))
        fill = f.A(R(90, 54, 28 * fillcells // 8 + (0 if fillcells == 8 else 0), 5, c),
                   sc=([(0, 0, 1, 1), (on + 2, 0, 1, fillcells), (on + 12, 1, 1, 1)], (1, 1)))
        gaps = G("g", *[R(90 + 4 * k - 1 + 4, 54, 1, 5) for k in range(7)]) if False else ""
        s = gl + f.T(105, 46, word, fs=7, anchor="middle", c="k") + fill
        return f.A(s, vis=(0, [(on, 1), (off, 0)]), show=(word == "YES"))

    # fill width: 4 units per notch (7 -> 28, 5 -> 20)
    f.add(verdict(24, 52, 7, "check", "YES", "b"))
    f.add(verdict(74, 98, 5, "cross", "NO", "p"))
    f.add(G("g", *[R(90 + 4 * k, 54, 1, 5) for k in range(1, 8)]))
    return f


def leaderboard() -> Fig:
    f = Fig(
        "leaderboard", "lb", 128, 80,
        "Animated diagram of a benchmark leaderboard. Five horizontal bars grow to different "
        "lengths, ranked one to five. The pink bar, third at first, grows past the two above "
        "it and climbs to first place, pushing the others down one rank each. A crown "
        "marks first place.",
        "Same test, same protocol for every entry. Bars grow, ranks change, and a crown "
        "marks the leader.",
        [("crown", "Leader")],
        L=8, t0=-7.0)
    ys = [6 + 14 * i for i in range(5)]
    for i, y in enumerate(ys):
        f.add(f.T(3, y + 7, str(i + 1), fs=6))
    f.add(bmp(CROWN, 117, ys[0] + 2, "p"))
    # (final length, final row, start row)
    spec = [(80, 1, 0, "b"), (68, 2, 1, "b"), (88, 0, 2, "p"), (44, 3, 3, "b"), (30, 4, 4, "b")]
    for i, (ln, fr, sr, c) in enumerate(spec):
        t = 4 + 3 * i
        sc = [(0, 0, 1, 1), (t, 0, 1, 10), (t + 10, 1 if i != 2 else 56 / 88, 1, 1)]
        if i == 2:
            sc += [(52, 56 / 88, 1, 8), (62, 1, 1, 1)]
        mv = [(0, 12, ys[sr]), (46, 12, ys[sr]), (56, 12, ys[fr])] if fr != sr else None
        inner = R(0, 0, ln, 8, c)
        f.add(f.A(inner, (12, ys[fr]), mv=mv, sc=(sc, (1, 1)), hop=5))
    return f


def timeline() -> Fig:
    f = Fig(
        "timeline", "tl", 128, 80,
        "Animated diagram of a company timeline from 2007 to today. A progress bar fills "
        "from left to right, and six milestone blocks, each taller than the last, rise "
        "from the bar as it passes them.",
        "Running systems since 2007, and still in production.",
        [("block", "Milestone")],
        L=8, t0=-7.0)
    xs = [8, 30, 52, 74, 96, 118]
    f.add(R(6, 44, 118, 4, "d"))
    f.add(f.A(R(6, 44, 118, 4, "b"), sc=([(0, 0, 1, 1), (6, 0, 1, 28), (82, 1, 1, 1)], (1, 1))))
    for i, x in enumerate(xs):
        h = 6 + 5 * i
        t = 6 + 76 * (x - 6) // 118 + 2
        f.add(R(x + 3, 48, 1, 3, "k"))
        f.add(f.A(R(x, 42 - h, 7, h, "b") if i < 5 else R(x - 1, 42 - h, 7, h, "p"),
                  vis=(0, [(t, 1)])))
    f.add(f.T(6, 62, "2007", fs=6), f.T(64, 62, "IN PRODUCTION", anchor="middle"),
          f.T(124, 62, "TODAY", fs=6, anchor="end", c="p"))
    return f


def lost_sprite() -> Fig:
    f = Fig(
        "lost-sprite", "ls", 128, 80,
        "Animated diagram for a missing page. A small robot stands in an empty, dashed "
        "stage under the number 404 and looks left, then right, with a question mark over "
        "its head. The text reads: stage not found.",
        "This page is not here. Try the menu, or start from the home page.",
        [("q", "Looking for the page")],
        L=8, t0=-5.0)
    f.add(bmp(D4, 42, 4, "p", s=3), bmp(D0, 58, 4, "k", s=3), bmp(D4, 74, 4, "p", s=3))
    f.add(G("d", R(10, 54, 108, 2)), dashv(10, 22, 54, "d"), dashv(117, 22, 54, "d"))
    f.add(G("d", *[R(x, 22, 3, 1) for x in range(10, 118, 6)]))
    ax = 53
    body = f.A(bmp(ROBOT_C, 0, 0, "b", s=3), vis=(1, [(10, 0), (66, 1)]))
    body += f.A(bmp(ROBOT_L, 0, 0, "b", s=3), vis=(0, [(10, 1), (34, 0)]), show=False)
    body += f.A(bmp(ROBOT_R, 0, 0, "b", s=3), vis=(0, [(34, 1), (66, 0)]), show=False)
    body += f.A(bmp(QUEST, 8, -12, "p", s=2), vis=(0, [(8, 1), (66, 0)]), show=False)
    f.add(f.A(body, (ax, 36),
              mv=[(0, ax, 36), (10, ax, 36), (14, ax - 16, 36), (34, ax - 16, 36),
                  (42, ax + 16, 36), (64, ax + 16, 36), (68, ax, 36)]))
    f.add(f.T(64, 72, "STAGE NOT FOUND", fs=7, anchor="middle"))
    return f


_BUILDERS = {
    "hero-loop": hero_loop, "knowledge-base": knowledge_base, "self-aligning": self_aligning,
    "agent-harness": agent_harness, "confidence-gate": confidence_gate, "scorecard": scorecard,
    "relocate": relocate, "platform-stack": platform_stack, "engagement-path": engagement_path,
    "verdict-meter": verdict_meter, "leaderboard": leaderboard, "timeline": timeline,
    "lost-sprite": lost_sprite,
}


def render(name: str) -> str:
    """One ``<figure class="px">`` for ``name``. Raises KeyError if unknown."""
    if name not in _BUILDERS:
        raise KeyError(name)
    return _BUILDERS[name]().figure()


def keyframes_css() -> str:
    return "\n".join(_BUILDERS[n]().css() for n in NAMES)


def write_css(path: Path | None = None) -> Path:
    path = path or Path(__file__).resolve().parent / "css" / "arcade-pictograms.css"
    text = path.read_text()
    a, b = text.index(CSS_BEGIN) + len(CSS_BEGIN), text.index(CSS_END)
    path.write_text(text[:a] + "\n" + keyframes_css() + "\n" + text[b:])
    return path


if __name__ == "__main__":
    if "--write-css" in sys.argv:
        print(write_css())
    elif len(sys.argv) > 1 and sys.argv[1] in _BUILDERS:
        print(render(sys.argv[1]))
    else:
        print("usage: arcade_pictograms.py --write-css | <name>")
