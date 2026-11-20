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

Motion is SMIL (animateTransform / animate with discrete keyTimes), generated from the
same tracks that place the sprites. Every length is an SVG user unit: no CSS px in any
transform, so WebKit's text zoom cannot move a sprite off its track. web/assets/px-live.js
pauses and resumes the animations (svg.pauseAnimations) and drops them under
prefers-reduced-motion, leaving each sprite on its static pose attribute.

Every coordinate is an integer on a one-unit pixel grid. Sprites are ASCII
bitmaps merged into rects. Colour only via CSS classes (pk ink, pp pink,
pb blue, pd dim, pg bg cutout) that map to --px-* variables.
"""

from __future__ import annotations

import re
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
    "eras",
    "lost-sprite",
    "chat-room",
    "page-audio",
    "venue-system",
    "newsroom",
)


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
LAMBDA = ["#....", ".#...", ".#...", "..#..", ".#.#.", "#...#"]
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
    def __init__(self, name, abbr, w, h, label, sentence, legend, L=8, t0=0.0, fs=5, y0=0):
        self.name, self.abbr, self.w, self.h = name, abbr, w, h
        self.label, self.sentence, self.legend = label, sentence, legend
        self.L, self.t0, self.fs, self.y0 = L, t0, fs, y0
        self.alt = None
        self.meta: dict = {}
        self.parts: list[str] = []
        self.defs = ""

    # -- text -------------------------------------------------------------
    def T(self, x, y, s, fs=None, anchor="start", c="k") -> str:
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        return (f'<text class="px__t p{c}" x="{_n(x)}" y="{_n(y)}" '
                f'font-size="{_n(fs or self.fs)}"{a}>{s}</text>')

    def add(self, *s):
        self.parts.extend(s)

    # -- motion (SMIL, so every length is an SVG user unit and never a CSS px) ----------
    def _timing(self, rep=1) -> str:
        return (f'dur="{_n(self.L / rep)}s" begin="{_n(self.t0)}s" '
                f'repeatCount="indefinite" calcMode="discrete"')

    @staticmethod
    def _stepped(pts):
        """[(pct, (v...), n)] -> discrete (times, values): CSS steps(n, end) between points."""
        times, vals = [], []
        for i, (p, v, n) in enumerate(pts):
            if i + 1 == len(pts):
                times.append(p)
                vals.append(v)
                break
            q, w = pts[i + 1][0], pts[i + 1][1]
            for k in range(n):
                times.append(p + (q - p) * k / n)
                vals.append(tuple(a + (b - a) * k / n for a, b in zip(v, w)))
        return times, vals

    def _smil(self, tag, extra, times, vals, rep=1) -> str:
        kt = ";".join(_n(round(t / 100, 4)) for t in times)
        vs = ";".join(" ".join(_n(x) for x in v) for v in vals)
        return f'<{tag} {extra} values="{vs}" keyTimes="{kt}" {self._timing(rep)}/>'

    def _vis_anim(self, init, tg) -> str:
        times, vals = [0], [(init,)]
        for t, v in tg:
            times.append(t)
            vals.append((v,))
        return self._smil("animate", 'attributeName="opacity"', times, vals)

    def vcls(self, init, tg) -> str:
        """The animation a vis track with this clock uses (shared clocks are identical strings)."""
        return self._vis_anim(init, tg)

    def A(self, inner, pose=None, mv=None, sc=None, vis=None, hop=4, rep=1, show=True,
          org=(0, 0)):
        """Wrap ``inner`` in animation groups (all SMIL, user units).

        mv:  [(pct, x, y), ...] stepped translate (hop = unit size of one step)
        sc:  [(pct, sx, sy, steps), ...] stepped scale about ``org``
        vis: (initial 0/1, [(pct, 0/1), ...]) hard toggles
        show: static (reduced-motion) visibility
        """
        s = inner
        if vis is not None:
            init, tg = vis
            op = "" if show else ' opacity="0"'
            s = f'<g{op}>{self._vis_anim(init, tg)}{s}</g>'
        elif not show:
            s = f'<g opacity="0">{s}</g>'
        if sc is not None:
            pts = list(sc)
            if pts[-1][0] < 100:
                pts.append((100, pts[-1][1], pts[-1][2], 1))
            times, vals = self._stepped([(p, (sx, sy), n) for p, sx, sy, n in pts])
            a = self._smil("animateTransform", 'attributeName="transform" type="scale"',
                           times, vals)
            ox, oy = org
            if org != (0, 0):
                s = f'<g transform="translate({_n(-ox)} {_n(-oy)})">{s}</g>'
            s = f'<g>{a}{s}</g>'
            if org != (0, 0):
                s = f'<g transform="translate({_n(ox)} {_n(oy)})">{s}</g>'
        if mv is not None:
            pts = list(mv)
            if pts[0][0] > 0:
                pts.insert(0, (0, pts[0][1], pts[0][2]))
            if pts[-1][0] < 100:
                pts.append((100, pts[-1][1], pts[-1][2]))
            sp = []
            for i, (p, x, y) in enumerate(pts):
                n = 1
                if i + 1 < len(pts):
                    n = max(1, round(max(abs(pts[i + 1][1] - x), abs(pts[i + 1][2] - y)) / hop))
                sp.append((p, (x, y), n))
            times, vals = self._stepped(sp)
            a = self._smil("animateTransform", 'attributeName="transform" type="translate"',
                           times, vals, rep)
            tr = f' transform="translate({_n(pose[0])} {_n(pose[1])})"' if pose else ""
            s = f'<g{tr}>{a}{s}</g>'
        elif pose is not None and pose != (0, 0):
            s = f'<g transform="translate({_n(pose[0])} {_n(pose[1])})">{s}</g>'
        return s

    # -- output -----------------------------------------------------------
    def svg(self, plain=False, v="") -> str:
        d = f"<defs>{self.defs}</defs>" if self.defs else ""
        a = ('' if plain else f' role="img" aria-label="{self.label}"')
        return (f'<svg class="px__svg"{v} viewBox="0 {self.y0} {self.w} {self.h}"{a} '
                f'shape-rendering="crispEdges" focusable="false"'
                f'{" aria-hidden=\"true\"" if plain else ""}>'
                f'{d}{"".join(self.parts)}</svg>')

    def figure(self) -> str:
        lg = "".join(f'<li>{_lg_glyph(k)}<span>{t}</span></li>' for k, t in self.legend)
        ul = f'<ul class="px__lg">{lg}</ul>' if lg else ""
        if self.alt:
            stage = (f'<div class="px__stage" role="img" aria-label="{self.label}">'
                     f'{self.svg(True, ' data-v="wide"')}{self.alt.svg(True, ' data-v="tall"')}</div>')
        else:
            stage = self.svg()
        return (f'<figure class="px px--{self.abbr}" data-px="{self.name}">{stage}'
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
    "play": (ARROW_R, "p"), "lines": (["#####", ".....", "####.", ".....", "###.."], "k"),
    "wave": (["..#....", "..#...#", "..#.#.#", "#.#.#.#", "#.#.#.#"], "b"),
    "lambda": (LAMBDA, "b"), "token": (["#####"] * 5, "p"),
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
    return s


# --------------------------------------------------------------------------
# the pictograms
# --------------------------------------------------------------------------
_HERO_LABEL = (
    "Animated diagram of a self-aligning loop. A steady stream of items enters a model. "
    "Most are confident: each carries a check mark and goes straight to the automatic bin. "
    "One is uncertain: it carries a question mark and goes to a human reviewer, who marks "
    "it with a cross. A pink correction then travels back along the loop to the model, "
    "its confidence meter rises from two notches to three, and the items that follow go "
    "straight through.")
_HERO_SENT = ("Confident items go straight through. Uncertain ones go to a person, and every "
              "correction travels back to the model.")
_HERO_LEG = [("check", "Confident: auto"), ("q", "Uncertain: ask a person"),
             ("cross", "Reviewer says no"), ("corr", "Correction")]


def _hero(wide: bool) -> Fig:
    if wide:
        f = Fig("hero-loop", "hl", 192, 82, _HERO_LABEL, _HERO_SENT, _HERO_LEG,
                L=12, t0=-6.6, fs=7, y0=14)
        mx, ent, hold, edge, bx, slots = 48, 42, 58, 88, 99, [180, 172, 164, 156, 148, 140]
        LY, desk = 71, 124
        starts = [0, 10, 20, 30, 40, 50, 58]
        fs = 7
    else:
        f = Fig("hero-loop", "hm", 120, 108, _HERO_LABEL, _HERO_SENT, _HERO_LEG,
                L=12, t0=-6.6, fs=6)
        mx, ent, hold, edge, bx, slots = 30, 24, 44, 70, 73, [108, 100, 92]
        LY, desk = 67, 84
        starts = [0, 14, 28, 56]
        fs = 6
    Y = 30
    cw = mx + 40  # right edge of model
    # tracks and arrows
    if wide:
        f.add(G("d", R(0, 32, mx, 3), R(cw, 32, 50, 3), R(101, 35, 3, 40), R(101, 73, 25, 3),
                R(66, 83, 81, 3), R(66, 62, 3, 22), R(144, 80, 3, 5)))
        f.add(bmp(ARROW_R, 131, 31, "k"), bmp(ARROW_R, 118, 72, "k"), bmp(ARROW_D, 100, 52, "k"))
        f.add(f.T(2, 25, "ITEMS"))
    else:
        f.add(G("d", R(0, 32, mx, 3), R(cw, 32, 14, 3), R(75, 35, 3, 36), R(75, 69, 9, 3),
                R(48, 95, 68, 3), R(48, 61, 3, 36), R(113, 66, 3, 31), R(103, 66, 10, 3)))
        f.add(bmp(ARROW_R, 79, 31, "k"), bmp(ARROW_R, 79, 68, "k"), bmp(ARROW_D, 74, 50, "k"))
        f.add(f.T(2, 25, "ITEMS"))
    # items, drawn before the model so they pass behind it
    for k, st in enumerate(starts):
        if k == 0:
            i0 = (R(0, 0, 7, 7, "b")
                  + f.A(bmp(QUEST, 2, 1, "g"), vis=(0, [(36, 1), (56, 0)]), show=False)
                  + f.A(bmp(CROSS, 1, -7, "p"), vis=(0, [(56, 1)])))
            f.add(f.A(i0, (desk, LY), vis=(1, [(68, 0)]),
                      mv=[(0, -8, Y), (20, ent, Y), (23, hold, Y), (34, hold, Y), (38, bx, Y),
                          (40, bx, Y), (48, bx, LY), (52, desk, LY)]))
            continue
        slot = slots[k - 1]
        te = st + 26 + round(13 * (edge - hold) / (slot - hold))
        it = R(0, 0, 7, 7, "b") + f.A(bmp(CHECK, 1, 2, "g"), vis=(0, [(te, 1)]))
        f.add(f.A(it, (slot, Y), mv=[(0, -8, Y), (st, -8, Y), (st + 20, ent, Y),
                                     (st + 23, hold, Y), (st + 26, hold, Y), (st + 39, slot, Y)]))
    # model
    cx = mx + 20
    f.add(R(mx, 16, 40, 42, "p"), R(mx + 2, 18, 36, 38, "g"),
          f.T(cx, 30, "MODEL", anchor="middle"), f.T(cx, 52, "TRUST", anchor="middle"))
    cells = [R(mx + 6 + 6 * i, 36, 5, 6) for i in range(5)]
    f.add(G("d", *cells), G("b", cells[0], cells[1]))
    f.add(f.A(G("b", cells[2]), vis=(0, [(70, 1)])))
    # auto bin
    if wide:
        f.add(G("k", R(138, 26, 52, 2), R(138, 40, 52, 2), R(188, 28, 2, 12)))
        f.add(bmp(CHECK, 150, 19, "b"), f.T(158, 23, "AUTO"))
    else:
        f.add(G("k", R(84, 26, 34, 2), R(84, 40, 34, 2), R(116, 28, 2, 12)))
        f.add(bmp(CHECK, 88, 19, "b"), f.T(96, 23, "AUTO"))
    # reviewer
    if wide:
        f.add(bmp(ARROW_U, 65, 59, "p"), f.T(74, 91, "CORRECTION", c="p"))
        f.add(bmp(PERSON, 140, 68, "k"), f.T(154, 75, "REVIEW"),
              bmp(CHECK, 154, 79, "b"), bmp(CROSS, 164, 79, "p"))
        pm = [(0, 144, 76), (57, 144, 76), (59, 144, 83), (66, 66, 83), (69, 66, 62)]
        pp = (66, 62)
    else:
        f.add(bmp(ARROW_U, 47, 58, "p"), f.T(82, 106, "CORRECTION", anchor="middle", c="p"))
        f.add(bmp(PERSON, 96, 62, "k"), f.T(98, 82, "REVIEW", anchor="middle"),
              bmp(CHECK, 87, 85, "b"), bmp(CROSS, 101, 85, "p"))
        pm = [(0, 103, 66), (57, 103, 66), (58, 113, 66), (60, 113, 95), (66, 48, 95),
              (69, 48, 61)]
        pp = (48, 61)
    f.add(f.A(R(0, 0, 3, 3, "p"), pp, vis=(0, [(57, 1), (69, 0)]), show=False, mv=pm))
    return f


def hero_loop() -> Fig:
    f = _hero(True)
    f.alt = _hero(False)
    return f


def knowledge_base() -> Fig:
    f = Fig(
        "knowledge-base", "kb", 128, 88,
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
    f.add(box(2, 76, 38, 11, "k"), f.T(21, 84, "QUERY", anchor="middle"))
    f.add(f.A(bmp(CURSOR, 0, 0, "k"), (89, 41),
              mv=[(0, 34, 80), (58, 34, 80), (66, 118, 60), (72, 100, 48), (76, 89, 41)]))
    # found marker
    f.add(f.A(G("p", R(84, 35, 3, 1), R(84, 35, 1, 3), R(95, 35, 3, 1), R(97, 35, 1, 3),
                R(84, 46, 3, 1), R(84, 44, 1, 3), R(95, 46, 3, 1), R(97, 44, 1, 3))
              + bmp(CHECK, 88, 28, "b"), vis=(0, [(78, 1)])))
    return f


def self_aligning() -> Fig:
    f = Fig(
        "self-aligning", "sa", 128, 80,
        "Animated diagram of a rule being learned. The first item on the conveyor stops at "
        "a human reviewer, who marks it with a cross. A pink correction travels to a gate, "
        "which becomes a rule. The next three similar items pass through the rule gate "
        "without review, each marked with a check, and land in the automatic bin.",
        "A reviewer says no once, and we write down why. After that, the rule handles the "
        "same case without them.",
        [("cross", "Reviewer says no"), ("rule", "Rule"), ("check", "Passed by rule")],
        L=8, t0=-7.4)
    f.add(G("d", R(0, 33, 88, 4)))
    arch = lambda c: G(c, R(52, 20, 28, 3), R(52, 23, 3, 19), R(77, 23, 3, 19))
    f.add(arch("d"))
    f.add(f.A(arch("p") + f.T(66, 17, "RULE", anchor="middle"), vis=(0, [(42, 1)])))
    f.add(G("k", R(88, 22, 38, 2), R(88, 41, 38, 2), R(124, 24, 2, 17)))
    f.add(bmp(CHECK, 96, 11, "b"), f.T(103, 16, "AUTO"))
    f.add(bmp(PERSON, 16, 44, "k"), f.T(20, 64, "REVIEW", anchor="middle"))
    i0 = R(0, 0, 8, 8, "b") + f.A(bmp(CROSS, 1, -7, "p"), vis=(0, [(18, 1)]))
    f.add(f.A(i0, (16, 31), vis=(1, [(30, 0)]), mv=[(0, -9, 31), (14, 16, 31), (30, 16, 31)]))
    for st, bx in ((34, 113), (46, 102), (58, 91)):
        it = R(0, 0, 8, 8, "b") + f.A(bmp(CHECK, 1, -6, "b"), vis=(0, [(st + 16, 1)]))
        f.add(f.A(it, (bx, 31), mv=[(0, -9, 31), (st, -9, 31), (st + 34, bx, 31)], hop=5))
    f.add(f.A(R(0, 0, 3, 3, "p"), (66, 24), vis=(0, [(30, 1), (42, 0)]), show=False,
              mv=[(0, 24, 47), (30, 24, 47), (36, 66, 47), (42, 66, 24)]))
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
        f.add(f.A(R(14, y + 1, fl, 5, "b"), org=(14, y + 1),
                  sc=[(0, 0, 1, 1), (t + 4, 0, 1, 8), (t + 12, 1, 1, 1)]))
        if ok:
            g = bmp(CHECK, 98, y + 1, "b") + f.T(106, y + 6, "AUTO")
        else:
            g = bmp(QUEST, 98, y + 1, "p") + f.T(106, y + 6, "ESCALATE")
        f.add(f.A(g, vis=(0, [(t + 13, 1)])))
    return f


_SC_ROWS = tuple(8 + 12 * r for r in range(6))  # % at which row r is scored AND document r joins the stack
_SC_GRID = ["1111", "1011", "1110", "0111", "1111", "1101"]  # 4 crosses, 20 checks


def scorecard() -> Fig:
    f = Fig(
        "scorecard", "sc", 128, 80,
        "Animated diagram of calls being scored. A scorecard lists six calls, each with a "
        "waveform, scored against four criteria. A scanner moves down the rows and each "
        "row's cells fill with checks and crosses: twenty checks and four crosses in all. "
        "Each call is one document: every time a row is scored, one new document joins the "
        "stack at the top right at that same moment, so six rows scored means six documents "
        "stacked. The labels read: hundreds of scorecards, millions of calls.",
        "Each call is one document and gets one scored row. We have scored calls this way "
        "across hundreds of scorecards and millions of calls.",
        [("check", "Pass"), ("cross", "Miss")],
        L=12, t0=-10.0)
    heights = [[2, 5, 3, 6, 2], [4, 2, 6, 3, 5], [3, 6, 4, 2, 5], [5, 3, 2, 6, 4],
               [2, 4, 6, 3, 2], [6, 2, 4, 5, 3]]
    f.add(box(2, 2, 86, 76, "k"))
    f.add(f.T(6, 11, "CALL"), f.T(34, 11, "CRITERIA"))

    def raw(rows):  # rects only; colour comes from the referencing <use>
        return bmp(rows, 0, 0, "k")[len('<g class="pk">'):-len("</g>")]
    f.defs = f'<g id="px-sc-ck">{raw(CHECK)}</g><g id="px-sc-cx">{raw(CROSS)}</g>'
    f.meta["rows"], f.meta["docs"] = [], []
    for r in range(6):
        y = 15 + 10 * r
        f.add(G("b", *[R(6 + 4 * i, y + 4 - h // 2, 2, h) for i, h in enumerate(heights[r])]),
              G("d", *[R(34 + 11 * j, y, 9, 8) for j in range(4)]))
    for r, t in enumerate(_SC_ROWS):
        y = 15 + 10 * r
        marks = ""
        for j in range(4):
            ok = _SC_GRID[r][j] == "1"
            marks += (f'<use class="p{"b" if ok else "p"}" href="#px-sc-{"ck" if ok else "cx"}" '
                      f'x="{36 + 11 * j}" y="{y + (2 if ok else 1)}"/>')
        spec = (0, [(t, 1)])
        f.meta["rows"].append(f.vcls(*spec))
        f.add(f.A(marks, vis=spec))
    pts = []
    for r, t in enumerate(_SC_ROWS):
        pts += [(t, 0, 14 + 10 * r), (t + 6, 0, 14 + 10 * r)]
    f.add(f.A(box(4, 0, 80, 10, "p"), show=False, vis=(1, []), mv=pts, hop=5))
    # the stack of documents: document r appears on the very same clock as row r
    for r, t in enumerate(_SC_ROWS):
        x, y = 92 + 2 * r, 4 + 3 * r
        doc = (G("g", R(x, y, 22, 24)) + box(x, y, 22, 24, "k")
               + G("d", R(x + 3, y + 4, 12, 2), R(x + 3, y + 9, 12, 2)))
        spec = (0, [(t, 1)])
        f.meta["docs"].append(f.vcls(*spec))
        f.add(f.A(doc, vis=spec))
    f.add(f.T(92, 54, "HUNDREDS OF", c="p"), f.T(92, 60, "SCORECARDS"),
          f.T(92, 70, "MILLIONS OF", c="b"), f.T(92, 76, "CALLS"))
    return f


def relocate() -> Fig:
    f = Fig(
        "relocate", "rl", 128, 80,
        "Animated diagram of a system surviving a data center failure. Site A, a rack of four "
        "blocks, fails and is marked with a cross, and the heartbeat line at the bottom goes "
        "flat. The four blocks move one by one to Site B, which takes over and is marked "
        "with a check. The heartbeat resumes, and a check appears at the marker labelled "
        "doors, so we were back up before the doors opened.",
        "A data center failed. We moved the system within hours and were back up before the "
        "doors opened.",
        [("cross", "Site down"), ("check", "Serving")],
        L=12, t0=-9.6)
    # the clip rect grows left to right (stepped), revealing the heartbeat trace as time passes
    wt, wv = f._stepped([(0, (0,), 1), (4, (0,), 23), (84, (94,), 1), (100, (94,), 1)])
    f.defs = (f'<clipPath id="px-rl-c"><rect x="34" y="58" width="94" height="22">'
              + f._smil("animate", 'attributeName="width"', wt, wv)
              + "</rect></clipPath>")
    RX = (10, 88)
    f.add(f.A(box(10, 10, 28, 42, "k", 2), vis=(1, [(18, 0)]), show=False),
          f.A(box(10, 10, 28, 42, "d", 2), vis=(0, [(18, 1)])))
    f.add(f.A(box(88, 10, 28, 42, "d", 2), vis=(1, [(22, 0)]), show=False),
          f.A(box(88, 10, 28, 42, "k", 2), vis=(0, [(22, 1)])))
    f.add(f.T(24, 7, "SITE A", anchor="middle"), f.T(102, 7, "SITE B", anchor="middle"))
    f.add(f.A(bmp(CROSS, 35, 2, "p"), vis=(0, [(18, 1)])))
    f.add(f.A(bmp(CHECK, 113, 3, "b"), vis=(0, [(52, 1)])))
    f.add(bmp(ARROW_R, 58, 29, "d"))
    for i in range(4):
        y = 14 + 10 * i
        t = 20 + 6 * i
        f.add(f.A(R(0, 0, 20, 6, "b"), (92, y),
                  mv=[(0, 14, y), (t, 14, y), (t + 6, 53, y - 4), (t + 12, 92, y)], hop=5))
    # heartbeat: a fixed trace revealed left to right by a moving cover
    f.add(f.T(2, 72, "UPTIME"))
    ecg = G("p", R(0, 70, 7, 1), R(7, 69, 2, 1), R(9, 70, 3, 1), R(12, 62, 1, 9),
            R(13, 70, 1, 7), R(14, 70, 10, 1))
    tr = ("".join(f'<g transform="translate({x} 0)">{ecg}</g>' for x in (34, 90, 114))
          + G("p", R(58, 70, 32, 1)))
    f.add('<g clip-path="url(#px-rl-c)">' + tr + "</g>")
    f.add(f.A(bmp(CROSS, 71, 60, "p"), vis=(0, [(18, 1), (54, 0)]), show=False))
    f.add(G("k", *[R(108, y, 1, 2) for y in range(60, 78, 4)]), f.T(108, 58, "DOORS", anchor="middle"))
    f.add(f.A(bmp(CHECK, 116, 54, "b"), vis=(0, [(72, 1)])))
    return f


def platform_stack() -> Fig:
    f = Fig(
        "platform-stack", "ps", 128, 80,
        "Animated diagram of a platform stacking up like falling blocks. Five layers drop "
        "in one at a time and lock into a stack: knowledge at the bottom, then decision "
        "models, agents, operations and media on top. A bracket then names the whole stack "
        "as one platform.",
        "Knowledge, decision models, agents, operations and media: five layers that fit "
        "together.",
        [("layer", "Platform layer")],
        L=8, t0=-7.0)
    layers = ["KNOWLEDGE", "DECISION MODELS", "AGENTS", "OPS", "MEDIA"]
    for i, nm in enumerate(layers):
        y = 66 - 12 * i
        cap = "b" if i % 2 == 0 else "p"
        cells = G(cap, *[R(4 + 8 * k, y, 7, 10) for k in range(2)])
        cells += G("d", *[R(4 + 8 * k, y, 7, 10) for k in range(2, 11)])
        s = cells + f.T(22, y + 7, nm)
        t = 10 * i
        f.add(f.A(s, mv=[(0, 0, -44 - 8 * i), (t, 0, -44 - 8 * i), (t + 7, 0, 0)], hop=6))
    br = G("p", R(95, 18, 1, 58), R(92, 18, 3, 1), R(92, 75, 3, 1))
    f.add(f.A(br + f.T(100, 44, "ONE") + f.T(100, 51, "PLATFORM"), vis=(0, [(52, 1)])))
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
        fill = f.A(R(90, 54, 28 * fillcells // 8, 5, c), org=(90, 54),
                   sc=[(0, 0, 1, 1), (on + 2, 0, 1, fillcells), (on + 12, 1, 1, 1)])
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
        f.add(f.A(inner, (12, ys[fr]), mv=mv, sc=sc, hop=5))
    return f


def _cloud_rows():
    """Pixel cloud outline (27 x 17): union of circles over a flat base, outline only."""
    circles = [(9, 12, 5), (16, 8, 7), (24, 11, 6)]

    def inside(x, y):
        return (any((x - cx) ** 2 + (y - cy) ** 2 <= r * r for cx, cy, r in circles)
                or (4 <= x <= 29 and 12 <= y <= 17))
    rows = []
    for y in range(1, 18):
        row = ""
        for x in range(4, 31):
            edge = inside(x, y) and any(not inside(x + dx, y + dy)
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            row += "#" if edge else "."
        rows.append(row)
    return rows


_CLOUD = _cloud_rows()


def _loop_pos(pts, n, off):
    """n integer positions evenly spaced (by arc length) around the closed polyline ``pts``."""
    segs = list(zip(pts, pts[1:] + pts[:1]))
    lens = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in segs]
    total = sum(lens)
    out = []
    for i in range(n):
        d = (total * (i / n + off)) % total
        for (a, b), ln in zip(segs, lens):
            if d < ln or ln == 0:
                k = d / ln if ln else 0
                out.append((round(a[0] + (b[0] - a[0]) * k), round(a[1] + (b[1] - a[1]) * k)))
                break
            d -= ln
    return out, total


def eras() -> Fig:
    f = Fig(
        "eras", "er", 160, 88,
        "Animated diagram of one revenue-critical system that the same team kept running "
        "through four shifts in technology, left to right. First, on-premises: the system "
        "runs in a server rack whose unit lights blink. Second, cloud: it runs in a cloud, "
        "with small puffs rising from the rack into it. Third, serverless: it is a set of "
        "small functions, each marked with a lambda sign, passing events around a ring. "
        "Fourth, AI: a model and agents sit around a function, and a check mark shows each "
        "decision. Small revenue tokens flow along a conveyor under all four stages without "
        "a break. The first stage is dated 2007 and the last is today.",
        "One system, four shifts: on-premises, cloud, serverless, and now AI. We kept it "
        "running through each.",
        [("token", "Revenue"), ("lambda", "Function"), ("robot", "Agent"),
         ("check", "Decision")],
        L=12, t0=-2.0, fs=5.5)

    def stream(pts, n, offs, inner, show_static=True):
        """Dots circulating a closed polyline: stepped translate SMIL, one clock."""
        for off in offs:
            pos, _ = _loop_pos(pts, n, off)
            kt = [100 * i / n for i in range(n)]
            vals = [(x, y) for x, y in pos]
            a = f._smil("animateTransform", 'attributeName="transform" type="translate"',
                        kt, vals)
            tr = f' transform="translate({pos[0][0]} {pos[0][1]})"'
            op = "" if show_static else ' opacity="0"'
            f.add(f'<g{op}><g{tr}>{a}{inner}</g></g>')

    # conveyor of revenue tokens under all four stages
    f.add(G("d", R(2, 57, 150, 2)), bmp(ARROW_R, 153, 54, "k"))
    # stage 1: ON-PREM, a rack with blinking unit lights
    f.add(R(7, 4, 24, 46, "g"), box(7, 4, 24, 46, "k"), G("k", R(9, 50, 4, 2), R(25, 50, 4, 2)))
    for i in range(4):
        y = 8 + 10 * i
        f.add(box(10, y, 18, 8, "k"), G("d", R(18, y + 2, 8, 1), R(18, y + 5, 8, 1)))
        on = [((i * 9 + 25 * k) % 100) for k in range(4)]
        tg = []
        for p in sorted(on):
            tg += [(p, 1), (min(p + 12, 99), 0)]
        tg = sorted(set(tg))
        f.add(f.A(R(12, y + 3, 3, 2, "p"), vis=(0, tg), show=True))
    # rack -> cloud: puffs rising and drifting into the cloud
    stream([(30, 14), (30, 2), (42, 2), (42, 24), (50, 24), (50, 24)], 24, (0, 0.5),
           R(0, 0, 2, 2, "b"))
    # stage 2: CLOUD with the system's blocks inside
    f.add(bmp(_CLOUD, 47, 18, "k"))
    for j in range(3):
        x = 51 + 8 * j
        f.add(R(x, 28, 5, 5, "g"), box(x, 28, 5, 5, "b"))
        w = 33 * j
        f.add(f.A(R(x, 28, 5, 5, "b"), vis=(0, [(w + 4, 1), (w + 30, 0)]), show=True))
    # cloud -> functions, functions -> model
    stream([(74, 26), (80, 26), (80, 14), (88, 14), (88, 14), (80, 14), (80, 26)], 20, (0, 0.5),
           R(0, 0, 2, 2, "b"))
    stream([(112, 12), (128, 12), (128, 12), (112, 12)], 12, (0, 0.5),
           R(0, 0, 2, 2, "b"))
    # stage 3: SERVERLESS, functions passing events around a ring
    f.add(G("d", R(95, 12, 11, 3), R(110, 19, 3, 22), R(106, 38, 7, 3),
            R(89, 38, 6, 3), R(89, 19, 3, 22)))
    ring = [(96, 12), (108, 12), (108, 38), (96, 38), (89, 38), (89, 12)]
    stream(ring, 28, (0, 1 / 3, 2 / 3), R(0, 0, 3, 3, "p"))
    for k, (x, y) in enumerate(((84, 8), (106, 8), (95, 34))):
        f.add(R(x, y, 11, 11, "g"), box(x, y, 11, 11, "b"), bmp(LAMBDA, x + 3, y + 3, "b"))
        w = 33 * k
        f.add(f.A(R(x, y, 11, 11, "b") + bmp(LAMBDA, x + 3, y + 3, "g"),
                  vis=(0, [(w + 2, 1), (w + 24, 0)]), show=False))
    # stage 4: AI, a model and agents around a function, with a decision
    f.add(R(128, 6, 24, 11, "g"), box(128, 6, 24, 11, "k"), f.T(140, 14.5, "MODEL", anchor="middle"))
    f.add(bmp(ARROW_D, 138, 18, "k"))
    f.add(R(136, 22, 9, 9, "g"), box(136, 22, 9, 9, "b"), bmp(LAMBDA, 138, 23, "b"))
    for x in (125, 149):
        look = {"C": ROBOT_C, "L": ROBOT_L, "R": ROBOT_R}
        f.add(f.A(bmp(look["C"], x, 23, "b"), vis=(1, [(20, 0), (40, 1), (60, 0), (80, 1)])))
        f.add(f.A(bmp(look["L"], x, 23, "b"), vis=(0, [(20, 1), (40, 0)]), show=False))
        f.add(f.A(bmp(look["R"], x, 23, "b"), vis=(0, [(60, 1), (80, 0)]), show=False))
    f.add(bmp(ARROW_D, 138, 32, "k"))
    f.add(R(136, 37, 9, 9, "g"), box(136, 37, 9, 9, "d"))
    f.add(f.A(box(136, 37, 9, 9, "k") + bmp(CHECK, 138, 40, "b"),
              vis=(0, [(p, v) for q in (10, 35, 60, 85) for p, v in ((q, 1), (q + 12, 0))]),
              show=True))
    # revenue tokens: never stop
    stream([(3, 54), (149, 54)], 37, (0, 1 / 3, 2 / 3), R(0, 0, 5, 5, "p"))
    f.add(f.T(19, 70, "ON-PREM", anchor="middle"), f.T(60, 70, "CLOUD", anchor="middle"),
          f.T(100, 70, "SERVERLESS", anchor="middle"), f.T(140, 70, "AI", anchor="middle"))
    f.add(f.T(19, 82, "2007", anchor="middle"), f.T(140, 82, "TODAY", anchor="middle", c="p"))
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


def _msg(f, x, y, w, c="k"):
    """A message bubble: outlined box with two text lines."""
    return box(x, y, w, 12, c) + G("d", R(x + 3, y + 3, w - 10, 2), R(x + 3, y + 7, w - 18, 2))


def chat_room() -> Fig:
    f = Fig(
        "chat-room", "cr", 128, 80,
        "Animated diagram of a shared chat room where two people and two bots work "
        "together. A person posts a message and the first bot replies. The bot then posts "
        "an action marked with a question mark, which needs approval. The second person "
        "approves it with a check mark and the action runs. The second bot posts another "
        "request, also marked with a question mark, and the person declines it with a "
        "cross.",
        "People and bots share one room. A bot asks before it acts: a person approves or "
        "declines each request.",
        [("check", "Approved"), ("cross", "Declined"), ("q", "Needs approval")],
        L=12, t0=-10.0)
    f.add(f.T(4, 9, "ROOM"), box(2, 12, 124, 66, "k"))
    f.add(bmp(PERSON, 6, 16, "k"), bmp(PERSON, 6, 44, "k"))
    f.add(bmp(ROBOT_C, 112, 24, "b", s=1), bmp(ROBOT_C, 112, 56, "b", s=1))
    f.add(G("d", R(18, 31, 94, 1)))
    # row 1: a person's message and the bot's reply
    f.add(f.A(_msg(f, 16, 17, 40), vis=(0, [(4, 1)])))
    f.add(f.A(_msg(f, 64, 17, 40, "b"), vis=(0, [(12, 1)])))
    # row 2: the bot asks, the second person approves, the action runs
    f.add(f.A(box(60, 37, 46, 12, "p") + f.T(74, 46, "ACTION"), vis=(0, [(22, 1)])))
    f.add(f.A(bmp(QUEST, 63, 39, "p"), vis=(0, [(22, 1), (40, 0)]), show=False))
    f.add(f.A(bmp(CHECK, 63, 40, "b"), vis=(0, [(40, 1)])))
    f.add(G("d", R(60, 51, 46, 3)))
    f.add(f.A(R(60, 51, 46, 3, "b"), org=(60, 51),
              sc=[(0, 0, 1, 1), (42, 0, 1, 12), (56, 1, 1, 1)]))
    f.add(f.A(box(16, 37, 14, 12, "k") + bmp(CHECK, 20, 41, "b"), vis=(0, [(38, 1), (58, 0)]),
              show=False))
    # row 3: another request, declined
    f.add(f.A(box(60, 58, 46, 12, "d") + f.T(74, 67, "ACTION", c="d"), vis=(0, [(78, 1)]),
              show=False))
    f.add(f.A(box(60, 58, 46, 12, "p") + f.T(74, 67, "ACTION"), vis=(0, [(62, 1), (78, 0)])))
    f.add(f.A(bmp(QUEST, 63, 60, "p"), vis=(0, [(62, 1), (78, 0)]), show=False))
    f.add(f.A(bmp(CROSS, 63, 61, "p"), vis=(0, [(78, 1)])))
    f.add(f.A(box(16, 58, 14, 12, "k") + bmp(CROSS, 20, 61, "p"), vis=(0, [(76, 1), (96, 0)]),
              show=False))
    return f


def page_audio() -> Fig:
    f = Fig(
        "page-audio", "pa", 128, 80,
        "Animated diagram of a web page reading itself aloud. A page with seven lines of "
        "text and a play button sends its text to a chip labelled GPU. A pink reading "
        "cursor moves down the lines one at a time, each line turning dark as it is read, "
        "while a waveform of ten pixel bars grows on the right.",
        "One embed on the page turns its text into speech, using open text-to-speech models "
        "on a GPU you choose.",
        [("play", "Play"), ("lines", "Text"), ("wave", "Audio")],
        L=12, t0=-9.0)
    f.add(box(4, 6, 62, 68, "k"), G("d", R(6, 8, 58, 4)))
    widths = [40, 50, 34, 50, 44, 28, 46]
    for i, w in enumerate(widths):
        y = 16 + 7 * i
        f.add(G("d", R(8, y, w, 3)))
        f.add(f.A(G("k", R(8, y, w, 3)), vis=(0, [(10 + 10 * i, 1)])))
    f.add(f.A(box(7, 14, 56, 7, "p"), show=False, vis=(1, []),
              mv=[(0, 0, 0), (8, 0, 0), *[(10 + 10 * i, 0, 7 * i) for i in range(7)], (82, 0, 42),
                  (100, 0, 42)], hop=7))
    f.add(box(8, 63, 12, 9, "p"), bmp(ARROW_R, 12, 65, "p"))
    # page -> GPU -> audio
    f.add(G("d", R(66, 13, 14, 2), R(101, 22, 2, 8)), bmp(ARROW_R, 78, 11, "k"),
          bmp(ARROW_D, 99, 30, "k"))
    f.add(box(84, 6, 36, 16, "k"), f.T(102, 17, "GPU", anchor="middle"))
    f.add(G("k", *[R(88 + 8 * k, 3, 2, 3) for k in range(4)],
            *[R(88 + 8 * k, 22, 2, 3) for k in range(4)]))
    f.add(G("d", R(80, 58, 42, 1)))
    hs = [8, 16, 12, 22, 14, 20, 10, 18, 12, 6]
    for k, h in enumerate(hs):
        t = 12 + 7 * k
        pts = [(0, 1, 0, 1), (t, 1, 0, 1), (t + 4, 1, 1, 3)]
        for c in range(4):
            pts += [(t + 10 + 14 * c, 1, 0.6, 2), (t + 17 + 14 * c, 1, 1, 2)]
        pts = [p for p in pts if p[0] < 100]
        f.add(f.A(R(0, -h, 2, h, "b"), (82 + 4 * k, 58), sc=pts))
    f.add(f.T(101, 68, "AUDIO", anchor="middle"))
    return f


def venue_system() -> Fig:
    f = Fig(
        "venue-system", "vs", 128, 82,
        "Animated diagram of Venue Driver as a serverless, event-driven system. Three intake "
        "blocks on the left, tickets, tables and guest list, send small event blocks along "
        "tracks into a single queue. The events pass through a row of three serverless "
        "functions, each marked with a lambda sign, and fan out to three integrations on the "
        "right: loyalty, ServiceNow, and a data and BI system. Each integration lights up "
        "with a check mark as an event reaches it.",
        "Ticketing, VIP tables and guest lists on serverless, event-driven infrastructure, "
        "wired into loyalty, ServiceNow and a data warehouse.",
        [("item", "Event"), ("lambda", "Function"), ("check", "Delivered")],
        L=12, t0=-10.0, fs=4.5)
    YR = (10, 34, 58)       # block tops, 17 tall, centre row y+8.5
    ITEM = (16, 40, 64)     # event top for each lane
    # tracks
    f.add(G("d", R(30, 17, 8, 3), R(30, 65, 8, 3), R(36, 17, 3, 51), R(36, 41, 22, 3),
            R(91, 41, 5, 3), R(94, 17, 3, 51), R(96, 17, 4, 3), R(96, 41, 4, 3), R(96, 65, 4, 3)))
    f.add(G("k", *[R(40 + 4 * k, 45, 2, 1) for k in range(5)]))   # stepped conveyor teeth
    f.add(f.T(47, 38, "QUEUE", anchor="middle"))
    # events travel behind the function and integration blocks
    flows = [(0, 0), (1, 2), (2, 1), (0, 2), (1, 0), (2, 1)]
    arrivals = {0: [], 1: [], 2: []}
    for n, (src, dst) in enumerate(flows):
        t = 2 + 12 * n
        ys, yd = ITEM[src], ITEM[dst]
        pts = [(0, 22, ys), (t, 22, ys), (t + 6, 35, ys), (t + 9, 35, 40), (t + 15, 58, 40),
               (t + 22, 93, 40), (t + 24, 93, 40), (t + 28, 93, yd), (t + 31, 99, yd)]
        pose = (42 + 10 * n, 40) if n < 2 else (99, yd)
        f.add(f.A(R(0, 0, 5, 5, "b"), pose, mv=pts))
        arrivals[dst].append(t + 31)
    for i, y in enumerate(YR):
        f.add(R(2, y, 28, 17, "g"), box(2, y, 28, 17, "k"),
              f.T(16, y + 11, ("TICKETS", "TABLES", "GUEST LIST")[i], anchor="middle"))
    # functions
    for k in range(3):
        x = 60 + 11 * k
        f.add(R(x, 38, 9, 9, "g"), box(x, 38, 9, 9, "b"), bmp(LAMBDA, x + 2, 40, "b"))
    f.add(f.T(76, 56, "SERVERLESS", anchor="middle"))
    # integrations light up with a check as an event arrives
    for j, y in enumerate(YR):
        ivs = sorted((a, a + 12) for a in arrivals[j])
        merged = []
        for a, b in ivs:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(b, merged[-1][1])
            else:
                merged.append([a, b])
        tg = [(v, w) for a, b in merged for v, w in ((a, 1), (min(b, 99), 0))]
        f.add(R(98, y, 28, 17, "g"), box(98, y, 28, 17, "d"))
        lit = box(98, y, 28, 17, "k") + bmp(CHECK, 120, y + 2, "b")
        f.add(f.A(lit, vis=(0, tg), show=True))
        f.add(f.T(112, y + 13, ("LOYALTY", "SERVICENOW", "DATA / BI")[j], anchor="middle"))
    return f


_NS = [  # item shapes by stage: signal, assignment, packet, draft
    ["#####"] * 5,
    ["#####", "#...#", "#...#", "#...#", "#####"],
    ["#####", ".....", "#####", ".....", "#####"],
    ["#####", "#...#", "#.#.#", "#...#", "#.#.#", "#####"],
]


def newsroom() -> Fig:
    f = Fig(
        "newsroom", "nr", 128, 92,
        "Animated diagram of an automated newsroom built around a beat. Signal blocks come "
        "from the beat and move through four stages, signal, assign, packet and draft, "
        "carried by small blue agent sprites. The block changes shape at each stage. After "
        "the draft stage, a human editor stands in front of the published box. One draft "
        "passes the editor, who marks it with a check, and reaches published. A second "
        "draft is held back and marked with a cross.",
        "Agents watch the beat, assign, report and draft. A person, the executive editor, "
        "approves each item before it publishes.",
        [("check", "Approved"), ("cross", "Held"), ("robot", "Agent"), ("person", "Editor")],
        L=12, t0=-9.0)
    R1, R2 = 12, 60                  # box tops (20 tall)
    X = (2, 48, 94)
    names = (("BEAT", "SIGNAL", "ASSIGN"), ("PACKET", "DRAFT", "PUBLISHED"))
    # tracks (centre of the item row is y0 + 5.5)
    f.add(G("d", R(34, R1 + 4, 14, 3), R(80, R1 + 4, 14, 3), R(34, R2 + 4, 14, 3),
            R(80, R2 + 4, 14, 3), R(109, 32, 3, 14), R(17, 45, 95, 3), R(17, 48, 3, 12),
            R(80, 47, 0, 0)))
    f.add(bmp(ARROW_R, 40, R1 + 3, "k"), bmp(ARROW_R, 86, R1 + 3, "k"),
          bmp(ARROW_R, 40, R2 + 3, "k"), bmp(ARROW_D, 16, 51, "k"))
    for row, y0 in enumerate((R1, R2)):
        for c in range(3):
            x = X[c]
            f.add(R(x, y0, 32, 20, "g"), box(x, y0, 32, 20, "k"),
                  f.T(x + 16, y0 - 3 if row == 0 else y0 + 28, names[row][c], anchor="middle"))
            if (row, c) not in ((0, 0), (1, 2)):
                f.add(bmp(ROBOT_C, x + 3, y0 + 11, "b"))
    f.add(G("d", *[R(6 + 7 * k, R1 + 11, 5, 5) for k in range(3)]))      # beat signals
    f.add(bmp(PERSON, 83, 69, "k"), f.T(86, 90, "EDITOR", anchor="middle"))
    # item paths: (kind, duration %, x, y); item top-left, row y = y0 + 3
    ya, yb, yz = R1 + 3, R2 + 3, 44
    steps = [("m", 7, 62, ya), ("h", 3), ("m", 7, 108, ya), ("h", 3), ("m", 5, 108, yz),
             ("m", 12, 16, yz), ("m", 3, 16, yb), ("h", 3), ("m", 7, 62, yb), ("h", 3)]
    def build(t0, ending):
        t, x, y = t0, 16, ya
        pts, holds = [(0, x, y), (t, x, y)], []
        for st in steps + ending:
            t += st[1]
            if st[0] == "m":
                x, y = st[2], st[3]
            else:
                holds.append(t)
            pts.append((t, x, y))
        return pts, holds
    # A passes the editor and is published; B is held back
    ptsA, hA = build(2, [("m", 8, 108, yb)])
    ptsB, hB = build(30, [("m", 3, 73, yb)])
    for pts, holds, pose, last in ((ptsA, hA, (108, yb), 3), (ptsB, hB, (73, yb), 3)):
        shapes = ""
        sw = [holds[0], holds[1], holds[2]]
        for k in range(4):
            tg = []
            if k > 0:
                tg.append((sw[k - 1], 1))
            if k < 3:
                tg.append((sw[k], 0))
            init = 1 if k == 0 else 0
            shapes += f.A(bmp(_NS[k], 0, 0, "b"), vis=(init, tg), show=(k == last))
        f.add(f.A(shapes, pose, mv=pts))
    tA = ptsA[-1][0] - 8 + round(8 * (84 - 62) / 46)
    tB = ptsB[-1][0]
    f.add(f.A(bmp(CHECK, 84, 54, "b"), vis=(0, [(tA, 1), (tA + 18, 0)]), show=True))
    f.add(f.A(bmp(CROSS, 73, 53, "p"), vis=(0, [(tB, 1)]), show=True))
    return f


_BUILDERS = {
    "hero-loop": hero_loop, "knowledge-base": knowledge_base, "self-aligning": self_aligning,
    "agent-harness": agent_harness, "confidence-gate": confidence_gate, "scorecard": scorecard,
    "relocate": relocate, "platform-stack": platform_stack, "engagement-path": engagement_path,
    "verdict-meter": verdict_meter, "leaderboard": leaderboard, "eras": eras,
    "lost-sprite": lost_sprite, "chat-room": chat_room, "page-audio": page_audio, "venue-system": venue_system, "newsroom": newsroom,
}


def render(name: str) -> str:
    """One ``<figure class="px">`` for ``name``. Raises KeyError if unknown."""
    if name not in _BUILDERS:
        raise KeyError(name)
    return _BUILDERS[name]().figure()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in _BUILDERS:
        print(render(sys.argv[1]))
    else:
        print("usage: arcade_pictograms.py <name>")
