# Live anth.us DOM changes the Papyrus port must apply

Compiled 2026-10-03 against production as deployed by Amplify job #258
(AnthusAI/Anth.us `96ac29c241a1b75373d13f21268afcfb681bf5e5`, content submodule
`AnthusAI/anthus-site-content` `4b80f02431d0f8f59fb08a8cc7961d07cdbe789b`).

* BEFORE = the stale reference build `/Users/home/Projects/Anth.us/public/`
  (2026-09-24 Gatsby build; the port was wired to this).
* AFTER  = `/Users/home/Projects/Anth.us-live/public/`, a build of the deployed
  commit, proven equal to production (see "Provenance" at the end). The
  authoritative raw copies are in `/Users/home/Projects/Anth.us-live-mirror/html/`.
* Snippets are copied from built HTML. `<GatsbyImage class="X"/>` stands for the
  unchanged gatsby-plugin-image wrapper (`div[data-gatsby-image-wrapper].gatsby-image-wrapper.gatsby-image-wrapper-constrained.X`
  plus sizer/placeholder/picture); only the extra class `X` matters here. React's
  `<!-- -->` text separators are removed. Everything else is verbatim.
* The stylesheet already contains every rule these changes need
  (`web/css/anthus-theme.css`, regenerated from the live bundle; selector set
  identical to `styles.a4f6abf91bb86f9d4c6f.css`). The work left is markup.

Short list, in order of how much of the site each touches:

1. Header menu: 5 links -> 7, each link now has title + subtitle spans.
2. Every listing (/blog/, /posts/, tag-less collections) is now one template,
   `collection.jsx`: 4 featured `ul.blog` items, then `<h2>Earlier</h2>` and an
   8-card `platform-module--grid` (research-cards), with new `/<base>/page/N/` URLs.
   `/blog/` was a single unpaginated page and `/posts/` used the home-page row
   markup; both are different now.
3. Featured image class `right` -> `featured` (blog previews, home "Recent Articles").
4. Home page: new hero copy + `heroProof` line, hero button is a `<Link to="/engage">`,
   Case studies moved before "How we work" and became bullet facts, B0rd section gone,
   Recent Posts thumbnail moved first and gained a class.
5. Article: `div.repository` line in the heading block; `EngageCTA` box after the
   body for posts tagged `client-acquisition`; head gets `og:type=article` and
   JSON-LD.
6. New pages `/research/`, `/reading/`, `/engage/`, `/decision-models/`, and the
   8 bespoke pages regenerated (`anthus_page_html`, new `ai_solutions_html` holes).
7. `/posts/N/` is now a meta-refresh stub to `/posts/page/N/`.
8. Platform page: Chatticus/Antharchy text and one recipe card removed (content only).
9. `<head>`: analytics opt-out script, sitemap link, new meta descriptions.

Nothing outside `<header>` and `<main>` changed: the `div.layout > header + div.wrapper > main + footer`
shell and the footer are byte-identical (modulo the same content) between BEFORE and AFTER
on `/`, `/about/`, an article and `/404.html`. `web/anthus_footer.html` therefore
needs no change (verified by diffing the live footer against it; the only difference is
the logo `<div class="gatsby-image-wrapper">` that the port deliberately swaps for a plain `<img>`).

---------------------------------------------------------------------------

## 1. Header  (anthus_dom._header_html)

Source: `gatsby-config.mjs` `menuLinks` gained a `description`; `layout.js` queries it;
`header.js` renders it.

`src/components/header.js` diff:

```diff
-                    {link.name}
+                    <span className="menu-title">{link.name}</span>
+                    {link.description && (
+                      <span className="menu-subtitle">{link.description}</span>
+                    )}
```

BEFORE (`/`):

```html
<header><div class="content"><a aria-current="page" class="logo active" href="/">Anthus </a><div class="menu"><nav><ul class="js-p-target"><li><a href="/ai-solutions/">AI Solutions</a></li><li><a href="/platform/">Platform</a></li><li><a href="/about/">About</a></li><li><a href="/blog/">Articles</a></li><li><a href="/posts/">Posts</a></li></ul></nav></div></div></header>
```

AFTER (`/`), complete:

```html
<header><div class="content"><a aria-current="page" class="logo active" href="/">Anthus </a><div class="menu"><nav><ul class="js-p-target"><li><a href="/ai-solutions/"><span class="menu-title">AI Solutions</span><span class="menu-subtitle">What we build and run for clients, with the case studies.</span></a></li><li><a href="/platform/"><span class="menu-title">Platform</span><span class="menu-subtitle">The components behind the work: Primus, Kanbus, and the rest.</span></a></li><li><a href="/research/"><span class="menu-title">Research</span><span class="menu-subtitle">Experiments on how decision models behave, with the numbers.</span></a></li><li><a href="/reading/"><span class="menu-title">Reading List</span><span class="menu-subtitle">Papers and books we keep coming back to, one note each.</span></a></li><li><a href="/about/"><span class="menu-title">About</span><span class="menu-subtitle">Who we are, and the track record since 2007.</span></a></li><li><a href="/blog/"><span class="menu-title">Articles</span><span class="menu-subtitle">Long-form pieces on classifiers, agents, and the economics of AI.</span></a></li><li><a href="/posts/"><span class="menu-title">Posts</span><span class="menu-subtitle">Short takes on what shipped this week.</span></a></li></ul></nav></div></div></header>
```

Order is: AI Solutions, Platform, Research, Reading List, About, Articles, Posts.
Active state is unchanged in kind: on `/research/` the link renders
`<a aria-current="page" class="active" href="/research/">` (exact-match only; on an
article or `/posts/page/2/` nothing is active, and the logo is `class="logo"` without
`active`). `.menu-subtitle` is `display:none` in the desktop bar and only shows inside the
overflow (hamburger) panel, which is why the CSS carries `ul.p-plus__overflow .menu-title/.menu-subtitle`.

In the port, hrefs keep their production spelling (`/blog/`, `/posts/` ...) in the header
text above; apply the port's canonical-URL mapping (`/articles/` etc.) the same way
it already does for the old header.

---------------------------------------------------------------------------

## 2. Collections: /blog/, /posts/ (and new /research/, /reading/)  (anthus_pages articles_index / posts_pages)

`gatsby-node.js` deletes `blog.jsx` and `posts-list.jsx` and creates every listing through
`src/templates/collection.jsx`:

* featured count on page 1 = 4, grid size = 8, so page 1 holds 12 items and pages >= 2 hold 8.
  `numPages = 1 + ceil(max(0, n - 12) / 8)`.
* URLs: page 1 `/<base>/`, page N `/<base>/page/N/`. Bases: `blog` (Articles; every published,
  non-platform node without tag `solutions` or `posts`), `research` (tag `research`),
  `reading` (tag `reading`), `posts` (tag `posts`).
* Items are sorted by `date DESC` inside a page, but page membership comes from the
  `allNodes` order in `gatsby-node.js`; ties in `date` are ordered arbitrarily
  (see "Provenance", ordering).
* `title` = "Articles" | "Research" | "Reading List" | "Posts"; page N > 1 uses `"<title>, page N"`
  as the `<h1>` and the `<title>`.
* `intro` (only `research`, only page 1) renders `<p class="platform-module--lead--c57dd">intro</p>`
  under the `<h1>`; the text is the `research` entry in `gatsby-node.js` (also present verbatim in
  `anthus_page_html.research_html`).
* `description` per collection (used for `<meta name=description>`):
  Articles: "Long-form articles from Anthus on decision models, agent systems, classifiers in production, and the economics of AI-built software." /
  Research: "Experiments on how Jev, Laya and other decision models actually behave in production: bias, calibration, fine-tuning and distillation, with the method and the measurements." /
  Reading: "Papers and books behind the work at Anthus, one short note each on what they say and what we checked." /
  Posts: "Short posts from Anthus on what shipped, what we read, and what changed in AI this week."

### /blog/ page 1

BEFORE (`/blog/`, ALL published articles in one list, wrapper `<div>`, image class `right`):

```html
<main><article><div><h1>Blog articles</h1><ul class="blog"><div class="blog-post-preview"><li class="clear-float"><a href="/blog/can-you-fix-it/"><GatsbyImage class="right"/><h3>Can You Fix It? ...</h3></a><div class="date">September 22, 2026</div><p>excerpt</p></li></div> ... </ul></div></article></main>
```

AFTER (`/blog/`):

```html
<main><article><h1>Articles</h1><ul class="blog"><div class="blog-post-preview"><li class="clear-float"><a href="/blog/glide-decision-model-ten-seconds/"><GatsbyImage class="featured"/><h3>It&#x27;s Not a System 1 Model If It Takes Ten Seconds</h3></a><div class="date">October 2, 2026</div><p>Fastino's GLiDE beats ...</p></li></div> <!-- x4 -->
</ul><h2>Earlier</h2><ul class="platform-module--grid--279c8"><li class="platform-module--card--0e0b8"><a class="research-cards-module--imageLink--25731" href="/blog/decision-models-are-not-calculators/"><GatsbyImage class="research-cards-module--headlineImage--8f69e"/></a><a class="platform-module--cardTitleLink--86ffe" href="/blog/decision-models-are-not-calculators/"><h3>Decision Models Are Not Calculators</h3></a><div class="platform-module--metaRow--493c0"><span class="platform-module--pill--2c821">September 25, 2026</span></div><p>excerpt</p><div class="platform-module--cardActions--b863f"><a href="/blog/decision-models-are-not-calculators/">Read more</a><a href="https://github.com/AnthusAI/Decision-Models-Are-Not-Calculators" target="_blank" rel="noopener noreferrer">Code: AnthusAI/Decision-Models-Are-Not-Calculators</a></div></li> <!-- x8 -->
</ul><nav class="clear-float" style="display:flex;justify-content:space-between;align-items:center;margin-top:1.5rem" aria-label="Articles pagination"><div><span></span></div><div>Page 1 of 5</div><div><a href="/blog/page/2/">Next →</a></div></nav></article></main>
```

Details that matter:
* Featured items: `<ul class="blog">` only rendered if there are featured items; the `<div class="blog-post-preview">` inside the `<ul>` is verbatim production (invalid but real).
  Excerpt is `<p>` with `dangerouslySetInnerHTML`; date via `formatPostDate` ("October 2, 2026").
* `<h2>Earlier</h2>` appears only when there ARE featured items (page 1). Pages >= 2 have the grid directly under the `<h1>`.
* Card `<a class="research-cards-module--imageLink--25731">` + image only when the post has a preview image;
  `.pill` date span only when the post has a date; the second link in `cardActions` ("Code: owner/repo",
  `repository` frontmatter with `https://github.com/` stripped) only when `repository` is set; both `target=_blank rel="noopener noreferrer"`.
* The pagination `<nav>` is rendered only when numPages > 1; the empty side is a bare `<span></span>`; last page: right `<div>` holds `<span></span>`.
  Link text `← Previous` / `Next →`.
* Item links are `/blog/<slug>` (the live HTML has the trailing slash because Gatsby adds it).
  Cards and featured items link to `/blog/…`, not `/posts/…`, for every collection.

### /blog/page/N/ (N=2..5 live)

```html
<main><article><h1>Articles, page 2</h1><ul class="platform-module--grid--279c8"><li class="platform-module--card--0e0b8">...</li> <!-- x8 --></ul><nav class="clear-float" style="..." aria-label="Articles pagination"><div><a href="/blog/page/1/">← Previous</a></div>...
```

(Page 2's Previous link goes to `/blog/` and Next to `/blog/page/3/`: `collectionPagePath(base, 1)` is `/<base>/`.)

### /posts/

BEFORE (`posts-list.jsx`, home-style rows, 12 per page, `/posts/N/`): 

```html
<main><h1>Recent Posts</h1><ul class="index-module--postsList--d248b"><li class="index-module--postsListItem--87ad2"><div class="index-module--postsListItemContent--e9dfd"><a class="index-module--postsListItemLink--85004" href="/blog/text-as-image-lensvlm/"><div><div class="index-module--listItemTitle--6ad29">...</div><div class="index-module--listItemDescription--f3875">...</div><div class="index-module--listItemRight--a56d2"><div class="index-module--listItemDate--6e6a2">September 24, 2026</div><div><i>more...</i></div></div></div><GatsbyImage class=""/></a></div></li> ...</ul><nav class="clear-float" ... aria-label="Posts pagination">...<a href="/posts/2/">Next →</a>...Page 1 of 4</nav></main>
```

AFTER (`/posts/`): identical to the `/blog/` shape above with `<h1>Posts</h1>`, `aria-label="Posts pagination"`, 5 pages, `Next` -> `/posts/page/2/`. No `<main><h1>` direct child: it is `<main><article><h1>`.

`/posts/N/` is now a stub generated in `onPostBuild` (exact bytes, used for 2..5):

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved to Posts, page 2</title>
<link rel="canonical" href="https://anth.us/posts/page/2/">
<meta http-equiv="refresh" content="0;url=/posts/page/2/">
</head>
<body>
<p>This page moved to <a href="/posts/page/2/">anth.us/posts/page/2/</a>.</p>
</body>
</html>
```

(The port already does 301 redirects for legacy URL shapes; nothing needs to be rendered in
production-for-the-port, this is informational. Only `posts` has `legacyPagePaths: true`;
`/blog/N/` never existed.)

### /research/ and /reading/ (new)

Same template, one page each (they have <= 12 items). Static text and the two lists are regenerated
into `anthus_page_html.research_html(featured=..., earlier=...)` / `reading_html(...)`; the lists are the
same `ul.blog` featured items and `platform-module--grid` cards as above. `/research/` has
`<p class="platform-module--lead--c57dd">` between the `<h1>` and the featured list.

Generators affected: `anthus_pages` articles_index (was blog.jsx shape), posts_pages (was posts-list.jsx
shape; pages and URLs change), a new pair of research/reading pages (already drivable through
`anthus_page_html`), and the card/featured list renderers (shared).

---------------------------------------------------------------------------

## 3. Featured-image class `right` -> `featured`

`.gatsby-image-wrapper.featured` is new in layout.scss (float right, 50%, 4px radius,
stacks full-width under 640px) and `ul.blog li` gained `display: flow-root`.
Everything that used `className="right"` inside a `blog-post-preview` now uses `className="featured"`:

* `/blog/` (see above) and every collection featured list
* Home "Recent Articles"  (`index.js`)
* The `ai-solutions` Engagements list
* NOT changed: tag pages (plain `<ul><li><a>`), article body images (`right` still means the old float via MDX `BlogImage`).

The class is the only markup change; `div.date`, `h3`, excerpt are as before.

---------------------------------------------------------------------------

## 4. Home page  (anthus_pages homepage)

All changes (BEFORE -> AFTER, in document order):

1. Hero overlay copy, new `heroProof` paragraph, button is an internal link:

```html
BEFORE: <div class="hero-overlay"><h1>Depend on proven experts</h1><p>We solve your business problems with AI, then run it securely in production.</p><a href="https://docs.google.com/forms/d/e/1FAIpQLSdWlt4KpwPSBHzg3o8fikHcfrzxo5rCcV-0-zDt815NZ1tcyg/viewform?usp=sf_link" class="button">Tell us the problem</a></div>
AFTER:  <div class="hero-overlay"><h1>Depend on proven experts</h1><p>We build the system, run it in production, and your experts keep it aligned.</p><p class="index-module--heroProof--e3c4c"><mark>A quarter billion dollars</mark> processed in production, at nearly 100% uptime.</p><a class="button" href="/engage/">Tell us the problem</a></div>
```

2. Intro paragraph:

```html
BEFORE: <p class="index-module--intro--0b876"><mark>A quarter billion dollars</mark> in revenue processed at scale, at nearly 100% uptime. <mark>180 billion tokens</mark> of production LLM workload. AI in production, not just in demos.</p>
AFTER:  <p class="index-module--intro--0b876"><mark>180 billion tokens</mark> of production LLM workload. AI in production, not just in demos.</p>
```

3. "What We Do" list: the 4th item ("Machine Learning") now links to `/decision-models/` (was
   `/blog/domain-specific-turn-detection/`) and its description reads "Custom classifiers, fine-tuned models, decision models like Jev, and <mark>calibrated confidence</mark> that tells you ..." (the rest of the sentence is unchanged).

4. Section order is now: What We Do, **Case studies**, **How we work**, The Anthus Platform, Recent Articles, Recent Posts.
   (BEFORE: What We Do, Our Approach: Cybernetic Development, The Anthus Platform, B0rd, Case studies, Recent Articles, Recent Posts.)

5. Case studies items are now fact lists, no `p`:

```html
AFTER: <h2>Case studies</h2><ul class="index-module--list--fb407"><li class="index-module--listItem--06e6d"><a class="index-module--listItemLink--02c9e" href="/blog/call-criteria/"><h3>Call Criteria</h3></a><ul class="index-module--caseFacts--1db6d"><li>Call-center QA, scored by an outside service&#x27;s fine-tuned classifiers.</li><li>Too expensive and too slow to scale to every new scorecard.</li><li>We built their classifier lab on Primus in their own AWS account and ran it for years.</li><li><mark>Hundreds of scorecards, millions of calls scored</mark>.</li></ul></li><li class="index-module--listItem--06e6d"><a class="index-module--listItemLink--02c9e" href="/blog/venue-driver/"><h3>Venue Driver</h3></a><ul class="index-module--caseFacts--1db6d"><li>Ticketing and reservations backbone for Las Vegas nightlife.</li><li>An AWS data center failed catastrophically.</li><li>We relocated the entire system within hours — ticket scanning never stopped.</li><li><mark>In continuous operation since 2007</mark>.</li></ul></li></ul><div class="clear-float">See our <a href="/ai-solutions/">solution patterns</a>.</div>
BEFORE: each <li> had <p class="index-module--listItemDescription--f3875"><mark>100% of calls reviewed</mark>, up from a sample. ...</p> instead of the <ul class="...caseFacts...">
```

6. Approach section: `<h2 class="index-module--approachHeading--15d5e">How we work</h2>` (was "Our Approach: Cybernetic Development");
   first paragraph is new text (the February 2026 "Continue." story, contains `<a href="/about/">That night is on the record.</a>`);
   `approachActions` loses the "Contact us" `<a class="button">` and the secondary link text changes:

```html
BEFORE: <div class="index-module--approachActions--a7c68"><a href="https://docs.google.com/forms/d/e/1FAI...viewform?usp=sf_link" class="button">Contact us</a><a class="index-module--approachSecondaryCta--79796" href="/blog/cybernetic-development/">Read Cybernetic Development</a></div>
AFTER:  <div class="index-module--approachActions--a7c68"><a class="index-module--approachSecondaryCta--79796" href="/blog/cybernetic-development/">How we govern AI-built systems</a></div>
```

   (Take the full section text from `web/reference/live/` is not saved for `/`; fetch https://anth.us/ or read
   `/Users/home/Projects/Anth.us-live-mirror/html/index.html`, `<section class="index-module--approachSection--61ee7">`.)

7. The B0rd `<section class="index-module--plexusFeature--...">` ("SPINOFF", "B0rd — desk displays for agent monitoring") is REMOVED. The Platform `plexusFeature` section stays.

8. Recent Articles: image class `right` -> `featured`; the date `<div class="date">2026-10-02</div>` and the
   excerpt `<div>` (not `<p>`) are unchanged in shape. Footer line:

```html
BEFORE: <div class="clear-float index-module--seeMoreFooter--ce8de">Please see our <a href="/blog/">Articles</a> for more.</div>
AFTER:  <div class="clear-float index-module--seeMoreFooter--ce8de">More in <a href="/blog/">Articles</a>.</div>
```

9. Recent Posts: thumbnail moves from last to first inside the link and gets a class; footer text changes:

```html
BEFORE: <a class="index-module--postsListItemLink--85004" href="/blog/text-as-image-lensvlm/"><div><div class="index-module--listItemTitle--6ad29">…</div>…</div><GatsbyImage class=""/></a>
AFTER:  <a class="index-module--postsListItemLink--85004" href="/blog/text-as-image-lensvlm/"><GatsbyImage class="index-module--postsListThumbnail--f612d"/><div><div class="index-module--listItemTitle--6ad29">…</div>…</div></a>
        <div class="clear-float index-module--seeMoreFooter--ce8de">More in <a href="/posts/">Posts</a>.</div>   (was: Please see our <a href="/posts/">Posts</a> for more.)
```

`<head>` description for the home page: "Anthus builds self-aligning AI systems: custom models, agent harnesses, evaluation loops, and unattended automation with a human in the loop, grounded in production operations since 2007." (was "... In production since 2023."), also in `og:description` and `twitter:description`.

---------------------------------------------------------------------------

## 5. Articles  (article heading + tail in the blog-post generator)

`src/templates/blog-post.jsx`:

* **Repository line**, inside `div.heading`, directly after the `div.authors` block, only when the
  frontmatter has `repository`:

```html
BEFORE: <div class="heading"><h1>…</h1><div class="date">September 22, 2026</div><div class="authors"><span class="byline">by </span><span class="author"><a href="/ryan">Ryan Porter</a></span></div></div>
AFTER:  <div class="heading"><h1>…</h1><div class="date">September 22, 2026</div><div class="authors"><span class="byline">by </span><span class="author"><a href="/ryan">Ryan Porter</a></span></div><div class="repository"><span class="byline">code and data at </span><a href="https://github.com/AnthusAI/Jev-Flywheel" target="_blank" rel="noopener noreferrer">AnthusAI/Jev-Flywheel</a></div></div>
```

  The link text is the repository URL with `^https?://(www\.)?github\.com/` removed. 11 pages carry it.
  CSS: `article .heading div.repository { opacity: .7; font-size: var(--font-sm) }`.

* **EngageCTA**: after the MDX body, last child of `<article>`, for posts whose `tags` include
  `client-acquisition` (11 articles; `/decision-models/` has the same block inline). Exact markup:

```html
<div class="engage-cta-module--box--92c7c"><h2 class="engage-cta-module--heading--f8246">We do this for clients, at scale</h2><p class="engage-cta-module--text--60ac0">Anthus has run this kind of loop in production for years: reviewers correct the model and say why, the explanation becomes policy, and the system gets more trustworthy month over month across hundreds of scorecards and millions of interactions. Bring us the judgment task and we&#x27;ll run it on Primus with your reviewers in the loop, and hand you a scorecard you can inspect after the first month.</p><a class="button" href="/engage/">See how an engagement works</a></div>
```

  (The source is `src/components/engage-cta.jsx`; its `href` is `/engage/` and it uses
  `contact-url.js` only for the sibling pages.) Applies on: distilling-jev-into-a-classifier, primus-classifier-lab,
  jev-vs-laya, one-word-test, decision-models-are-not-calculators, who-is-responsible-after-you-deploy-a-decision-model,
  making-decisions-instead-of-generating-text, fine-tuning-jev, encoding-prejudice, can-you-fix-it, can-you-trust-jev-confidence.

* **`<head>` for published articles**: `<meta property="og:type" content="article" .../>` (was `website`) and
  `<script type="application/ld+json" data-gatsby-head="true">{"@context":"https://schema.org","@type":"Article","headline":<title>,"description":<excerpt>,"datePublished":<date>,"author":[{"@type":"Person","name":<author>}...],"publisher":{"@type":"Organization","name":"Anthus AI Solutions"},"mainEntityOfPage":"https://anth.us/blog/<slug>/","image":<imageURL when present>}</script>`.
  Only for `state: published` posts.

Unchanged: the article body, `div.authors`, MDX components, `article.jsx` and `blog-tag.jsx`.

---------------------------------------------------------------------------

## 6. Tag pages  (anthus_pages tag_pages)

`blog-tag.jsx` and its markup are unchanged:
`<main><div><h1>Articles tagged with: HITL</h1><ul><li><a href="/blog/the-simulation-told-them-they-would-win/">The Simulation Told Them They Would Win</a></li></ul></div></main>`.
Caveat for any verification: the tag template has NO sort, so list order on live is whatever
Gatsby's datastore returned in Amplify's build (see Provenance); only the item set is stable.

---------------------------------------------------------------------------

## 7. Platform pages  (anthus_pages platform_*)

`/platform/`: content only. Chatticus and Antharchy are dropped from the prose and the "Multi-user agent workplace"
`platform-module--recipeCard--440b5` card is removed (24 -> 22 `<li>`; one recipe card fewer). Same classes and structure otherwise.
Product pages (`/platform/<product>/`): the one I diffed old-vs-new (`/platform/primus/`) has an identical `<main>`; all product
pages are identical between the new build and production. The `antharchy` and `chatticus` product pages still exist.

---------------------------------------------------------------------------

## 8. Bespoke pages: new hole APIs  (anthus_page_html)

Regenerated by `bin/extract-page-html.py` from fresh live fetches (all 8 pages now
`web/reference/live/*.html`; each `<main>` also verified equal to the build). Signatures:

```python
about_html() -> str
ai_solutions_html(*, engagements: str, projects: str, integrations: str) -> str   # CHANGED (was featured, portfolio, integrations)
ryan_html(*, portfolio: str, integrations: str) -> str                           # unchanged signature
not_found_html() -> str
engage_html() -> str
reading_html(*, featured: str, earlier: str) -> str
research_html(*, featured: str, earlier: str) -> str
decision_models_html() -> str
PAGE_META['/about/' | '/ai-solutions/' | '/ryan/' | '/404.html' | '/engage/' | '/reading/' | '/research/' | '/decision-models/']  # new text, regenerate any use
```

`ai_solutions_html` holes:

* `engagements` = `<ul class="blog">` (4 items today: dataparade, call-criteria, vault, venue-driver). Different from
  collection featured items: the date line is the free-text `display_date` (e.g. `2026 - ongoing`) falling back to `date`, and the
  excerpt is wrapped in `<div>` not `<p>`:
  `<div class="blog-post-preview"><li class="clear-float"><a href="/blog/dataparade/"><GatsbyImage class="featured"/><h3>DataParade</h3></a><div class="date">2026 - ongoing</div><div>EXCERPT HTML</div></li></div>`
  (source: posts tagged `solutions` AND `engagement`, not `integrations`; sorted date DESC).
* `projects` = `<ul class="platform-module--grid--279c8">` of research-cards (27 today): posts tagged `solutions` that are not
  `engagement`/`integrations`, merged with published posts tagged `project`, sorted date DESC. Card markup exactly as in section 2.
* `integrations` = `<ul class="index-module--list--fb407 undefined">` (Paytronix ... Marketo), unchanged shape.

`ryan_html`: unchanged API; portfolio is still TWO adjacent `index-module--list` `<ul>`s (smallImageList then plain).
`reading_html` / `research_html` need the featured `ul.blog` (4 items) and the `<ul class="platform-module--grid--279c8">`
(`earlier`, 8 items) from section 2; the `<h2>Earlier</h2>` is inside the static text.

Static changes inside regenerated pages worth knowing: `/about/` now has an intro `<strong>` paragraph, "The night we stopped
being the loop", Spinoffs, Who We Work With, Key Facts and FAQ sections (and a `twitter-tweet` class token with no CSS rule, as live);
`/ai-solutions/` has "What We Build" (4 `ul` items), Engagements, "How we work", "Projects and examples", Integrations, The Process.
CSS tokens used by those pages that production's stylesheet does not define (so they are expected to be unstyled):
`key-facts`, `twitter-tweet`, `blog-post-preview`, `description`, `resume`, and the literal class `undefined`.

---------------------------------------------------------------------------

## 9. `<head>` and site-wide

* New first-in-head inline script (analytics opt-out; the port has no gtag, so it can be omitted):
  `<script>(function(){try{var k='anthus-no-analytics',q=location.search.match(/[?&]notrack=(\w+)/);if(q){if(q[1]==='1')localStorage.setItem(k,'1');else localStorage.removeItem(k)}if(localStorage.getItem(k)==='1')window['ga-disable-G-31SC26SDGX']=true}catch(e){}})();</script>`
* New `<link rel="sitemap" type="application/xml" href="/sitemap-index.xml"/>` (gatsby-plugin-sitemap, excludes unpublished posts).
* `siteMetadata.description` now "... grounded in production operations since 2007." (home, about, ai-solutions descriptions changed; use `PAGE_META`).
* Fonts: the Google Fonts `<link>` is byte-identical to the old build (`Jersey 25`, `Geist Mono`, `Montserrat`, `display=block`); the font changes are only in the stylesheet.
* The shell outside `<header>` and `<main>` (including the footer) is unchanged.

## Provenance of the reference (what "AFTER" means)

* Deployed commit: Amplify app `d1ffh6ny5rvtl` (read-only `get-app`, `list-jobs`), branch `main`, latest successful job #258,
  commit `96ac29c241a1b75373d13f21268afcfb681bf5e5`, finished 2026-10-03 08:32 EDT. The content submodule is pinned by the commit
  (message "Pin content: ..."): `4b80f02431d0f8f59fb08a8cc7961d07cdbe789b`.
* Build: `npm ci` + `npm run build` (Node 20.20.2, `TZ=UTC`; Amplify uses Node 22). No secrets or env vars were needed (the app defines none).
* `styles.a4f6abf91bb86f9d4c6f.css`: same filename, same SHA-256 (`babbca7b...1e5d`), byte-identical to live.
* HTML: all 253 sitemap pages plus `/`, `/404.html`, `/posts/2..4/` compared with live. After normalising only build-noise
  (webpack chunk/compilation hashes, `app-*.js`, base64 blur placeholders): 237 identical; 15 contain the same items in a different
  order (unsorted tag pages and date ties: `blog/<tag>/` ordering is not deterministic across build machines, and `posts/page/4`
  swaps two posts both dated September 12, 2024); `blog/LLMs/` differs in its `<h1>` (`llms` live, `LLMs` in my build) and in one item; this looks like a tag-case collision
  (`llms` vs `LLMs` both map to the same path, last writer wins; assumed, not traced). Every one of the 8 bespoke pages, `/`, `/blog/`, `/posts/`, `/posts/page/2/`, `/platform/`, products and
  articles is in the identical set.
* For those order-only pages use the live copies in `/Users/home/Projects/Anth.us-live-mirror/html/` as the reference, not the build.
