# WIP — exact design parity with the production Anth.us site

**This branch is mid-refactor and the build does NOT currently run.** It was
wound down deliberately, not abandoned. Read this before touching anything.

Branch: `feature/exact-design-parity` (worktree `../Anth.us-Papyrus-design`).
Companion Papyrus branch: `feature/markus-layout-parity`.

## The goal

The port's front end must look **exactly** like the existing production
Anth.us site. Ryan: *"We want the front end design to be exactly the same as
the old site."* Then, later: *"Yes, fix Markus"* — where Markus's markup or
design language blocks parity, the fix belongs upstream in Papyrus/Markus
(publication-neutral, config-driven), **not** in regex surgery here.

## The diagnosis (established, do not re-derive)

The two sites share **zero** CSS class names.

| | Production | This port, before this branch |
| --- | --- | --- |
| Classes | `index-module--listItem--06e6d`, `blog-post-preview`, `gatsby-image-wrapper`, `clear-float`, `date`, `button`, `logo` | `markus-card`, `markus-document`, `markus-site-masthead`, `markus-header`, `markus-lede` |
| CSS | 33KB SCSS → 26,104-byte compiled bundle | hand-written 12,241-byte `web/css/anthus-theme.css` |

Ground truth is `/Users/home/Projects/Anth.us/public/` — a real 2026-09-24
Gatsby production build, 243 rendered HTML pages plus
`styles.04b540856f53bb5e70f2.css`. **Treat it as read-only and precious.**

## What is DONE and believed correct

### 1. The stylesheet is now the real one, compiled from source
`bin/build-theme-css.py` regenerates `web/css/anthus-theme.css` (28,327 bytes)
from the actual Anth.us style sources:

* `src/components/layout.scss` via Dart Sass from `../Anth.us/node_modules`
  (it `@import`s `priority-plus`, so the `.p-plus*` nav rules come with it);
* `src/components/index.module.css` and `platform.module.css`, with local
  class names rewritten to Gatsby's hashed names using the mapping committed
  in `web/css/css-module-hashes.json`. Those hashes are produced inside
  webpack and are not reproducible outside it, so they are extracted once from
  a shipped bundle (`--extract-hashes`) and read by **both** the CSS generator
  and `anthus_dom.css_modules()` — CSS and DOM cannot drift apart;
* `gatsby-plugin-image`'s inline stylesheet, pulled from
  `node_modules/gatsby-plugin-image/gatsby-ssr.js`. It is *not* in
  `public/styles.*.css` (the plugin injects it per page) but
  `.gatsby-image-wrapper` is load-bearing for every floated/centred article
  image.

**Verified**: `python3 bin/build-theme-css.py --anthus ../Anth.us --verify
/Users/home/Projects/Anth.us/public/styles.04b540856f53bb5e70f2.css` prints
`selector sets are identical` (291 selectors each). A declaration-level diff
showed 45 of 287 shared selectors differing, and every one was a cssnano
normalisation of an equivalent value (`flex:1 1` vs `flex:1`, `transparent`
vs `rgba(0,0,0,0)`, `#639` vs `#663399`, `calc(a*2)` vs `calc(2*a)`).

The result is committed because an Amplify CI build has neither Dart Sass nor
the Anth.us checkout.

### 2. `web/anthus_dom.py` — the production DOM layer (new)
* `render_shell()` — the `.layout > header + .wrapper>main + footer` envelope
  from `layout.js`, including the `#___gatsby` wrappers, the Google Fonts link
  (`Jersey 25` / `Geist Mono` / `Montserrat`), and the `{title} | Anthus`
  title template.
* `_header_html()` — `header.js` rendered: `header > .content > a.logo` plus
  `.menu > nav > ul.js-p-target`, with Gatsby's exact-match `active` class.
* `FOOTER_HTML` — the **real** `anthus-footer` component output, captured into
  `web/anthus_footer.html` (7,062 bytes) from `public/posts/index.html`. It is
  styled entirely with inline `style=` attributes, so static markup is
  pixel-identical; the only edit is the logo `<img>`.
* `image_html()` / `hero_image_html()` — `gatsby-plugin-image`'s constrained
  and FULL_WIDTH markup shapes, with real pixel dimensions read via Pillow.
* `css_modules()` — the hashed CSS-module class names.
* Sentinel encode/decode, `article_fragment()`, `plain_fragment()`,
  `assert_no_markus_classes()`.

### 3. `web/anthus_mdx.py` — the six gaps, addressed at the source
* `<mark>` (204 uses) now round-trips as a sentinel pair instead of being
  flattened to `**bold**`.
* Inline `<svg>` (2 uses) round-trips verbatim instead of being dropped.
* A table using `colspan`/`rowspan` is passed through verbatim instead of
  being flattened into the wrong shape.
* `render_image_directive()` now carries the authored `className`
  (`right` ×20, `full` ×114, `centered` ×32, plus 89
  `<figure className="center-full-image">`), which `:::figure{}` could not
  express and which is what `layout.scss` uses to float and size images.

### 4. `priority-plus` nav — the real library
`web/assets/priority-plus.js` is priority-plus 1.5.1 (ISC) vendored verbatim
from `../Anth.us/node_modules`, and `web/assets/site-nav.js` initialises it
against `ul.js-p-target` with the same `innerToggleTemplate` production uses.
The breakpoint-hamburger approximation is gone. The `.p-plus*` CSS is already
in the compiled theme.

### 5. Screenshot harness
`bin/shoot.js` (Puppeteer) + `bin/compare.py` (Pillow). Self-tested against
`Anth.us/public` served on 8081: same-directory comparison reports
pixel-identical; two independent runs differ by one antialiasing pixel.

Two environment facts: **Puppeteer is at
`/Users/home/Projects/Pilobol.us/node_modules/puppeteer` (v25.10.0), not under
Anth.us**, and its managed Chrome was never downloaded — `shoot.js` resolves
the Playwright-managed `chrome-headless-shell` instead. A naive
`puppeteer.launch()` fails on this machine.

```bash
python3 -m http.server 8081 --directory /Users/home/Projects/Anth.us/public &
node bin/shoot.js --base http://localhost:8081 --out /tmp/shots/old --pages pages.json --widths 1440,390
node bin/shoot.js --base http://localhost:8082 --out /tmp/shots/new --pages pages.json --widths 1440,390
python3 bin/compare.py /tmp/shots/old /tmp/shots/new --diff-out /tmp/shots/diff
```

## What is HALF DONE — pick up here

### `web/anthus_pages.py.new` (717 lines, parses, not yet wired)
The rewrite of the page templates from Markdown generators to **HTML**
generators emitting the production DOM. `.new` so it is not importable yet.
Written and believed right (all against reference DOM dumps):
`_blog_item`, `_posts_item`, `solutions_list`, `_hero`, `homepage`,
`articles_index`, `posts_pages`, `tag_pages`, plus the carried-over platform
constants.

Still to write (listed as TODO at the end of that file):
`_platform_card`, `platform_index`, `platform_product_head`/`_tail`, and thin
wrappers delegating `about_page` / `ai_solutions_page` / `ryan_page` /
`not_found_page` to `anthus_page_html`.

**Note the API changes** vs the current `anthus_pages.py`: generators return
HTML (not Markdown), `posts_pages` keys are bare names without `.md`,
`tag_pages` returns `{slug: (label, html)}`, and hrefs are emitted in
**production shape** (`/blog/<slug>/`, `/posts/2/`, `/platform/`) to be
rewritten by `build_via_papyrus._rewrite_internal_links`. That last choice is
deliberate: it keeps one link mapper and keeps the emitted DOM directly
comparable to `Anth.us/public/`, and it should survive the concurrent URL
agent's changes.

### `web/anthus_page_html.py`
Was being generated by a sub-agent from the reference pages when this session
wound down; see that sub-agent's state in the Kanbus issue. It must expose
`set_image_renderer(render)`, `about_html()`,
`ai_solutions_html(featured=, portfolio=, integrations=)`,
`ryan_html(portfolio=, integrations=)`, `not_found_html()`.

### `web/build_via_papyrus.py` — NOT YET TOUCHED. This is why the build breaks.
`anthus_mdx` now emits image/mark/svg sentinels that nothing decodes, so the
pipeline is inconsistent. The wiring still to do:

1. Stop monkeypatching `markus_shell.render_page`; use the new Papyrus
   `SiteChrome` seams (`render_masthead` / `render_body` / `body_class` /
   `stylesheets` / `head_html` / `title_template` / `asset_root`) from
   `feature/markus-layout-parity`.
2. Pass a `FragmentTransform` so Markus decodes the sentinels and maps its
   structural classes, rather than doing it with regexes here.
3. `build_markus_site(..., vendor_css=False)` — this build ships a complete
   stylesheet and must not link Markus's 27KB vendor CSS.
4. Drop `"posts"` and `"tags"` from `sections=`; write those pages directly
   from the HTML generators. Keep `"platform"` for product bodies.
5. Omit `title`/`description` from staged article front matter so Markus does
   not render its own `<header class="markus-header">`; build the production
   `<div class="heading">` (h1 + `.date` + `.authors`, with `.draft-overlay`
   first for drafts) from `anthus_dom.ArticleHeading` instead. This removes
   the need for the `_MARKUS_HEADER` / `_MARKUS_DRAFT` / `_MARKUS_BYLINE_P`
   regexes in `anthus_dom`, which exist only as a fallback.
6. Call `anthus_dom.set_asset_roots(...)` before rendering (image dimensions)
   and `assert_no_markus_classes()` on every page as a build gate.
7. Update the parity report counters: `report.svgs`, `report.span_tables`
   replaced `dropped_svg` and the cell-span drop.

## Findings worth keeping

* **Production platform-product pages are broken.** In the reference build,
  `/platform/<product>/index.html` renders with **no chrome at all** — no
  `.layout`, no header, no footer, just the MDX body. The same is true of
  `/solutions/<x>/` and of the bare-slug article duplicates
  (`/ai-agents/index.html` has no chrome; `/blog/ai-agents/index.html` does).
  So for those routes there is **no usable visual reference**; implement what
  `platform-product.jsx` intends and say so.
* Tag pages DO have chrome; target DOM is
  `<div><h1>Articles tagged with: X</h1><ul><li><a …></li></ul></div>`.
* `404.html` has full chrome; body is just `<h1>` + `<p>`.
* Production emits React artefacts worth reproducing verbatim rather than
  "fixing": `class="… undefined"` where a `className` prop is absent, a
  trailing space in an unfeatured solution item's class list, `<div
  class="blog-post-preview">` wrapping an `<li>`, and `<p class="…"><p>…</p></p>`
  nesting from `dangerouslySetInnerHTML` excerpts.
* The production bundle defines `--color-background-secondary`,
  `--color-text-light` and `--line-height-loose` nowhere, so every rule using
  them is inert on the live site too. Do not "fix" that.
* Homepage Recent Articles uses the raw front-matter date in a `<div>`;
  `/blog/` uses the formatted date in a `<p>`. Not a style choice — reproduce
  both.

* **Open parity risk.** Production's
  `.responsive-float-right-image{float:right;…width:40%}` targets the `<img>`
  itself, but `anthus_dom.image_html()` puts `class_name` on the wrapping
  `div.gatsby-image-wrapper`. Routing the about / ai-solutions images through
  it changes the DOM shape — probably visually equivalent, definitely not
  byte-identical. Check it with `bin/compare.py`.
* `/ryan/` has **three** `index-module--list--fb407` lists, not two, and the
  first two are adjacent with zero characters between them — so a single
  `{portfolio}` hole has to span both. Matching the holes needs
  `<ul>`/`</ul>` depth counting, because the lists contain nested plain
  `<ul>`s.
* On `/about/`, `/ai-solutions/`, `/ryan/` and `/404` the static regions
  contain only **three** plain `<img>` elements in total (`ryan-porter.png`,
  `ai-software-solutions.png`, `Anthus AI Application Lifecycle.png`, all
  already in `web/assets/site/`); every gatsby-plugin-image block falls inside
  a dynamic hole. Production srcs there are `/assets/images/…`, not
  `/static/<hash>/…`.

## Not verified — do this first

* **No page has been rendered or screenshotted on the new build.** Every
  parity claim above is structural (selector-set and DOM comparison against
  the reference), not visual. Nothing here may be reported as visually
  verified.
* The build has not been run since the `anthus_mdx` changes.
* Nothing has been deployed; staging still serves the previous build.
* The rebase onto the concurrent URL agent's `feature/anthus-papyrus-port`
  has not been attempted.
