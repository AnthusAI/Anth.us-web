# Building the Anth.us Papyrus/Markus staging site

`build_via_papyrus.py` imports Papyrus's `papyrus_content.markus_renderer`
(`build.py` and `shell.py` — `build_markus_site`, `SiteChrome`, `NavItem`,
`render_page`, `convert_fragment`, `_read_title`, `_css_version`,
`_build_nav_items`). That module **is** present in `AnthusAI/Papyrus` on
`develop` and `main`; the note in `Pilobol.us/web/BUILD-NOTES.md` claiming it
is missing is stale.

```bash
git submodule update --init --recursive
pip install "git+https://github.com/AnthusAI/Markus@v0.5.1" "Pillow>=10,<12" "PyYAML>=6"
PAPYRUS_ROOT=/path/to/Papyrus python3 web/build_via_papyrus.py
python3 bin/dev-server.py --port 8080
```

`PAPYRUS_ROOT` defaults to `../Papyrus`. The Amplify build pins Papyrus by
commit (`PAPYRUS_PIN` in `amplify.yml`) rather than tracking a branch, because
this script builds on the renderer's public surface (`SiteChrome` hooks,
`FragmentTransform`, `ImagePipeline.wrap`) and a silent upstream change there
breaks the build with no commit in this repo to blame.

**Do not try to preview from a cloud session.** Nothing bound inside a Claude
Code cloud container is reachable from a browser — no port forwarding, no
preview URL. Run the dev server on a local machine.

## What the build does, in order

1. **Discover** (`anthus_content.discover`) — walk the content submodule for
   `*.mdx`, honoring the same ignore list as `gatsby-config.mjs`
   (`README.md`, `*.IMAGE.*`, `*.STYLE-NOTES.*`).
2. **Classify** (`anthus_content.Collections`) — reproduce
   `gatsby-node.js`: a node is a *platform* node if
   `content_type: platform-product` or it lives under `platform/`; everything
   else is a *blog* node. Articles, posts, and solutions are then filtered out
   of the blog set the way `blog.jsx`, `posts-list.jsx`, and
   `ai-solutions.js` filter them.
3. **Normalize** (`anthus_mdx.normalize_body`) — strip MDX imports, convert
   `<BlogImage>`/`<Citation>`/`<CitationsList>`, collapse `<figure>`/`<img>`
   into `:::figure`, convert HTML tables to GFM, rewrite inline HTML to
   Markdown, and leave tag-shaped prose alone.
4. **Generate pages** (`anthus_pages`) — the homepage, `about`,
   `ai-solutions`, `ryan`, `404`, the platform overview and per-product chrome,
   the articles archive, the paginated posts listings, and the tag pages.
5. **Stage images** (`anthus_content.ImageIndex.stage`) — copy only referenced
   images, downscaling anything wider than 1600 px.
6. **Render** — Papyrus's `build_markus_site` over `web/staging`, plus
   `build_standalone()` for the depth-0 bespoke pages.
7. **Finish** — link rewriting and social meta (in the `render_page` wrapper),
   `/blog/<slug>.html` redirect stubs, `robots.txt`, `sitemap.xml`, and the
   parity report.

## Troubleshooting

**`Unclosed directive '<name>' starting at line N`** — almost always a leaf
directive written with three colons. `metric` is a leaf: `::metric{…}`, no
closing fence. Container directives (`figure`, `card`, `card-grid`, `callout`,
`two-up`, `column`, `pull-quote`, `details`, `aside`, `tabs`, `step-list`,
`timeline`) open with `:::` and close with `:::`.

**`Markus 0.5.1 required for static builds; got …`** — Papyrus pins the Markus
CLI version in `markus_renderer/security.py`. Install the exact pin.

**A page shows literal `&lt;div&gt;`** — raw HTML reached Markus. Static
builds never pass `--allow-html`, so the fix belongs in
`anthus_mdx._convert_block_html`, not in a build flag.

**Two `<h1>`s on a page** — the front-matter `title` already renders one.
Don't also write `# …` at the top of the body.

**`markus validate` / unknown directive** — do not emit a directive the pinned
Markus does not register. `markus convert` fails the entire page, not just the
block.

## Site origin and canonical URLs

`SITE_ORIGIN` is derived from Amplify's `AWS_APP_ID` / `AWS_BRANCH` at build
time, falling back to `$ANTHUS_SITE_ORIGIN` or `http://localhost:8080`. It is
deliberately **not** `https://anth.us`: canonical and `og:url` must not claim
to be production while this is a staging copy. Set `ANTHUS_SITE_ORIGIN` if you
need absolute URLs in a local build.

## Listing visuals and the `pictogram:` front-matter field

Every listing card (articles, posts, research, reading, tags, solutions, the
homepage writing section) has a 16:10 visual slot: the item's `pictogram:`
(inline animated SVG, any name in `arcade_pictograms.NAMES`; an unknown name fails
the build), else its `preview_image` (lazy, with width/height), else a
first-letter tile. An item with `pictogram:` also shows it at the top of its
article header.

An inline SVG cannot be an og:image, so each pictogram has a committed PNG
(1200x630, light mode, static frame) in `web/assets/site/pictograms/<name>.png`.
The build never renders them; it reads them: an item with `pictogram:` and no
`preview_image` uses its PNG for `og:image` / `twitter:image`. After adding or
changing a pictogram, regenerate and commit them:

    python3 bin/render-pictogram-pngs.py            # all
    python3 bin/render-pictogram-pngs.py self-aligning   # one

(Needs Node with puppeteer, default `~/Projects/Pilobol.us/node_modules/puppeteer`,
and Chrome; override with `PUPPETEER_DIR` / `PUPPETEER_EXECUTABLE_PATH`.)

## Image placement (articles and posts)

A picture goes exactly where the author puts the `::image{}` directive; its `layout`
decides the look. Everything is measured against the **text column** (68ch, the width of
the paragraphs), so a centred picture is centred on the text above and below it.

| `layout=` | Look | Notes |
| --- | --- | --- |
| `center-small-image` | **small**: centred, 60% of the text column | used by 48 images |
| `centered`, `center-full-image` | **medium**: centred, up to 44rem (never wider than the column) | 32 + 6 |
| `full` | **full**: the whole article width, left edge on the text column | 112 |
| `right`, `right-aligned` | **inset right**: floated right, 40% of the text column, right edge on the text column, text wraps; full width, stacked, on phones | 20 + 2 |
| (none) | medium | |

Legacy wrappers still work and map onto the same looks: `<div class="center-small-image">`
and `box-*` styled divs are small/medium, `float:right` styled divs are inset right;
`<p|div|figure class="center-full-image">` around an image only add a `figcaption` and keep the
layout's own look. There is no inset-left (no content uses it).

Authoring examples (the directive's position in the text is the placement in the page):

```
::image{src="images/x.png" layout="center-small-image" alt="..."}   <- small, centred

::image{src="images/x.png" layout="full" alt="..." caption="..."}   <- full width

First paragraph of the article, with the image floated beside it.

::image{src="images/x.png" layout="right" alt="..."}                <- inset right, wraps the
                                                                       paragraphs that follow
Second paragraph...
```

"After the first paragraph" is simply writing the directive after that paragraph; an inset-right
picture placed before a paragraph floats beside that paragraph and the ones after it.
A heading (`##`) clears the float, so an inset never spills past its section.
The markup is `.img.img--small|medium|full|inset-right` (from `anthus_dom.anthus_image_wrap`,
mapping in `PLACEMENT_BY_LAYOUT` / `WRAPPER_PLACEMENT`); the CSS is in `web/css/arcade.css`.
