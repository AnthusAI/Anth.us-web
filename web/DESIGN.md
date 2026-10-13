# Anth.us design system: "Arcade, corporate"

This replaces the Gatsby-parity design (see DESIGN-PARITY.md, now historical).
The goal: a professional, minimal AI-engineering firm site with an 80s arcade
accent. No generated illustrations on the main pages; animated pixel
pictograms carry the visuals. The brand lives in three things, so keep them
strong: the **colours**, the **blocky type**, and the **pixel grid**.

Taste rule: corporate first, arcade second. One arcade wink per screen, not
ten. No "INSERT COIN", no fake CRT curvature, no neon glow blur, no emoji.

## 1. Colour tokens

Use these exact brand values. Only the neutrals are new.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#fbfdff` | `#0e0b16` | page |
| `--panel` | `#f1f9fe` (brand ice) | `#17121f` | bands, cards |
| `--panel-2` | `#e4f2fc` | `#211a2c` | hover, inset |
| `--line` | `#d6e6f2` | `#2e2540` | 1px rules, card borders |
| `--ink` | `#1b1426` | `#f3eef8` | body text |
| `--ink-2` | `#4a4157` | `#b9aec8` | secondary text |
| `--pink` | `#dc5497` | `#ff57b4` | brand primary, buttons, pictogram accent |
| `--pink-hot` | `#ff57b4` | `#ff87c3` | highlight, hover |
| `--pink-deep` | `#9b165d` | `#ff87c3` | links, eyebrows (AA on bg) |
| `--pink-shadow` | `#620e32` | `#000000` | hard pixel shadow under buttons |
| `--blue` | `#0389d7` | `#3fb2f7` | second accent, pictogram "machine" colour |
| `--grad` | `linear-gradient(90deg,#d03382,#9b165d 50%,#0389d7)` | same | brand bar, rare large accents |
| `--on-pink` | `#ffffff` | `#ffffff` | text on pink |

Footer is the dark band in both modes: `#150f20` with `--ink` `#f3eef8`.
`color-scheme: light dark` on `:root`. Mode follows `prefers-color-scheme`
only; there is no toggle UI.

Contrast: body text and links must pass WCAG AA in both modes. `--pink` on
`--bg` is only for large display text, buttons (white text on pink) and
pictogram fills, never for small body text; small coloured text uses
`--pink-deep`.

## 2. Type

Google Fonts, one `<link>` with `preconnect`, `display=swap`:
`Jersey 25`, `Jersey 25 Charted`, `Jersey 10`, `Geist` (400, 500, 600),
`Geist Mono` (400, 500).

| Role | Font | Notes |
|---|---|---|
| Display (h1, h2, big numbers) | `Jersey 25` | weight 400 only, never faux bold; `letter-spacing: .01em`; `line-height: .95` for h1 |
| Score numerals, hero-scale accent words | `Jersey 25 Charted` | the variant with visible block gaps; use sparingly |
| Eyebrows, nav, buttons, labels, pictogram text | `Jersey 10` | uppercase, `letter-spacing: .08em` |
| Body, UI copy | `Geist` | 400; 500 for emphasis; `line-height: 1.6` |
| Code, metadata (dates, tags) | `Geist Mono` | |

Fluid scale (clamp, rem-based):
`--step-5` h1 `clamp(3rem, 2rem + 4.5vw, 7.5rem)`;
`--step-4` h2 `clamp(2.25rem, 1.6rem + 2.4vw, 4.25rem)`;
`--step-3` h3 `clamp(1.6rem, 1.3rem + 1vw, 2.25rem)`;
`--step-1` lead `clamp(1.15rem, 1rem + .5vw, 1.45rem)`;
body `1.0625rem`. Root font-size steps up on big screens:
`100%`, `106.25%` at ≥96rem, `112.5%` at ≥120rem, `125%` at ≥160rem.

## 3. Layout and wide screens

- Container: `width: min(100% - 2 * var(--gutter), var(--max))`, centred.
  `--gutter: clamp(1.25rem, 4vw, 4rem)`. `--max: 76rem`; `92rem` at
  ≥100rem viewport; `120rem` at ≥140rem.
- Reading column for prose: `max-width: 68ch`.
- Grids are intrinsic: `repeat(auto-fill, minmax(min(100%, 18rem), 1fr))`, so
  cards go 1 → 2 → 3 → 4 → 5 columns as width allows. Never hard-cap a
  listing at two columns.
- Hero is split (text | pictogram) from 64rem up; the pictogram column grows
  with the viewport (`grid-template-columns: minmax(0, 6fr) minmax(0, 7fr)`).
- Sections are separated by space (`clamp(4rem, 8vw, 9rem)`) and the odd
  full-bleed `--panel` band, not by boxes inside boxes.
- Section header pattern: an eyebrow line `01 / WHAT WE DO` (Jersey 10,
  `--pink-deep`, with a 2rem pixel rule before it), then an h2, then an
  optional lead. On ≥80rem the header sits in a left column (4/12) and the
  section content in the right column (8/12).

## 4. Pixel details (the arcade layer)

- **Stepped corners**: buttons, cards, tags and the logo mark use a
  `clip-path` polygon with 4px notched corners (`--notch: 4px`), never
  `border-radius`. Rounded corners are banned site-wide.
- **Hard shadow**: the primary button has `box-shadow: 4px 4px 0
  var(--pink-shadow)` (via a wrapper or `filter: drop-shadow` so clip-path
  does not eat it); on `:active` it moves 4px down-right and the shadow goes
  to 0 ("pressed").
- **Pixel rule**: the brand gradient as a 4px bar at the top of the header,
  rendered in 8px steps (`background-size` with hard stops), not a smooth fade.
- **Pixel grid background**: the hero has a faint 16px grid
  (`--line` at 40% opacity), fading out toward the bottom with a mask.
- **Cursor**: the hero h1 ends with a block cursor in `--pink` that blinks
  with `steps(1)`. Disabled under `prefers-reduced-motion`.
- **Motion** is stepped: `animation-timing-function: steps(n)` for pictogram
  movement so it reads as sprites, not tweens. Hover states snap (no
  transitions longer than 80ms).

## 5. Components

- **Header**: sticky, `--bg` at 88% with `backdrop-filter: blur(8px)`, 1px
  `--line` bottom border, gradient pixel rule above. Left: logo (pixel "A"
  mark, 6x6 blocks, + "ANTHUS" in Jersey 25). Right: nav in Jersey 10
  uppercase; last item is a small primary button "START A PROJECT" →
  `/engage/`. Below 60rem the nav collapses into a disclosure (`<details>`
  or a button) with a full-width panel; no JS framework.
- **Buttons**: `.btn` (pink fill, white Jersey 10 text, notched, hard
  shadow) and `.btn--ghost` (1px `--ink` outline, notched, no shadow).
  Arrow glyph `→` drawn as text.
- **Stat strip ("score bar")**: a row of 4 cells divided by 1px `--line`;
  each has a number in Jersey 25 Charted (`--step-4`, `--pink`) and a label in
  Jersey 10. Wraps to 2x2 then 1 col.
- **Card**: `--panel` fill, 1px `--line` border, notched corners, padding
  `clamp(1.25rem, 2vw, 2rem)`. Optional pictogram slot at top. Title in
  Jersey 25 `--step-3`. Hover: border becomes `--pink`, title gets the pink
  underline in 2px steps. No images.
- **Article card**: no cover image. Mono date + tag line, Jersey 25 title,
  2–3 line excerpt clamp, "Read →".
- **Eyebrow**: see 3.
- **Footer**: dark band `#150f20`, gradient pixel rule on top, columns
  (Company, Work, Platform, Writing, Elsewhere), wordmark, the
  `site_env.footer_note()` line.

## 6. Pictograms

Inline SVG generated by `web/arcade_pictograms.py` (one function per
pictogram returning an `<figure>` string). Styled by CSS in the site sheet.

- **Pixel grid**: every coordinate on an integer grid; cell = 1 viewBox unit
  for sprites, typically `viewBox="0 0 64 40"`-ish; `shape-rendering:
  crispEdges`; only `<rect>`s and pixel-built glyphs. No curves, no
  strokes except 1-unit rects.
- **Colours by role, through CSS variables only** (so dark mode works):
  `--px-ink` (= `--ink`, people, outlines), `--px-pink` (= `--pink`,
  decisions / the model), `--px-blue` (= `--blue`, data / machines),
  `--px-dim` (= `--line`, idle cells, tracks). No hard-coded hex in SVG.
- **Marks, not colour**: state is always carried by a pixel glyph: ✓ (check,
  5x4 px), × (cross, 5x5 px), ? (question, 3x5 px). Colour reinforces. Each
  pictogram has a `<figcaption>` with a drawn mini legend (glyph + word)
  and one plain sentence. `role="img"` + `aria-label` narrates it with counts
  in words. (Ryan is colourblind: never colour alone.)
- **Motion**: CSS `@keyframes` with `steps()`; loops of 4–8 s; nothing
  flashes faster than 3 Hz. Animations run only while on screen: a tiny shared
  script adds `.is-live` via IntersectionObserver; CSS uses
  `animation-play-state: paused` unless `.is-live`. Under
  `prefers-reduced-motion: reduce`, no animation; show the most informative
  final frame.
- Labels inside SVG in Jersey 10, ≥11px rendered at 375px wide.

## 7. Images

Main pages (home, about, solutions, engage, platform, decision models,
benchmarks, research, reading, 404) use no raster illustrations. Article
bodies keep their images (they are content). Listings use no cover images.

## 8. Voice

Anthus brand voice, first person plural, plain and specific, numbers over
adjectives. Short sentences. No hype words ("revolutionary", "cutting-edge",
"unlock", "leverage"). Every claim on the page already exists in the current
copy or the content repo; do not invent clients, numbers or certifications.
