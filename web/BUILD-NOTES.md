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
this script monkey-patches the renderer's public surface and a silent upstream
change there breaks the build with no commit in this repo to blame.

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
