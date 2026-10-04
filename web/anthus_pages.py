"""The production Anth.us page templates, emitting the production DOM.

Each generator here replaces one Gatsby page or template and returns the
**inner HTML of `<main>`** for that page. It returns HTML rather than Markdown
on purpose: the port reuses the production site's own compiled stylesheet
(`web/css/anthus-theme.css`), and that stylesheet targets the DOM these
templates produce -- `ul.blog > .blog-post-preview > li.clear-float`,
`.index-module--postsList--d248b`, `.platform-module--card--0e0b8`,
`.gatsby-image-wrapper.right`. Markdown routed through `markus convert` cannot
express any of it, so these pages bypass Markus entirely; only the MDX corpus
(articles and platform-product bodies) is converted.

| Gatsby source                      | Generator                 | Reference page                   |
| ---------------------------------- | ------------------------- | -------------------------------- |
| `src/pages/index.js`               | `homepage`                | `Anth.us/public/index.html`      |
| `src/pages/about.js`               | `about_page`              | `public/about/index.html`        |
| `src/pages/ai-solutions.js`        | `ai_solutions_page`       | `public/ai-solutions/index.html` |
| `src/pages/platform.js`            | `platform_index`          | `public/platform/index.html`     |
| `src/pages/ryan.js`                | `ryan_page`               | `public/ryan/index.html`         |
| `src/pages/404.js`                 | `not_found_page`          | `public/404.html`                |
| `src/templates/blog.jsx`           | `articles_index`          | `public/blog/index.html`         |
| `src/templates/posts-list.jsx`     | `posts_pages`             | `public/posts/index.html`        |
| `src/templates/blog-tag.jsx`       | `tag_pages`               | `public/blog/<tag>/index.html`   |
| `src/templates/platform-product`   | `platform_product_*`      | see note below                   |

The four pages whose bodies are pure static copy (`about`, `ai-solutions`,
`ryan`, `404`) live in `anthus_page_html`, lifted verbatim from the rendered
reference pages, because their copy is in the Gatsby repo's JSX rather than in
the content submodule -- transcribing it by hand would only introduce drift.

**Hrefs are emitted in production shape** (`/blog/<slug>/`, `/platform/`,
`/posts/2/`) and rewritten to this build's static paths by
`build_via_papyrus._rewrite_internal_links`. One mapper, one place to change,
and the emitted DOM stays directly comparable to `Anth.us/public/`.

**Platform product pages have no usable visual reference.** In the 2026-09-24
production build, `/platform/<product>/index.html` (and `/solutions/<x>/`, and
the bare-slug article duplicates) render with *no chrome at all* -- no
`.layout`, no header, no footer, just the MDX body. `platform-product.jsx`
clearly intends the full template, so what is implemented here is the DOM that
JSX would produce. Flagged rather than silently matched.

Hero and capability imagery comes from `web/assets/site/`, which is committed
in this repo: those files live in the **Anth.us** repo's `src/images`/`static`
trees, not in the content submodule, and the Amplify build has no access to a
sibling checkout.
"""

from __future__ import annotations

from html import escape

import anthus_dom
import anthus_page_html
from anthus_content import ContentNode, ImageIndex

CONTACT_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdWlt4KpwPSBHzg3o8fikHcfrzxo5rCcV-0-zDt815NZ1tcyg/viewform?usp=sf_link"
)

SITE_TITLE = "Anthus"
SITE_DESCRIPTION = (
    "Anthus builds self-aligning AI systems: custom models, agent harnesses, "
    "evaluation loops, and unattended automation with a human in the loop, "
    "grounded in production operations since 2007."
)

# gatsby-config.mjs siteMetadata.menuLinks. Kept here for the build's page
# registry; the rendered nav is `anthus_dom.MENU_LINKS`, which is the same set
# in production href shape.
MENU = anthus_dom.MENU_LINKS

# index.module.css / platform.module.css, as Gatsby hashes them. Read from the
# same committed JSON that `bin/build-theme-css.py` uses to rewrite the CSS, so
# a class name can never exist in one and not the other.
C = anthus_dom.css_modules()


def _esc(value: str) -> str:
    return escape(str(value), quote=True)


def blog_href(node: ContentNode) -> str:
    """The production route for one article or post."""
    return f"/blog/{node.slug}/"


def platform_href(node: ContentNode) -> str:
    return f"/platform/{node.slug}/"


# Kept under the old names so the build script and any callers keep working.
def article_href(node: ContentNode) -> str:
    return blog_href(node)


def _preview(node: ContentNode, images: ImageIndex) -> str | None:
    raw = node.front_matter.get("preview_image")
    if not raw:
        return None
    return images.resolve_path(str(raw), relative_to=node.source)


_BLOCK_TAG_RE = __import__("re").compile(r"<(p|ul|ol|div|h[1-6]|table|blockquote|pre)\b", __import__("re").I)


def _excerpt_container(tag: str, attrs: str, excerpt: str) -> str:
    """`<p ...>{excerpt}</p>`, as production renders it once React has hydrated.

    The excerpt is injected with `dangerouslySetInnerHTML`, and several contain
    block elements (`<p>`, `<ul>`). React builds `p > p/ul` in the DOM; an HTML
    parser would close the outer `<p>` at the first block child and leave empty
    `<p>`s around the content, changing every height below it. A `<div>` keeps
    the children inside the box; it takes the margin the `p` element rule would
    have given (`calc(var(--space-4) / 2)`), which is the only `p` rule that
    changes the geometry. Excerpts that are plain inline text stay a `<p>`.
    """
    if _BLOCK_TAG_RE.search(excerpt):
        # A `<div>` excerpt wrapper (`tag == "div"`) has no `p` margin to keep.
        style = ' style="margin-bottom:calc(var(--space-4)/2)"' if tag == "p" and not attrs else ""
        return f"<div{attrs}{style}>{excerpt}</div>"
    return f"<{tag}{attrs}>{excerpt}</{tag}>"


def _headline_from_excerpt_or_title(node: ContentNode) -> str:
    return node.excerpt_text.strip() or node.title


def _excerpt_html(node: ContentNode) -> str:
    """The excerpt as authored, markup intact.

    `solutions.js` and `posts-list.jsx` both render it with
    `dangerouslySetInnerHTML`, so `<mark>`, `<a>` and even a wrapping `<p>`
    reach the page verbatim -- including the nested-`<p>` quirk that production
    has. `excerpt_text` strips all of that and is only right for `<meta>`.
    """
    raw = node.front_matter.get("excerpt")
    return "" if raw is None else str(raw).strip()


# --------------------------------------------------------------------------
# Shared list items
# --------------------------------------------------------------------------


def _blog_item(
    node: ContentNode,
    images: ImageIndex,
    *,
    date: str,
    excerpt_tag: str,
    href: str | None = None,
    image_class: str = "featured",
    shows_excerpt_as_headline: bool = False,
) -> str:
    """One `ul.blog` row: `blog.jsx`'s `<BlogPostPreview>`.

    The `<div class="blog-post-preview">` wrapping an `<li>` is invalid HTML
    and is reproduced anyway -- it is what production emits, `ul.blog li` is
    what the stylesheet targets, and "fixing" it changes the box tree.

    `date` and `excerpt_tag` differ by call site, which is not a style choice:
    the homepage's Recent Articles block renders the raw front-matter date in a
    `<div>`, while `/blog/` renders the formatted date in a `<p>`. Both are
    reproduced as-is.
    """
    target = href or blog_href(node)
    image = _preview(node, images)
    image_html = (
        anthus_dom.image_html(
            src=image, alt=node.title, class_name=image_class, eager=False
        )
        if image
        else ""
    )
    headline = _headline_from_excerpt_or_title(node) if shows_excerpt_as_headline else node.title
    excerpt = "" if shows_excerpt_as_headline else _excerpt_container(
        excerpt_tag, "", _excerpt_html(node)
    )
    return (
        '<div class="blog-post-preview"><li class="clear-float">'
        f'<a href="{_esc(target)}">{image_html}<h3>{escape(headline)}</h3></a>'
        f'<div class="date">{escape(date)}</div>'
        + excerpt
        + "</li></div>"
    )


def _posts_item(node: ContentNode, images: ImageIndex) -> str:
    """One `.index-module--postsList--d248b` cell: the home page's Recent Posts.

    Live production puts the thumbnail first inside the link and gives it the
    `postsListThumbnail` class (it used to be last, classless).
    """
    image = _preview(node, images)
    image_html = (
        anthus_dom.image_html(
            src=image,
            alt=node.title,
            class_name=C["index:postsListThumbnail"],
            eager=False,
        )
        if image
        else ""
    )
    return (
        f'<li class="{C["index:postsListItem"]}">'
        f'<div class="{C["index:postsListItemContent"]}">'
        f'<a class="{C["index:postsListItemLink"]}" href="{_esc(blog_href(node))}">'
        f"{image_html}"
        f'<div><div class="{C["index:listItemTitle"]}">{escape(node.title)}</div>'
        f'<div class="{C["index:listItemDescription"]}">{_excerpt_html(node)}</div>'
        f'<div class="{C["index:listItemRight"]}">'
        f'<div class="{C["index:listItemDate"]}">{escape(node.display_date)}</div>'
        "<div><i>more...</i></div></div></div></a></div></li>"
    )


def _solution_date(node: ContentNode) -> str:
    """`solutions.js`: date-fns `format(date, "MMMM dd, yyyy")`, raw if invalid.

    Live production ignores `display_date` here (it is used only by the
    Engagements list on /ai-solutions/).
    """
    parsed = node.date
    return parsed.strftime("%B %d, %Y") if parsed.year > 1 else node.date_raw


def solutions_list(
    nodes: list[ContentNode],
    images: ImageIndex,
    *,
    with_image: bool,
    extra_class: str | None = None,
) -> str:
    """`src/components/solutions.js`, rendered.

    Two production quirks are reproduced deliberately, because they are in the
    class attributes the stylesheet and any structural diff see: React
    interpolates a missing `className` prop as the literal string
    `undefined`, and leaves a trailing space on an unfeatured item's class
    list. Normalising them would make this build's DOM differ from the
    reference for no visual gain.
    """
    items = []
    for node in nodes:
        featured = "featured" in node.tags
        image = _preview(node, images) if with_image else None
        parts = []
        if image:
            parts.append(
                anthus_dom.image_html(
                    src=image, alt=node.title, class_name="", eager=False
                )
            )
        heading = f"<h3>{escape(node.title)}</h3>"
        if featured:
            parts.append(
                f'<a class="{C["index:listItemLink"]}" '
                f'href="{_esc(blog_href(node))}">{heading}</a>'
            )
        else:
            parts.append(heading)
        parts.append(
            f'<p class="{C["index:listItemDescription"]} date">'
            f"{escape(_solution_date(node))}</p>"
        )
        parts.append(
            _excerpt_container(
                "p", f' class="{C["index:listItemDescription"]}"', _excerpt_html(node)
            )
        )
        item_class = f'{C["index:listItem"]} {C["index:featuredItem"]}' if featured else f'{C["index:listItem"]} '
        items.append(f'<li class="{item_class}">{"".join(parts)}</li>')
    list_class = f'{C["index:list"]} {extra_class if extra_class else "undefined"}'
    return f'<ul class="{list_class}">{"".join(items)}</ul>'


# --------------------------------------------------------------------------
# Homepage — src/pages/index.js
# --------------------------------------------------------------------------

# (title, href, image basename, image alt, description HTML)
_CAPABILITIES = (
    (
        "Knowledge Bases",
        "https://github.com/AnthusAI/Biblicus",
        "smart-process-automation.png",
        "Knowledge bases with learned ontologies and taxonomies",
        "Your agents are only as good as what they can look up.  We build "
        "knowledge bases with <mark>ontologies and taxonomies that learn from "
        "your data</mark>, refining their own structure instead of going stale "
        "the week after someone hand-built them.",
    ),
    (
        "Self-Aligning Automation",
        "/blog/call-criteria/",
        "ai-enabled-projects.png",
        "Unattended automation with a human in the loop",
        "Unattended business process automation with a human in the loop.  "
        "Reviewers correct it and say why; the system <mark>turns the "
        "explanation into a stated policy</mark> and applies it from then on.",
    ),
    (
        "Agent Systems",
        "/blog/give-an-agent-a-tool/",
        "ai-agent.png",
        "Agent systems, tools, and orchestration",
        "A model is half a system.  The other half is the harness: the tools it "
        "can reach, the procedures it follows, the limits it runs inside, and "
        "the ability to work for hours <mark>without losing the plot</mark>.",
    ),
    (
        "Machine Learning",
        "/decision-models/",
        "ai-software-feature.png",
        "Custom and fine-tuned machine learning models",
        "Custom classifiers, fine-tuned models, decision models like Jev, and "
        "<mark>calibrated confidence</mark> that tells you which decisions to trust and which to "
        "escalate.  We find the cheapest model that clears your bar, prove that "
        "it clears it, and run it in production on AWS—training, serving, and "
        "evaluation included.",
    ),
)

HOME_TITLE = "Depend on proven experts"
HOME_SUBHEAD = "We build the system, run it in production, and your experts keep it aligned."


def _hero() -> str:
    """`src/components/hero.js` + the homepage's two hero images.

    `.hero-overlay` is absolutely positioned over the image by `layout.scss`.
    Two images are emitted because the stylesheet shows the tall one below
    941px and the wide one above it. The button is an internal link to
    `/engage/` on live production (it used to be the contact form).
    """
    return (
        '<div class="hero">'
        + anthus_dom.hero_image_html(
            src="/assets/site/serverless-ai-software-solutions.png",
            alt="Anthus",
            class_name="hero-image hero-image-default",
        )
        + anthus_dom.hero_image_html(
            src="/assets/site/serverless-ai-software-solutions-wide.png",
            alt="Anthus",
            class_name="hero-image hero-image-wide",
        )
        + '<div class="hero-overlay">'
        f"<h1>{escape(HOME_TITLE)}</h1><p>{escape(HOME_SUBHEAD)}</p>"
        f'<p class="{C["index:heroProof"]}"><mark>A quarter billion dollars</mark> '
        "processed in production, at nearly 100% uptime.</p>"
        '<a class="button" href="/engage/">Tell us the problem</a>'
        "</div></div>"
    )


def homepage(
    *,
    articles: list[ContentNode],
    posts: list[ContentNode],
    images: ImageIndex,
    blog: list[ContentNode] | None = None,
) -> str:
    """`src/pages/index.js`, as deployed (Anth.us 96ac29c).

    Section order: What We Do, Case studies, How we work, The Anthus Platform,
    Recent Articles, Recent Posts. The B0rd spinoff section is gone.
    """
    out = [_hero()]

    out.append(
        f'<p class="{C["index:intro"]}">'
        "<mark>180 billion tokens</mark> of production LLM workload. AI in "
        "production, not just in demos.</p>"
    )

    out.append("<h2>What We Do</h2>")
    cards = []
    for title, url, image, alt, description in _CAPABILITIES:
        cards.append(
            f'<li class="{C["index:listItem"]}">'
            f'<a href="{_esc(url)}" class="{C["index:listItemLink"]}">'
            + anthus_dom.image_html(
                src=f"/assets/site/{image}", alt=alt, class_name="", eager=False
            )
            + f"<h3>{escape(title)}</h3></a>"
            f'<p class="{C["index:listItemDescription"]}">{description}</p></li>'
        )
    out.append(f'<ul class="{C["index:list"]}">{"".join(cards)}</ul>')

    out.append(
        f'<p class="{C["index:intro"]} {C["index:textCenter"]}">'
        "Clients usually arrive asking about one of these. "
        "<mark>The work rarely stays in one box.</mark></p>"
    )

    def case(slug: str, title: str, facts: str) -> str:
        return (
            f'<li class="{C["index:listItem"]}">'
            f'<a class="{C["index:listItemLink"]}" href="/blog/{slug}/">'
            f"<h3>{title}</h3></a>"
            f'<ul class="{C["index:caseFacts"]}">{facts}</ul></li>'
        )

    out.append("<h2>Case studies</h2>")
    out.append(
        f'<ul class="{C["index:list"]}">'
        + case(
            "call-criteria",
            "Call Criteria",
            "<li>Call-center QA, scored by an outside service&#x27;s fine-tuned classifiers.</li>"
            "<li>Too expensive and too slow to scale to every new scorecard.</li>"
            "<li>We built their classifier lab on Primus in their own AWS account and ran it for years.</li>"
            "<li><mark>Hundreds of scorecards, millions of calls scored</mark>.</li>",
        )
        + case(
            "venue-driver",
            "Venue Driver",
            "<li>Ticketing and reservations backbone for Las Vegas nightlife.</li>"
            "<li>An AWS data center failed catastrophically.</li>"
            "<li>We relocated the entire system within hours \u2014 ticket scanning never stopped.</li>"
            "<li><mark>In continuous operation since 2007</mark>.</li>",
        )
        + "</ul>"
    )
    out.append(
        '<div class="clear-float">See our <a href="/ai-solutions/">solution '
        "patterns</a>.</div>"
    )

    out.append(
        f'<section class="{C["index:approachSection"]}">'
        f'<h2 class="{C["index:approachHeading"]}">How we work</h2>'
        f'<div class="{C["index:approachContent"]}"><div>'
        "<p>You might be wondering whether AI-built means nobody checked. For us it "
        "means the opposite, and we learned it the hard way: in February 2026 the "
        "nightly routine was pasting &quot;Continue.&quot; into four Codex sessions "
        "before bed, because nothing else kept the agents going or told us what "
        "they&#x27;d done. "
        '<a href="/about/">That night is on the record.</a> Everything we ship now '
        "runs under specs, tests, staged rollout, and a person who can say no. We "
        "call that cybernetic development: we use AI to write code the same way we "
        "use it to classify calls, inside a governor of constraints, feedback "
        "loops, and human judgment that keeps systems reliable in production.</p>"
        "<p>Modern failures increasingly look less like isolated \u201cbugs\u201d "
        "and more like operational, multi-system breakdowns. Great unit tests "
        "help\u2014but they don\u2019t cover every emergent scenario. So we build "
        "layered defenses and close the loop with real-world feedback.</p>"
        "<ul><li>Specs first: define behavior before implementation.</li>"
        "<li>Defense in depth: sandboxed tools, CI gates, staged rollouts, and "
        "fast rollback.</li>"
        "<li>Operational feedback: telemetry and incident-driven regressions "
        "that tighten the loop over time.</li>"
        "<li>Simplify and delete: reduce degrees of freedom to eliminate entire "
        "classes of failure.</li></ul>"
        f'<div class="{C["index:approachActions"]}">'
        f'<a class="{C["index:approachSecondaryCta"]}" '
        'href="/blog/cybernetic-development/">How we govern AI-built systems</a>'
        "</div></div></div></section>"
    )

    out.append(
        f'<section class="{C["index:plexusFeature"]}">'
        f'<span class="{C["index:eyebrow"]}">PART OF</span>'
        f'<h2 class="{C["index:platformHeader"]}">The Anthus Platform</h2>'
        "<p>Solve complex business problems with AI and ML using a proven, "
        "reusable technology stack that grew out of real delivery work \u2014 "
        "runtime, agent execution, knowledge, observability, and media, with the "
        "enterprise controls that matter in production.</p>"
        f'<div class="{C["index:approachActions"]}">'
        '<a class="button" href="/platform/">Explore the platform</a>'
        "</div></section>"
    )

    out.append("<h2>Recent Articles</h2>")
    out.append(
        '<ul class="blog">'
        + "".join(
            _blog_item(
                node,
                images,
                date=node.date_raw,
                excerpt_tag="div",
                href=str(node.front_matter.get("external_url") or blog_href(node)),
            )
            for node in articles[:4]
        )
        + "</ul>"
    )
    out.append(
        f'<div class="clear-float {C["index:seeMoreFooter"]}">More in '
        '<a href="/blog/">Articles</a>.</div>'
    )

    out.append("<h2>Recent Posts</h2>")
    out.append(
        f'<ul class="{C["index:postsList"]}">'
        + "".join(_posts_item(node, images) for node in posts[:4])
        + "</ul>"
    )
    out.append(
        f'<div class="clear-float {C["index:seeMoreFooter"]}">More in '
        '<a href="/posts/">Posts</a>.</div>'
    )
    return "".join(out)


# --------------------------------------------------------------------------
# Collections: collection.jsx -- /blog/, /posts/, /research/, /reading/
# --------------------------------------------------------------------------

from anthus_urls import FEATURED_COUNT, GRID_SIZE, collection_page_count  # noqa: E402

COLLECTION_DESCRIPTIONS = {
    "Articles": (
        "Long-form articles from Anthus on decision models, agent systems, "
        "classifiers in production, and the economics of AI-built software."
    ),
    "Research": (
        "Experiments on how Jev, Laya and other decision models actually behave "
        "in production: bias, calibration, fine-tuning and distillation, with the "
        "method and the measurements."
    ),
    "Reading List": (
        "Papers and books behind the work at Anthus, one short note each on what "
        "they say and what we checked."
    ),
    "Posts": (
        "Short posts from Anthus on what shipped, what we read, and what changed "
        "in AI this week."
    ),
}


def collection_page_path(base: str, page: int) -> str:
    """Production route of a collection page (rewritten by the link mapper)."""
    return f"/{base}/" if page == 1 else f"/{base}/page/{page}/"


def _grid_html(
    nodes: list[ContentNode], images: ImageIndex, shows_excerpt_as_headline: bool = False
) -> str:
    return (
        f'<ul class="{C["platform:grid"]}">'
        + "".join(
            _research_card(n, images, shows_excerpt_as_headline=shows_excerpt_as_headline)
            for n in nodes
        )
        + "</ul>"
    )


def collection_slices(nodes: list[ContentNode], page: int):
    """(featured, grid) node lists for one page of a collection."""
    if page == 1:
        return nodes[:FEATURED_COUNT], nodes[FEATURED_COUNT : FEATURED_COUNT + GRID_SIZE]
    start = FEATURED_COUNT + GRID_SIZE + (page - 2) * GRID_SIZE
    return [], nodes[start : start + GRID_SIZE]


def collection_lists(
    nodes: list[ContentNode],
    images: ImageIndex,
    page: int = 1,
    shows_excerpt_as_headline: bool = False,
) -> tuple[str, str]:
    """The (featured `ul.blog`, grid `ul`) HTML for one collection page."""
    featured_nodes, grid_nodes = collection_slices(nodes, page)
    featured = (
        '<ul class="blog">'
        + "".join(
            _blog_item(
                n,
                images,
                date=n.display_date,
                excerpt_tag="p",
                image_class="featured",
                shows_excerpt_as_headline=shows_excerpt_as_headline,
            )
            for n in featured_nodes
        )
        + "</ul>"
        if featured_nodes
        else ""
    )
    return featured, _grid_html(grid_nodes, images, shows_excerpt_as_headline)


def collection_nav(title: str, base: str, page: int, total: int) -> str:
    """The pagination `<nav>`, rendered only when there is more than one page."""
    if total <= 1:
        return ""
    previous = (
        f'<a href="{_esc(collection_page_path(base, page - 1))}">\u2190 Previous</a>'
        if page > 1
        else "<span></span>"
    )
    following = (
        f'<a href="{_esc(collection_page_path(base, page + 1))}">Next \u2192</a>'
        if page < total
        else "<span></span>"
    )
    return (
        '<nav class="clear-float" style="display:flex;justify-content:space-between;'
        'align-items:center;margin-top:1.5rem" '
        f'aria-label="{escape(title)} pagination">'
        f"<div>{previous}</div><div>Page {page} of {total}</div>"
        f"<div>{following}</div></nav>"
    )


def collection_page(
    title: str,
    base: str,
    nodes: list[ContentNode],
    page: int,
    images: ImageIndex,
    shows_excerpt_as_headline: bool = False,
) -> str:
    """`collection.jsx` for `/blog/` and `/posts/` (every page) and page >= 2 of any base."""
    total = collection_page_count(len(nodes))
    featured, grid = collection_lists(nodes, images, page, shows_excerpt_as_headline)
    heading = title if page == 1 else f"{title}, page {page}"
    return (
        f"<article><h1>{escape(heading)}</h1>"
        + featured
        + ("<h2>Earlier</h2>" if featured else "")
        + grid
        + collection_nav(title, base, page, total)
        + "</article>"
    )


def articles_collection(articles: list[ContentNode], images: ImageIndex) -> dict[int, str]:
    total = collection_page_count(len(articles))
    return {p: collection_page("Articles", "blog", articles, p, images) for p in range(1, total + 1)}


def posts_collection(posts: list[ContentNode], images: ImageIndex) -> dict[int, str]:
    total = collection_page_count(len(posts))
    return {
        p: collection_page("Posts", "posts", posts, p, images, shows_excerpt_as_headline=True)
        for p in range(1, total + 1)
    }


def tag_pages(tags: dict[str, list[ContentNode]]) -> dict[str, tuple[str, str]]:
    """`src/templates/blog-tag.jsx`. Returns `{slug: (label, html)}`.

    Production mounts these at `/blog/<tag>`, which shares a namespace with
    article slugs; this build uses `/tags/<tag>` so a tag can never shadow an
    article. The corpus also tags both `AI` and `ai`, which are the same tag to
    a reader, so case variants are merged rather than one silently overwriting
    the other's page.
    """
    merged: dict[str, tuple[str, list[ContentNode]]] = {}
    for tag, nodes in tags.items():
        slug = tag.strip().lower().replace(" ", "-")
        label, existing = merged.get(slug, (tag.strip(), []))
        combined = {node.slug: node for node in existing}
        combined.update({node.slug: node for node in nodes})
        if len(nodes) > len(existing):
            label = tag.strip()
        merged[slug] = (label, list(combined.values()))

    pages: dict[str, tuple[str, str]] = {}
    for slug, (label, nodes) in sorted(merged.items()):
        items = "".join(
            f'<li><a href="{_esc(blog_href(node))}">{escape(node.title)}</a></li>'
            for node in sorted(nodes, key=lambda n: (n.date, n.slug), reverse=True)
        )
        pages[slug] = (
            f"Articles tagged with: {label}",
            f"<div><h1>Articles tagged with: {escape(label)}</h1>"
            f"<ul>{items}</ul></div>",
        )

    index_items = "".join(
        f'<li><a href="/tags/{_esc(slug)}/">{escape(label)}</a> ({len(nodes)})</li>'
        for slug, (label, nodes) in sorted(merged.items())
    )
    pages["index"] = (
        "Tags",
        f"<div><h1>Tags</h1><ul>{index_items}</ul></div>",
    )
    return pages


# --------------------------------------------------------------------------
# Platform constants, carried over unchanged from the Markdown-era module.
# --------------------------------------------------------------------------

_CATEGORY_ORDER = (
    "Platform Runtime",
    "Agent Execution",
    "Data and Knowledge",
    "Observability",
    "Media Automation",
)

_STACK_RECIPES = (
    (
        "Research-to-output pipeline",
        "Biblicus collects and extracts the corpus, Tactus encodes the procedure, "
        "Babulus and VideoML generate the outward-facing output, and Korporus "
        "provides the place to run it as a service.",
    ),
    (
        "Governed agent application",
        "Tactus defines the durable procedure, Primus measures and improves it, "
        "Kanbus tracks work and operator state, and Caducus helps humans see what "
        "is going wrong in production.",
    ),
    (
        "Platform-native internal tooling",
        "Korporus supplies the shared shell while product-specific modules from "
        "Primus, Kanbus, Biblicus, and future tools appear as interoperable "
        "applications instead of one-off surfaces.",
    ),
    (
        "Multi-user agent workplace",
        "Chatticus is the shared room for people and named bots, Antharchy is the "
        "agentic desktop those bots can run, and Tactus encodes the durable "
        "procedures they execute with human approval boundaries.",
    ),
)

PLATFORM_RELATIONSHIPS: dict[str, dict] = {
    "primus": {
        "fits": "Primus is the MLOps and evaluation spine of the platform. It helps the other building blocks behave like governable production systems instead of isolated demos.",
        "links": [
            ("Works with Tactus procedures", "tactus"),
            ("Turns Biblicus feedback into evaluation inputs", "biblicus"),
            ("Runs inside broader Korporus surfaces", "korporus"),
        ],
        "recipe": "Example: pair Primus with Tactus for durable procedures, Biblicus for evidence-backed inputs, and Caducus for operator monitoring.",
    },
    "tactus": {
        "fits": "Tactus is the procedural core. It gives the rest of the platform a durable way to describe tool-using agent behavior.",
        "links": [
            ("Evaluated through Primus", "primus"),
            ("Grounded by Biblicus corpora", "biblicus"),
            ("Hosted inside Korporus", "korporus"),
        ],
        "recipe": "Example: use Tactus to encode a repeatable research workflow, Biblicus for the corpus, and Primus for regression checks before deployment.",
    },
    "kanbus": {
        "fits": "Kanbus supplies durable workflow memory so humans and agents can coordinate real delivery work instead of operating in a stateless loop.",
        "links": [
            ("Pairs with Tactus for execution", "tactus"),
            ("Feeds work cadence into Primus", "primus"),
            ("Appears in Korporus as an operator surface", "korporus"),
        ],
        "recipe": "Example: combine Kanbus, Tactus, and Primus to manage backlogs, execute procedures, and continuously improve the resulting system.",
    },
    "korporus": {
        "fits": "Korporus is the standard container for platform-powered applications. It is where multiple Anthus components can show up together as one service.",
        "links": [
            ("Hosts Primus-powered applications", "primus"),
            ("Hosts Tactus-driven workflows", "tactus"),
            ("Benefits from Caducus operator visibility", "caducus"),
        ],
        "recipe": "Example: use Korporus as the shell around a Tactus workflow, a Primus control plane, and a Babulus authoring surface for a complete internal platform app.",
    },
    "biblicus": {
        "fits": "Biblicus is the evidence layer. It gives other Anthus components something inspectable and rebuildable to reason over.",
        "links": [
            ("Grounds Tactus procedures", "tactus"),
            ("Feeds signals into Primus", "primus"),
            ("Supplies source material to Babulus", "babulus"),
        ],
        "recipe": "Example: use Biblicus to manage a document corpus, Tactus to extract and transform it, and Babulus to publish a derived narrative or video output.",
    },
    "virtuus": {
        "fits": "Virtuus keeps structured data portable for the rest of the platform, especially when a heavyweight service database is the wrong fit.",
        "links": [
            ("Supports Caducus storage", "caducus"),
            ("Supports Tactus worker data", "tactus"),
            ("Complements Biblicus corpora", "biblicus"),
        ],
        "recipe": "Example: pair Virtuus with Tactus and Caducus when you need portable, file-backed state for isolated workers and operational analysis.",
    },
    "caducus": {
        "fits": "Caducus is the operator-visibility layer. It helps Anthus services stay understandable after deployment.",
        "links": [
            ("Monitors Korporus-hosted services", "korporus"),
            ("Supports Primus-governed systems", "primus"),
            ("Uses Virtuus-backed local data", "virtuus"),
        ],
        "recipe": "Example: add Caducus to a Korporus and Primus deployment when humans need to triage incidents and understand evolving agent behavior.",
    },
    "babulus": {
        "fits": "Babulus is the content and video authoring layer for the platform. It applies the same code-reviewable discipline to outward-facing media.",
        "links": [
            ("Built on VideoML", "videoml"),
            ("Can use Biblicus as a source corpus", "biblicus"),
            ("Can run inside Korporus surfaces", "korporus"),
        ],
        "recipe": "Example: combine Biblicus, Babulus, VideoML, and Korporus to turn a living research corpus into repeatable product demos or explainers.",
    },
    "videoml": {
        "fits": "VideoML is the rendering substrate underneath Anthus media automation. It lets higher-level products treat video as a reproducible pipeline.",
        "links": [
            ("Powers Babulus authoring workflows", "babulus"),
            ("Can package Biblicus-derived narratives", "biblicus"),
            ("Can be surfaced through Korporus", "korporus"),
        ],
        "recipe": "Example: use VideoML and Babulus to turn a Biblicus-backed content workflow into automated demos, tutorials, and launch assets.",
    },
}

# --------------------------------------------------------------------------
# Platform — src/pages/platform.js, src/components/platform-cards.js
# --------------------------------------------------------------------------

P = {key.split(":")[1]: value for key, value in C.items() if key.startswith("platform:")}


def _fm(node: ContentNode, key: str) -> str:
    value = node.front_matter.get(key)
    return "" if value in (None, "") else str(value)


def _platform_card(node: ContentNode) -> str:
    """`PlatformCards`' `<li class=card>`. Text is escaped, as React does."""
    href = _esc(platform_href(node))
    pills = "".join(
        f'<span class="{C["platform:pill"]}">{escape(_fm(node, key))}</span>'
        for key in ("platform_category", "platform_stage")
        if _fm(node, key)
    )
    external = _fm(node, "external_url")
    visit = f'<a href="{_esc(external)}">Visit site</a>' if external else ""
    return (
        f'<li class="{C["platform:card"]}">'
        f'<a class="{C["platform:cardTitleLink"]}" href="{href}">'
        f"<h3>{escape(node.title)}</h3></a>"
        f'<div class="{C["platform:metaRow"]}">{pills}</div>'
        f"<p>{escape(_fm(node, 'excerpt'))}</p>"
        f'<div class="{C["platform:cardActions"]}"><a href="{href}">Read more</a>'
        f"{visit}</div></li>"
    )


def _platform_cards(nodes: list[ContentNode]) -> str:
    return f'<ul class="{C["platform:grid"]}">' + "".join(_platform_card(n) for n in nodes) + "</ul>"


_MAP_COLUMNS = (
    (
        "Runtime and control plane",
        (
            ("Korporus", "standardizes the shell and hosting model for platform-powered services."),
            ("Chatticus", "gives people and bots a shared room with approvals."),
            ("Primus", "manages evaluation, feedback loops, and MLOps."),
            ("Kanbus", "keeps work orchestration and project memory durable."),
        ),
    ),
    (
        "Agent execution and data",
        (
            ("Tactus", "defines durable, sandboxed agent procedures."),
            ("Antharchy", "is the agentic Linux desktop for long-running bot work."),
            ("Biblicus", "turns corpora into extractable, retrievable knowledge."),
            ("Virtuus", "makes structured JSON data queryable on disk."),
        ),
    ),
)


def platform_index(platform: list[ContentNode]) -> str:
    """`platform.js`. `platform` arrives already sorted by `platform_order`."""
    grouped: dict[str, list[ContentNode]] = {}
    for node in platform:
        grouped.setdefault(_fm(node, "platform_category") or "Platform", []).append(node)
    featured = [n for n in platform if n.slug in ("tactus", "videoml")]

    columns = "".join(
        f'<div class="{C["platform:mapColumn"]}"><h3>{escape(title)}</h3><ul>'
        + "".join(f"<li><code>{name}</code> {text}</li>" for name, text in items)
        + "</ul></div>"
        for title, items in _MAP_COLUMNS
    )
    columns += (
        f'<div class="{C["platform:mapColumn"]}"><h3>Operations and media</h3><ul>'
        "<li><code>Caducus</code> surfaces operator-facing health and incident signals.</li>"
        "<li><code>Babulus</code> and <code>VideoML</code> apply the same code-first "
        "approach to content and video.</li>"
        "<li>The result is one stack for systems, workflows, and communication.</li>"
        "</ul></div>"
    )
    recipes = "".join(
        f'<div class="{C["platform:recipeCard"]}"><h3>{escape(title)}</h3>'
        f"<p>{escape(summary)}</p></div>"
        for title, summary in _STACK_RECIPES
    )
    sections = "".join(
        f'<section class="{C["platform:section"]}">'
        f'<h2 class="{C["platform:sectionHeading"]}">{escape(category)}</h2>'
        f"{_platform_cards(grouped[category])}</section>"
        for category in _CATEGORY_ORDER
        if grouped.get(category)
    )
    return (
        "<article>"
        f'<section class="{C["platform:hero"]}"><h1>The Anthus Platform</h1>'
        f'<p class="{C["platform:lead"]}"><strong>A technology stack that grew out of '
        "real delivery work.</strong> It is not a speculative architecture diagram. "
        "This is the internal product line that emerged from building RLHF systems, "
        "durable agent workflows, retrieval-backed automation, hosted operator "
        "applications, and programmable media pipelines for real engagements. The same "
        "enterprise controls that matter in production software also matter here: "
        "auditability, rollback paths, operator visibility, and clear evaluation "
        "loops.</p>"
        f'<div class="{C["platform:actions"]}">'
        '<a class="button" href="/ai-solutions/">See the solutions we deliver</a>'
        f'<a class="{C["platform:secondaryLink"]}" href="/blog/cybernetic-development/">'
        "Read the cybernetic development thesis</a></div></section>"
        f'<section class="{C["platform:section"]}">'
        f'<h2 class="{C["platform:sectionHeading"]}">How the platform fits together</h2>'
        "<p>We think about the platform in layers because complete AI systems need more "
        "than a model call. Korporus is the host shell. Chatticus is the shared room "
        "for people and bots. Antharchy is the agentic desktop those bots can run. Tactus "
        "defines the durable procedure. Kanbus keeps workflow memory and state. Primus "
        "closes the evaluation loop. Biblicus and Virtuus make evidence and structured "
        "data portable. Caducus gives operators visibility. Babulus and VideoML apply the "
        "same discipline to narrative and media output.</p>"
        "<p>These are reusable building blocks, not isolated side projects. We combine "
        "them differently depending on the job: QA and evaluation, internal operator "
        "tooling, extraction and retrieval workflows, or outward-facing content "
        "systems.</p>"
        f'<div class="{C["platform:mapGrid"]}">{columns}</div>'
        f'<div class="{C["platform:recipeGrid"]}">{recipes}</div></section>'
        f'<section class="{C["platform:section"]}">'
        f'<h2 class="{C["platform:sectionHeading"]}">Featured platform technologies</h2>'
        "<p>Tactus and VideoML deserve separate attention because they express the "
        "broader Anthus point of view: treat complex operational systems as code, keep "
        "them inspectable, and make agent collaboration governable.</p>"
        f"{_platform_cards(featured)}</section>"
        f"{sections}</article>"
    )


def platform_product_head(node: ContentNode) -> str:
    """`platform-product.jsx`'s heading block, as HTML.

    There is no usable production reference for this route: the 2026-09-24
    build renders `/platform/<product>/` with no chrome at all. This is what
    the template's JSX produces, in the same class vocabulary as `platform.js`.
    """
    pills = "".join(
        f'<span class="{C["platform:pill"]}">{escape(_fm(node, key))}</span>'
        for key in ("platform_category", "platform_stage")
        if _fm(node, key)
    )
    external = _fm(node, "external_url")
    visit = (
        f'<a href="{_esc(external)}" class="button">Visit external site</a>' if external else ""
    )
    return (
        f'<a class="{C["platform:productBackLink"]}" href="/platform/">'
        "Back to Anthus Platform</a>"
        '<div class="heading">'
        f'<span class="{C["platform:eyebrow"]}">PART OF</span>'
        f'<h2 class="{C["platform:platformHeader"]}">The Anthus Platform</h2>'
        f"<h1>{escape(node.title)}</h1>"
        f'<div class="{C["platform:metaRow"]}">{pills}</div>'
        f'<p class="{C["platform:lead"]}">{escape(_fm(node, "excerpt"))}</p>'
        f'<div class="{C["platform:actions"]}">{visit}'
        f'<a class="{C["platform:secondaryLink"]}" href="/ai-solutions/">'
        "See how it fits our solutions work</a></div></div>"
    )


def platform_product_tail(node: ContentNode) -> str:
    relationship = PLATFORM_RELATIONSHIPS.get(node.slug)
    if not relationship:
        return ""
    links = "".join(
        f'<li><a href="/platform/{slug}/">{escape(label)}</a></li>'
        for label, slug in relationship["links"]
    )
    return (
        f'<section class="{C["platform:section"]}">'
        f'<h2 class="{C["platform:sectionHeading"]}">Where this fits in the Anthus Platform</h2>'
        f"<p>{escape(relationship['fits'])}</p>"
        f'<ul class="{C["platform:featureList"]}">{links}</ul>'
        f'<div class="{C["platform:recipeCard"]}"><h3>Common combination</h3>'
        f"<p>{escape(relationship['recipe'])}</p></div></section>"
    )


# --------------------------------------------------------------------------
# Solutions pages: about / ai-solutions / ryan / 404 (static copy lives in
# anthus_page_html; only the dynamic lists are generated here)
# --------------------------------------------------------------------------


def about_page() -> str:
    return anthus_page_html.about_html()


def ai_solutions_page(blog: list[ContentNode], images: ImageIndex) -> str:
    """`ai-solutions.js` as deployed: Engagements / Projects / Integrations.

    Engagements: posts tagged `solutions` AND `engagement` (not `integrations`),
    as `ul.blog` rows with the free-text `display_date` and a `<div>` excerpt.
    Projects: other `solutions` posts (not engagement/integrations) merged with
    published `project` posts, as the same research cards the collections use.
    """
    solutions = [n for n in blog if "solutions" in n.tags]
    engagements = [
        n for n in solutions if "engagement" in n.tags and "integrations" not in n.tags
    ]
    projects = {
        n.slug: n
        for n in solutions
        if "engagement" not in n.tags and "integrations" not in n.tags
    }
    projects.update({n.slug: n for n in blog if n.published and "project" in n.tags})
    integrations = [n for n in solutions if "integrations" in n.tags]
    by_date = lambda nodes: sorted(nodes, key=lambda n: n.date, reverse=True)  # noqa: E731
    return anthus_page_html.ai_solutions_html(
        engagements=(
            '<ul class="blog">'
            + "".join(
                _blog_item(n, images, date=n.display_date, excerpt_tag="div", image_class="featured")
                for n in by_date(engagements)
            )
            + "</ul>"
        ),
        projects=_grid_html(by_date(list(projects.values())), images),
        integrations=solutions_list(integrations, images, with_image=False),
    )


def ryan_page(solutions: list[ContentNode], images: ImageIndex) -> str:
    """`ryan.js`: its featured filter ignores `integrations`, unlike ai-solutions."""
    featured = [n for n in solutions if "featured" in n.tags]
    plain = [n for n in solutions if "featured" not in n.tags and "integrations" not in n.tags]
    integrations = [n for n in solutions if "featured" not in n.tags and "integrations" in n.tags]
    return anthus_page_html.ryan_html(
        portfolio=(
            solutions_list(featured, images, with_image=True, extra_class="smallImageList")
            + solutions_list(plain, images, with_image=False)
        ),
        integrations=solutions_list(integrations, images, with_image=False),
    )


def not_found_page() -> str:
    return anthus_page_html.not_found_html()


# --------------------------------------------------------------------------
# Collection pages: /reading/ and /research/ (static copy + the two lists)
# --------------------------------------------------------------------------


def collection_nodes(blog: list[ContentNode], tag: str) -> list[ContentNode]:
    """Published, non-platform posts with `tag`; date desc, ties by filename asc."""
    nodes = [
        n for n in blog if n.published and tag in n.tags and not n.is_platform
    ]
    nodes.sort(key=lambda n: n.source.name)
    nodes.sort(key=lambda n: n.date, reverse=True)
    return nodes


_RC = "research-cards-module"


def _research_card(
    node: ContentNode, images: ImageIndex, shows_excerpt_as_headline: bool = False
) -> str:
    href = _esc(blog_href(node))
    preview = _preview(node, images)
    image = ""
    if preview:
        image = (
            f'<a class="{_RC}--imageLink--25731" href="{href}">'
            + anthus_dom.image_html(
                src=preview,
                alt=node.title,
                class_name=f"{_RC}--headlineImage--8f69e",
                eager=False,
            )
            + "</a>"
        )
    repository = _fm(node, "repository")
    code = ""
    if repository:
        label = repository.removeprefix("https://github.com/")
        code = (
            f'<a href="{_esc(repository)}" target="_blank" rel="noopener noreferrer">'
            f"Code: {escape(label)}</a>"
        )
    return (
        f'<li class="{C["platform:card"]}">{image}'
        f'<a class="{C["platform:cardTitleLink"]}" href="{href}"><h3>'
        f"{escape(_headline_from_excerpt_or_title(node) if shows_excerpt_as_headline else node.title)}"
        "</h3></a>"
        f'<div class="{C["platform:metaRow"]}"><span class="{C["platform:pill"]}">'
        f"{escape(node.formatted_date)}</span></div>"
        + ("" if shows_excerpt_as_headline else _excerpt_container("p", "", _excerpt_html(node)))
        + f'<div class="{C["platform:cardActions"]}"><a href="{href}">Read more</a>{code}</div></li>'
    )


def reading_page(blog: list[ContentNode], images: ImageIndex) -> str:
    nodes = collection_nodes(blog, "reading")
    assert collection_page_count(len(nodes)) == 1, "reading outgrew one page"
    featured, earlier = collection_lists(nodes, images)
    return anthus_page_html.reading_html(featured=featured, earlier=earlier)


def research_page(blog: list[ContentNode], images: ImageIndex) -> str:
    nodes = collection_nodes(blog, "research")
    assert collection_page_count(len(nodes)) == 1, "research outgrew one page"
    featured, earlier = collection_lists(nodes, images)
    return anthus_page_html.research_html(featured=featured, earlier=earlier)


def engage_page() -> str:
    return anthus_page_html.engage_html()


def decision_models_page() -> str:
    return anthus_page_html.decision_models_html()


def benchmarks_page() -> str:
    return anthus_page_html.benchmarks_html()
