"""Anth.us page templates in the arcade design language (web/DESIGN.md).

Each generator returns the **inner HTML of `<main>`** for one page. Pages are
generated HTML rather than Markdown because they use the site's own component
vocabulary (`arcade.css`): page hero, section header, cards, steps, timeline.
Only the MDX corpus (articles and platform-product bodies) goes through Markus.

| Page                    | Generator                                   |
| ----------------------- | ------------------------------------------- |
| `/`                     | `homepage`                                  |
| `/about/`               | `about_page`                                |
| `/ai-solutions/`        | `ai_solutions_page`                         |
| `/ryan/`                | `ryan_page`                                 |
| `/engage/`              | `engage_page`                               |
| `/decision-models/`     | `decision_models_page`                      |
| `/benchmarks/`          | `benchmarks_page`                           |
| `/research/` `/reading/`| `research_page`, `reading_page`             |
| `/platform/`            | `platform_index`                            |
| `/platform/<product>/`  | `platform_product_head`, `..._tail`         |
| `/blog/`, `/posts/`     | `articles_collection`, `posts_collection`   |
| `/tags/`                | `tag_pages`                                 |
| `/404.html`             | `not_found_page`                            |

A page that composes its own full-bleed sections starts with `BARE`; the
envelope (`anthus_dom.render_envelope`) then skips the standard content
container. **Hrefs are emitted in production shape** (`/blog/<slug>/`) and
rewritten to this build's static paths by `build_via_papyrus`.

Copy rules: first person plural, plain and specific, every fact from the
previous page copy or the content front matter (DESIGN.md section 8).
"""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import anthus_dom
import solution_marks
import arcade_pictograms
from anthus_content import ContentNode, ImageIndex
from anthus_urls import FEATURED_COUNT, GRID_SIZE, collection_page_count, tag_slug

BARE = anthus_dom.BARE_MARKER

_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdWlt4KpwPSBHzg3o8fikHcfrzxo5rCcV-0-zDt815NZ1tcyg/viewform"
)
#: The Contact form's "How could we help you?" question (entry.923803174) is its one
#: free-text field, so the four qualification questions travel as a prefilled template
#: in it. The Engage page script fills in the source page and solution from the link.
FORM_ENTRY = "entry.923803174"
FORM_TEMPLATE = (
    "Solution or problem: \n"
    "Rough volume or scale: \n"
    "Do you have an AWS account (yes/no): \n"
    "Timeline: \n"
)

CONTACT_URL = f"{_FORM_URL}?usp=pp_url&{FORM_ENTRY}=" + quote(FORM_TEMPLATE)

#: One sentence, everywhere ownership is stated.
OWNERSHIP = (
    "You own and keep everything we build for you. Our solutions are open source and stay open. Integration code "
    "specific to your project is yours and private, and anything it depends on in our public projects stays public."
)

SITE_TITLE = "Anthus"
SITE_DESCRIPTION = (
    "Anthus builds self-aligning AI systems: custom models, agent harnesses, "
    "evaluation loops, and unattended automation with a human in the loop, "
    "grounded in production operations since 2007."
)

_SHARED_DESCRIPTION = (
    "Anthus builds and operates self-aligning AI systems — custom models, agent harnesses, "
    "and evaluation loops with a human in the loop, grounded in production operations since 2007."
)

#: Production `<title>` text and meta description per page URL.
PAGE_META: dict[str, dict[str, str]] = {
    "/about/": {
        "title": "About Us | Anthus",
        "description": "Anthus builds and operates self-aligning AI systems, grounded in production operations since 2007 — the reliability and security behind a multi-million-dollar platform, now applied to AI.",
    },
    "/ai-solutions/": {"title": "AI Solutions | Anthus", "description": _SHARED_DESCRIPTION},
    "/ryan/": {"title": "Ryan Porter | Anthus", "description": _SHARED_DESCRIPTION},
    "/404.html": {"title": "404: Not Found | Anthus", "description": _SHARED_DESCRIPTION},
    "/engage/": {
        "title": "Engage Anthus | Anthus",
        "description": "What an Anthus engagement looks like: bring any problem you think AI might solve, and we scope a first month with a record you can inspect. Classifier labs, factory-run software, and newsrooms are three examples.",
    },
    "/reading/": {
        "title": "Reading List | Anthus",
        "description": "Papers and books behind the work at Anthus, one short note each on what they say and what we checked.",
    },
    "/research/": {
        "title": "Research | Anthus",
        "description": "Experiments on how Jev, Laya and other decision models actually behave in production: bias, calibration, fine-tuning and distillation, with the method and the measurements.",
    },
    "/decision-models/": {
        "title": "Aligning Jev and Other Decision Models to Your Data | Anthus",
        "description": "You can't fine-tune Jev. Here is how to align a decision model to your own data instead: review its decisions, label the disagreements, calibrate its confidence, change the questions, gate by slice, and distill a classifier you own. Published measurements at every step.",
    },
    "/benchmarks/": {
        "title": "Decision Model Benchmarks: Biased-Decisions and Hard-Decisions | Anthus",
        "description": "Two public benchmarks for decision models: Biased-Decisions measures how often an answer changes when one personal detail changes, and Hard-Decisions measures how accuracy falls as reasoning gets deeper.",
    },
}

# Primary navigation (production href shape); the rendered nav is `anthus_dom.MENU_LINKS`.
MENU = anthus_dom.MENU_LINKS


def _esc(value: str) -> str:
    return escape(str(value), quote=True)


def blog_href(node: ContentNode) -> str:
    """The production route for one article or post."""
    return f"/blog/{node.slug}/"


def platform_href(node: ContentNode) -> str:
    return f"/platform/{node.slug}/"


def article_href(node: ContentNode) -> str:
    return blog_href(node)


def _preview(node: ContentNode, images: ImageIndex) -> str | None:
    """The item's preview image path (listing visual and social-share image)."""
    raw = node.front_matter.get("preview_image")
    if not raw:
        return None
    return images.resolve_path(str(raw), relative_to=node.source)


def _fm(node: ContentNode, key: str) -> str:
    value = node.front_matter.get(key)
    return "" if value in (None, "") else str(value)


def _excerpt_html(node: ContentNode) -> str:
    raw = node.front_matter.get("excerpt")
    return "" if raw is None else str(raw).strip()


# --------------------------------------------------------------------------
# Homepage — src/pages/index.js
# --------------------------------------------------------------------------

# (title, href, pictogram name, body)
_CAPABILITIES = (
    (
        "Knowledge Bases",
        "https://github.com/AnthusAI/Biblicus",
        "knowledge-base",
        "Your agents are only as good as what they can look up. We build knowledge "
        "bases with ontologies and taxonomies that learn from your data, instead of "
        "going stale the week after someone hand-built them.",
    ),
    (
        "Self-Aligning Automation",
        "/blog/call-criteria/",
        "self-aligning",
        "Business process automation with a human in the loop. Reviewers correct it "
        "and say why; the system turns the explanation into a stated policy and "
        "applies it from then on.",
    ),
    (
        "Agent Systems",
        "/blog/give-an-agent-a-tool/",
        "agent-harness",
        "A model is half a system. The other half is the harness: the tools it can "
        "reach, the procedures it follows, the limits it runs inside, and the "
        "ability to work for hours without losing the plot.",
    ),
    (
        "Machine Learning",
        "/decision-models/",
        "confidence-gate",
        "Custom classifiers, fine-tuned models, and decision models like Jev, with "
        "calibrated confidence that tells you which decisions to trust and which to "
        "escalate. We find the cheapest model that clears your bar and run it on AWS.",
    ),
)

# (client, href, pictogram, context, problem, what we did, outcome)
_CASES = (
    (
        "Call Criteria",
        "/blog/call-criteria/",
        "scorecard",
        "Call-center QA, scored by an outside service’s fine-tuned classifiers.",
        "Too expensive and too slow to scale to every new scorecard.",
        "We built their classifier lab on Primus in their own AWS account and ran it for years.",
        "Hundreds of scorecards, millions of calls scored.",
    ),
    (
        "Venue Driver",
        "/blog/venue-driver/",
        "venue-system",
        "Ticketing, VIP table reservations and guest lists for Las Vegas nightlife.",
        "A bespoke, serverless, event-driven system (AWS Lambda, Amplify, SQS), operationally mature.",
        "Integrated with Tao Group’s in-house loyalty system, Madison Square Garden Entertainment’s ServiceNow ITSM, "
        "and a bespoke data warehouse and business intelligence system.",
        "In continuous operation since 2007.",
        ("What it was", "What it integrated", "Outcome"),
        "",
    ),
)

_PRINCIPLES = (
    ("Specs first", "Define behavior before implementation."),
    ("Defense in depth", "Sandboxed tools, CI gates, staged rollouts, and fast rollback."),
    ("Operational feedback", "Telemetry and incident-driven regressions that tighten the loop over time."),
    ("Simplify and delete", "Reduce degrees of freedom to eliminate entire classes of failure."),
)

_STATS = (
    ("$250M", "Processed in production"),
    ("180B", "Tokens of production LLM work"),
    ("~100%", "Uptime"),
    ("2007", "Building production systems since"),
)


def _px(name: str) -> str:
    """Inline pictogram. An unknown name fails the build (no placeholder frames in production)."""
    if name not in arcade_pictograms.NAMES:
        raise KeyError(f"unknown pictogram {name!r}; known: {', '.join(arcade_pictograms.NAMES)}")
    return arcade_pictograms.render(name)


def _eyebrow(number: str, label: str) -> str:
    return f'<p class="eyebrow"><span>{number}</span> <span>/</span> <span>{escape(label)}</span></p>'


def _btn(label: str, href: str, *, ghost: bool = False) -> str:
    cls = "btn btn--ghost" if ghost else "btn"
    return f'<a class="{cls}" href="{_esc(href)}"><span>{escape(label)} &rarr;</span></a>'


def _section(number: str, label: str, heading: str, *, lead: str = "", body: str, head_extra: str = "",
             band: bool = False, stack: bool = False, section_id: str = "") -> str:
    lead_html = f'<p class="lead">{escape(lead)}</p>' if lead else ""
    ident = f' id="{section_id}"' if section_id else ""
    return (
        f'<section class="section{" section--band" if band else ""}"{ident}>'
        f'<div class="container section__grid{" section__grid--stack" if stack else ""}">'
        f'<header class="section__head">{_eyebrow(number, label)}<h2>{escape(heading)}</h2>'
        f"{lead_html}{head_extra}</header>"
        f'<div class="section__body">{body}</div></div></section>'
    )


def _hero() -> str:
    """Split hero: copy on the left, the animated hero pictogram on the right."""
    return (
        '<section class="hero"><div class="container hero__grid"><div class="hero__copy">'
        '<p class="eyebrow">AI ENGINEERING · SINCE 2007</p>'
        '<h1>AI that keeps working after the demo.<span class="cursor" aria-hidden="true"></span></h1>'
        '<p class="lead">We build custom models, agent systems and knowledge bases, run '
        "them in production, and keep them aligned with the people who know the work.</p>"
        '<div class="btn-row">'
        + _btn("Tell us the problem", "/engage/")
        + _btn("See the work", "/ai-solutions/", ghost=True)
        + '</div></div><div class="hero__art">'
        + _px("hero-loop")
        + "</div></div></section>"
    )


def _stats() -> str:
    cells = "".join(
        f'<li><span class="stats__n">{escape(n)}</span><span class="stats__l">{escape(l)}</span></li>'
        for n, l in _STATS
    )
    return f'<div class="stats-wrap"><div class="container"><ul class="stats">{cells}</ul></div></div>'


def _capability_card(title: str, url: str, pictogram: str, body: str) -> str:
    return (
        '<li class="card notch card--link">'
        f'<div class="card__px">{_px(pictogram)}</div>'
        f'<h3><a href="{_esc(url)}">{escape(title)}</a></h3><p>{escape(body)}</p></li>'
    )


def _case_card(client, href, pictogram, context, problem, did, outcome,
               labels=("Problem", "What we did", "Outcome"), footnote="") -> str:
    foot = f'<p class="case__foot">{escape(footnote)}</p>' if footnote else ""
    return (
        '<li class="card notch case card--link">'
        f'<div class="card__px">{_px(pictogram)}</div>'
        f'<h3 class="case__name"><a href="{_esc(href)}">{escape(client)}</a>{solution_marks.mark(client)}</h3>'
        f'<p class="case__ctx">{escape(context)}</p>'
        f"<dl><div><dt>{labels[0]}</dt><dd>{escape(problem)}</dd></div>"
        f"<div><dt>{labels[1]}</dt><dd>{escape(did)}</dd></div>"
        f'<div><dt>{labels[2]}</dt><dd class="case__out">{escape(outcome)}</dd></div></dl>{foot}</li>'
    )


def _platform_tile(node: ContentNode) -> str:
    return (
        '<li class="card notch tile card--link">'
        f'<h3><a href="{_esc(platform_href(node))}">{escape(node.title)}</a></h3>'
        f"<p>{escape(_fm(node, 'excerpt'))}</p></li>"
    )


#: Where each solution came from: (link text, href). Chatticus has no engagement to cite yet.
_SOLUTION_EVIDENCE = {
    "Cyclotron": ("Built from Call Criteria", "/blog/call-criteria/"),
    "Primus": ("Built from Call Criteria", "/blog/call-criteria/"),
    "Papyrus": ("Anth.us runs on it", "/about/#loop"),
}

_SOLUTION_DESCRIPTIONS = {
    "Cyclotron": "It starts on day one with a decision model’s general training, refits a small model on each "
                 "correction, and lets an LLM propose better questions that code tests before they go live. "
                 "The loop is open source under the MIT license.",
    "Chatticus": "A collaborative workplace with named teammates, one shared computer, skills, routines, and human "
                 "approval boundaries.",
    "Papyrus": "Stories move through Kanbus-governed stages from pitch to draft to published, with a human editor "
               "approving each move. Anth.us runs its own newsroom on it, and the board is public.",
    "Primus": "The Anthus MLOps platform and agent incubator: it evaluates, deploys, and continuously improves AI "
              "agents with human feedback in the loop.",
}


def _product_card(name: str, url: str, line: str, pictogram: str, page: str | None, *, describe: bool = False) -> str:
    also = f'<a href="{_esc(page)}">On anth.us</a>' if page else ""
    desc = f"<p>{escape(_SOLUTION_DESCRIPTIONS[name])}</p>" if describe and name in _SOLUTION_DESCRIPTIONS else ""
    if describe:
        # Evidence next to the ask: the engagement the solution came out of, then the way in.
        evidence = _SOLUTION_EVIDENCE.get(name)
        if evidence:
            also += f'<a href="{_esc(evidence[1])}">{escape(evidence[0])}</a>'
        also += f'<a href="/engage/?solution={quote(name)}">Work with us on {escape(name)}</a>'
    return (
        f'<li class="card notch product card--static{" product--desc" if desc else ""}">'
        f'<div class="card__px">{_px(pictogram)}</div><h3 class="product__name">{escape(name)}{solution_marks.mark(name)}</h3>'
        f'<p>{escape(line)}</p>{desc}'
        f'<div class="card__links"><a href="{_esc(url)}" rel="noopener">Visit {escape(name)}</a>{also}</div></li>'
    )


def _products_grid(*, describe: bool = False) -> str:
    return '<ul class="grid grid--products">' + "".join(
        _product_card(*p, describe=describe) for p in anthus_dom.PRODUCTS
    ) + "</ul>"


def _supporting_row() -> str:
    noopener = ' rel="noopener"'
    links = " ".join(
        f'<a href="{_esc(href)}"{noopener if ext else ""}>{escape(name)}</a>'
        for name, href, _line, ext in anthus_dom.SUPPORTING
    )
    return f'<p class="supporting"><strong>Supporting technology</strong> {links}</p>'


def homepage(
    *,
    articles: list[ContentNode],
    posts: list[ContentNode],
    images: ImageIndex,
    blog: list[ContentNode] | None = None,
    platform: list[ContentNode] | None = None,
) -> str:
    """The arcade homepage (HOME-COPY.md)."""
    out = [_hero(), _stats()]

    out.append(
        _section(
            "01", "What we do", "Four kinds of system. One way of running them.",
            lead="Clients usually arrive asking about one of these. The work rarely stays in one box.",
            body='<ul class="grid grid--caps">'
            + "".join(_capability_card(*c) for c in _CAPABILITIES)
            + "</ul>",
        )
    )

    out.append(
        _section(
            "02", "Proof", "Systems that ran for years, not weeks.",
            body='<ul class="grid grid--2">'
            + "".join(_case_card(*c) for c in _CASES)
            + '</ul><p class="more"><a href="/ai-solutions/">All engagements</a></p>',
            band=True,
            stack=True,
        )
    )

    principles = "".join(
        f"<li><span>{i:02d}</span><strong>{escape(name)}</strong><p>{escape(text)}</p></li>"
        for i, (name, text) in enumerate(_PRINCIPLES, 1)
    )
    out.append(
        _section(
            "03", "How we work", "AI-built, and checked harder because of it.",
            body='<div class="prose-block">'
            "<p>In February 2026 our nightly routine was pasting &quot;Continue.&quot; into "
            "four Codex sessions before bed, because nothing else kept the agents going or "
            "told us what they&#x27;d done. "
            '<a href="/about/">That night is on the record.</a> Everything we ship now runs '
            "under specs, tests, staged rollout, and a person who can say no.</p>"
            "<p>We use AI to write code the same way we use it to classify calls: inside a "
            "governor of constraints, feedback loops and human judgment.</p>"
            "<p>Most of that work happens in the open. Our repositories on GitHub show it in "
            "progress, issue by issue and commit by commit, at software-factory pace.</p></div>"
            f'<ol class="principles">{principles}</ol>'
            '<p class="more"><a href="/blog/cybernetic-development/">How we govern AI-built systems</a> '
            f'<a href="{anthus_dom.GITHUB_ORG}" rel="noopener">Watch the work on GitHub</a></p>',
        )
    )

    out.append(
        _section(
            "04", "Solutions", "Solutions we built from the work.",
            lead="Our in-house solutions, from a stack that grew out of real delivery work.",
            body=_products_grid() + _supporting_row()
            + '<p class="more"><a href="/platform/">The whole platform</a> '
            f'<a href="{anthus_dom.GITHUB_ORG}" rel="noopener">Our repositories on GitHub</a></p>',
            band=True,
        )
    )

    posts_items = "".join(
        f'<li><time>{escape(n.display_date)}</time><a href="{_esc(blog_href(n))}">{escape(n.title)}</a></li>'
        for n in posts[:4]
    )
    out.append(
        _section(
            "05", "Writing", "What we’re measuring.",
            body='<ul class="grid grid--list">'
            + "".join(_article_card(n, images) for n in articles[:6])
            + '</ul><p class="more"><a href="/blog/">All articles</a></p>'
            + (
                '<div class="shorter"><h3>Shorter posts</h3><ul>'
                + posts_items
                + '</ul><p class="more"><a href="/posts/">All posts</a></p></div>'
                if posts_items
                else ""
            ),
        )
    )

    out.append(
        '<section class="section section--band cta-band"><div class="container cta-band__in">'
        '<div><p class="eyebrow">PRESS START</p><h2>Bring us the problem.</h2>'
        '<p class="lead">Even if you can’t yet say what you need. Working that out is part of '
        "the first month, and it’s often the most useful part.</p></div>"
        '<div class="btn-row">' + _btn("Tell us the problem", "/engage/") + "</div></div></section>"
    )
    return "".join(out)



# --------------------------------------------------------------------------
# Shared page components (inner pages)
# --------------------------------------------------------------------------


def _page(*parts: str) -> str:
    return BARE + "".join(parts)


def _page_hero(
    eyebrow: str,
    title: str,
    lead_html: str,
    *,
    art: str = "",
    actions: str = "",
    compact: bool = False,
    cursor: bool = True,
) -> str:
    """Page hero: eyebrow, Jersey 25 h1, lead, optional art (pictogram or photo) from 64rem."""
    solo = "" if art else " hero__grid--solo"
    cur = '<span class="cursor" aria-hidden="true"></span>' if cursor else ""
    art_html = f'<div class="hero__art">{art}</div>' if art else ""
    return (
        f'<section class="hero hero--page{" hero--compact" if compact else ""}">'
        f'<div class="container hero__grid{solo}"><div class="hero__copy">'
        f'<p class="eyebrow">{escape(eyebrow)}</p><h1>{escape(title)}{cur}</h1>'
        + (f'<p class="lead">{lead_html}</p>' if lead_html else "")
        + (f'<div class="btn-row">{actions}</div>' if actions else "")
        + f"</div>{art_html}</div></section>"
    )


def _cta(title: str = "Bring us the problem.", lead: str = "", *, label: str = "Tell us the problem",
         href: str = "/engage/") -> str:
    lead = lead or (
        "Even if you can’t yet say what you need. Working that out is part of "
        "the first month, and it’s often the most useful part."
    )
    return (
        '<section class="section section--band cta-band"><div class="container cta-band__in">'
        f'<div><p class="eyebrow">PRESS START</p><h2>{escape(title)}</h2>'
        f'<p class="lead">{lead}</p></div>'
        f'<div class="btn-row">{_btn(label, href)}</div></div></section>'
    )


def _chips(items: list[tuple[str, str]]) -> str:
    return '<ul class="chips">' + "".join(
        f'<li><a class="chip" href="{_esc(h)}">{escape(t)}</a></li>' if h else f'<li><span class="chip">{escape(t)}</span></li>'
        for t, h in items
    ) + "</ul>"


def _links(items: list[tuple[str, str]]) -> str:
    return '<div class="card__links">' + "".join(
        f'<a href="{_esc(h)}">{escape(t)}</a>' for t, h in items
    ) + "</div>"


def _card(title: str, body_html: str, *, href: str = "", extra: str = "", cls: str = "") -> str:
    """A plain notched card; with `href` the whole card is the click target."""
    head = f'<h3><a href="{_esc(href)}">{escape(title)}</a></h3>' if href else f"<h3>{escape(title)}</h3>"
    return (
        f'<li class="card notch {cls}{" card--link" if href else " card--static"}">'
        f"{head}{body_html}{extra}</li>"
    )


def _qa_card(question: str, answer_html: str, links: list[tuple[str, str]] | None = None) -> str:
    return _card(
        question,
        f"<p>{answer_html}</p>",
        extra=_links(links) if links else "",
        cls="card--qa",
    )


def _steps(items: list[tuple[str, str]]) -> str:
    return '<ol class="steps">' + "".join(
        f"<li><div><strong>{escape(t)}</strong><p>{body}</p></div></li>" for t, body in items
    ) + "</ol>"


def _prose(*paragraphs: str) -> str:
    return '<div class="prose">' + "".join(f"<p>{p}</p>" for p in paragraphs) + "</div>"


def _short_date(node: ContentNode) -> str:
    """YYYY-MM-DD for the card meta line, however the front matter spells the date."""
    raw = node.date_raw
    return node.date.strftime("%Y-%m-%d") if "T" in raw and node.date.year > 1 else raw


_HIDDEN_TAGS = frozenset({"featured", "solutions", "engagement", "integrations"})


def _card_visual(node: ContentNode, images: ImageIndex | None, eager: bool = False, draft: bool = False) -> str:
    """The 16:10 visual slot of a listing card.

    A `pictogram:` front-matter name wins (inline, animated, follows light/dark);
    else the item's preview image (shown whole, `contain`, unless its aspect is within
    ~10% of 16:10); else a first-letter tile so cards still align.
    """
    name = anthus_dom.node_pictogram(node)
    if name:
        return f'<div class="acard__vis acard__vis--px">{arcade_pictograms.render(name)}</div>'
    src = _preview(node, images) if images is not None else None
    if src:
        size = anthus_dom._dimensions(src)
        dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
        fit = " acard__vis--cover" if size and abs(size[0] / size[1] / 1.6 - 1) <= 0.10 else ""
        load = "eager" if eager else "lazy"
        decode = "" if draft else ' decoding="async"'  # draft cards are revealed late: decode synchronously
        return (
            f'<div class="acard__vis{fit}"><img src="{_esc(src)}" alt="" loading="{load}"{decode}{dims}></div>'
        )
    letter = next((c for c in node.title if c.isalnum()), "A").upper()
    return f'<div class="acard__vis acard__vis--letter" aria-hidden="true"><span>{escape(letter)}</span></div>'


def _text_card(
    node: ContentNode,
    images: ImageIndex | None = None,
    *,
    headline: bool = False,
    display_date: bool = False,
    link: bool = True,
    code: bool = True,
    eager: bool = False,
    draft: bool = False,
) -> str:
    """The listing card: visual, mono date + tags, Jersey 25 title, clamped excerpt.

    `headline`: posts, whose excerpt is the headline (no separate excerpt).
    """
    tags = [t for t in node.tags if t not in _HIDDEN_TAGS][:2]
    date = node.display_date if display_date else _short_date(node)
    meta = f"<time>{escape(date)}</time>" + "".join(f"<span>#{escape(t)}</span>" for t in tags)
    if draft:
        meta = '<span class="pill pill--draft">DRAFT</span>' + meta
    nofollow = ' rel="nofollow"' if draft else ""
    title = (node.excerpt_text.strip() or node.title) if headline else node.title
    target = str(node.front_matter.get("external_url") or blog_href(node))
    heading = f'<h3><a href="{_esc(target)}"{nofollow}>{escape(title)}</a></h3>' if link else f"<h3>{escape(title)}</h3>"
    excerpt = "" if headline else f'<p class="acard__ex">{escape(node.excerpt_text)}</p>'
    repository = _fm(node, "repository") if code else ""
    extra = ""
    if repository:
        label = repository.removeprefix("https://github.com/")
        extra = (
            '<div class="card__links"><a href="'
            f'{_esc(repository)}" target="_blank" rel="noopener noreferrer">Code: {escape(label)}</a></div>'
        )
    foot = '<span class="card__link" aria-hidden="true">Read</span>' if link else ""
    cls = "card--link" if link else "card--static"
    return (
        f'<li class="card notch acard {cls}">{_card_visual(node, images, eager, draft)}<div class="acard__body">'
        f'<p class="acard__meta">{meta}</p>{heading}{excerpt}{extra}{foot}</div></li>'
    )


def _article_card(node: ContentNode, images: ImageIndex | None = None) -> str:
    return _text_card(node, images, code=False)


def _drafts_section(drafts: list[ContentNode] | None, images: ImageIndex | None) -> str:
    """Hidden review section: shown only by `drafts.js` when the URL has `?drafts`. No UI links to it."""
    if not drafts:
        return ""
    cards = "".join(_text_card(n, images, code=False, draft=True) for n in drafts)
    return (
        '<section class="drafts-review" hidden><div class="container">'
        '<p class="eyebrow">NOT PUBLISHED</p><h2>Drafts</h2>'
        "<p>Served but hidden from search engines and from the normal lists.</p>"
        f'<ul class="grid grid--list">{cards}</ul></div></section>'
    )


def _card_grid(nodes: list[ContentNode], images: ImageIndex | None = None, **kw) -> str:
    if not nodes:
        return ""
    return '<ul class="grid grid--list">' + "".join(
        _text_card(n, images, eager=i < 3, **kw) for i, n in enumerate(nodes)
    ) + "</ul>"


# --------------------------------------------------------------------------
# Collections: /blog/, /posts/, /research/, /reading/ and their pages
# --------------------------------------------------------------------------

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


def collection_slices(nodes: list[ContentNode], page: int):
    """(featured, grid) node lists for one page of a collection."""
    if page == 1:
        return nodes[:FEATURED_COUNT], nodes[FEATURED_COUNT : FEATURED_COUNT + GRID_SIZE]
    start = FEATURED_COUNT + GRID_SIZE + (page - 2) * GRID_SIZE
    return [], nodes[start : start + GRID_SIZE]


def collection_nav(title: str, base: str, page: int, total: int) -> str:
    """The pagination `<nav>`, rendered only when there is more than one page."""
    if total <= 1:
        return ""
    previous = (
        f'<a href="{_esc(collection_page_path(base, page - 1))}">&larr; Previous</a>'
        if page > 1
        else "<span></span>"
    )
    following = (
        f'<a href="{_esc(collection_page_path(base, page + 1))}">Next &rarr;</a>'
        if page < total
        else "<span></span>"
    )
    return (
        f'<nav class="pager" aria-label="{escape(title)} pagination">'
        f"{previous}<span>Page {page} of {total}</span>{following}</nav>"
    )


def collection_page(
    title: str,
    base: str,
    nodes: list[ContentNode],
    page: int,
    images: ImageIndex | None = None,
    shows_excerpt_as_headline: bool = False,
    *,
    eyebrow: str | None = None,
    drafts: list[ContentNode] | None = None,
) -> str:
    """A listing page: hero, an intrinsic grid of text cards, pager."""
    total = collection_page_count(len(nodes))
    featured, grid = collection_slices(nodes, page)
    shown = featured + grid
    heading = title if page == 1 else f"{title}, page {page}"
    return _page(
        _page_hero(
            eyebrow or title.upper(), heading, escape(COLLECTION_DESCRIPTIONS.get(title, "")),
            compact=True,
        ),
        '<section class="section section--tight"><div class="container">'
        + _card_grid(shown, images, headline=shows_excerpt_as_headline, code=False)
        + collection_nav(title, base, page, total)
        + "</div></section>"
        + (_drafts_section(drafts, images) if page == 1 else ""),
    )


def articles_collection(
    articles: list[ContentNode], images: ImageIndex | None = None, drafts: list[ContentNode] | None = None
) -> dict[int, str]:
    total = collection_page_count(len(articles))
    return {p: collection_page("Articles", "blog", articles, p, images, drafts=drafts) for p in range(1, total + 1)}


def posts_collection(
    posts: list[ContentNode], images: ImageIndex | None = None, drafts: list[ContentNode] | None = None
) -> dict[int, str]:
    total = collection_page_count(len(posts))
    return {
        p: collection_page("Posts", "posts", posts, p, images, shows_excerpt_as_headline=True, drafts=drafts)
        for p in range(1, total + 1)
    }


def collection_nodes(blog: list[ContentNode], tag: str) -> list[ContentNode]:
    """Published, non-platform posts with `tag`; date desc, ties by filename asc."""
    nodes = [n for n in blog if n.published and tag in n.tags and not n.is_platform]
    nodes.sort(key=lambda n: n.source.name)
    nodes.sort(key=lambda n: n.date, reverse=True)
    return nodes


def _single_page_collection(
    title: str, eyebrow: str, nodes: list[ContentNode], lead_html: str, base: str, images,
    drafts: list[ContentNode] | None = None,
) -> str:
    assert collection_page_count(len(nodes)) == 1, f"{base} outgrew one page"
    return _page(
        _page_hero(eyebrow, title, lead_html, compact=True),
        '<section class="section section--tight"><div class="container">'
        + _card_grid(nodes, images)
        + "</div></section>"
        + _drafts_section(drafts, images),
    )


def reading_page(blog: list[ContentNode], images: ImageIndex | None = None) -> str:
    return _single_page_collection(
        "Reading list", "WHAT WE READ", collection_nodes(blog, "reading"),
        escape(COLLECTION_DESCRIPTIONS["Reading List"]), "reading", images,
        [n for n in blog if n.draft and "reading" in n.tags and not n.is_platform],
    )


def research_page(blog: list[ContentNode], images: ImageIndex | None = None) -> str:
    return _single_page_collection(
        "Research", "EXPERIMENTS", collection_nodes(blog, "research"),
        "Jev, Laya and the rest of the field-coverage roster answer millions of bounded "
        "questions a day, so we run the experiments that check what they’re actually doing: "
        "where their verdicts move on a name or a pronoun, how well their confidence tracks "
        "reality, and what survives when you fine-tune, distill or gate them. Every piece here "
        "comes with the method and the numbers, not just the headline. If you’re here to align "
        'Jev or another decision model to your own data, start with the '
        '<a href="/decision-models/">guide to aligning decision models</a>.',
        "research", images,
        [n for n in blog if n.draft and "research" in n.tags and not n.is_platform],
    )


def tag_pages(tags: dict[str, list[ContentNode]], images: ImageIndex | None = None) -> dict[str, tuple[str, str]]:
    """Returns `{slug: (label, html)}`; `index` is the tag cloud.

    Production mounts these at `/blog/<tag>`, which shares a namespace with
    article slugs; this build uses `/tags/<tag>` so a tag can never shadow an
    article. The corpus also tags both `AI` and `ai`, which are the same tag to
    a reader, so case variants are merged rather than one overwriting the other.
    """
    merged: dict[str, tuple[str, list[ContentNode]]] = {}
    for tag, nodes in tags.items():
        slug = tag_slug(tag)
        label, existing = merged.get(slug, (tag.strip(), []))
        combined = {node.slug: node for node in existing}
        combined.update({node.slug: node for node in nodes})
        if len(nodes) > len(existing):
            label = tag.strip()
        merged[slug] = (label, list(combined.values()))

    pages: dict[str, tuple[str, str]] = {}
    for slug, (label, nodes) in sorted(merged.items()):
        ordered = sorted(nodes, key=lambda n: (n.date, n.slug), reverse=True)
        pages[slug] = (
            f"Articles tagged with: {label}",
            _page(
                _page_hero(
                    "TAG", f"Tagged: {label}",
                    f'{len(ordered)} {"article" if len(ordered) == 1 else "articles"}. '
                    '<a href="/tags/">All tags</a>.',
                    compact=True, cursor=False,
                ),
                '<section class="section section--tight"><div class="container">'
                + _card_grid(ordered, images, code=False)
                + "</div></section>",
            ),
        )

    cloud = "".join(
        f'<li><a class="chip" href="/tags/{_esc(slug)}/">{escape(label)}<small>{len(nodes)}</small></a></li>'
        for slug, (label, nodes) in sorted(merged.items())
    )
    pages["index"] = (
        "Tags",
        _page(
            _page_hero("TOPICS", "Tags", "Every topic we write about, with the number of pieces under each.",
                       compact=True),
            f'<section class="section section--tight"><div class="container"><ul class="chips">{cloud}</ul>'
            "</div></section>",
        ),
    )
    return pages
# --------------------------------------------------------------------------
# Platform constants, carried over unchanged from the Markdown-era module.
# --------------------------------------------------------------------------

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
        "Korporus supplies the shared shell while solution-specific modules from "
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


# --------------------------------------------------------------------------
# About
# --------------------------------------------------------------------------

_HISTORY = (
    ("2007", "The platform starts running",
     "Ryan Porter becomes CTO of Venue Driver, a hospitality technology startup, and builds and runs all of its "
     "technology. The system has been in continuous operation since."),
    ("2009", "A world tour",
     'Ryan builds an event ticket sales system for a <a href="https://en.wikipedia.org/wiki/Kaleidoscope_World_Tour">'
     "Tiësto world tour</a>. It sparks a business that generated up to $64 million annually."),
    ("2014", "Hakkasan Group",
     "Hakkasan Group acquires Angel Management Group together with Venue Driver, which Angel Management Group had "
     "created as a spin-off. The business grows from a tiny startup into a department of a large multinational. We integrate third-party "
     "platforms, including Salesforce, Marketo, Salesforce Marketing Cloud, Mailchimp and Paytronix, and build an "
     "enterprise data warehouse."),
    ("2021", "Tao Group Hospitality",
     'Under <a href="https://taogroup.com">Tao Group Hospitality</a> and its parent, Madison Square Garden '
     "Entertainment, the platform passes rigorous audits and moves from a monolith to a serverless distributed "
     "architecture, then is handed to the next team with no business interruption."),
    ("2024", "Anthus",
     "The team that has worked together for more than a decade turns full time to the intersection of software "
     "and artificial intelligence. The Anthus name is the only new thing."),
    ("2026", "The night we stopped being the loop",
     'In February, the nightly routine of pasting “Continue.” into agent sessions before bed breaks the '
     'chat way of working. <a href="#loop">The story is below.</a>'),
)

_HELD_UP = (
    ("What it was",
     "A bespoke ticketing, VIP table reservation and guest list system: serverless (AWS Lambda and Amplify), "
     "event-driven (SQS queues), and operationally mature."),
    ("What it integrated",
     "Tao Group’s in-house loyalty system, Madison Square Garden Entertainment’s ITSM (ServiceNow), and a bespoke "
     "data warehouse and business intelligence system."),
    ("Never breached",
     'The hackers never got us, despite being a <a href="https://twitter.com/RyanAlynPorter/status/890982980721790976">'
     "prime target</a>."),
    ("Everything else",
     "Massive DDoS attacks, primary database server failures, silent failures in third-party systems, and "
     "everything else you could imagine. We always kept the revenue flowing."),
)

_OPS_FOOTNOTE = (
    "A catastrophic failure once took out an entire AWS data center. We moved the whole system to a new one "
    "within hours, and it was back up before the doors opened, so ticket scanning at the venues went ahead "
    "without a hitch."
)

_VALUES = (
    ("Prioritize solutions over tools",
     "Products and services only deliver business value if you’re in the business of products and services. "
     "We’re in the business of solutions."),
    ("Focus on business logic",
     'The only code you should write is the business logic that solves real problems. '
     '<a href="/blog/langchain-by-example/">Don’t waste time reinventing wheels.</a>'),
    ("Continuously improve",
     "Rapid, iterative change through CI/CD and DevOps, then let the systems improve themselves. Self-optimizing "
     "classifiers and self-steering agent systems get better from production feedback without waiting for an "
     "engineer to notice."),
    ("Infrastructure as code",
     "DevOps for infrastructure, MLOps and LLMOps for the models. Every part of a production system, including "
     "training runs and evaluations, should be created by code so it’s reproducible, not clicked together by hand."),
    ("Commodify AI models",
     "Treat models as replaceable, not magic black boxes. In a world with no moats, "
     '<a href="/blog/a-world-with-no-moats/">don’t invest too much in any given castle.</a>'),
    ("Optimize resource usage",
     "Balance efficiency with cost-effectiveness. When intelligence is cheap, the goal shifts from conserving "
     "compute to conserving context and cognitive load."),
)

_FACTS = (
    ("Company name", "Anthus AI Solutions"),
    ("Type", "AI engineering and operations company"),
    ("Founder", '<a href="/ryan/">Ryan Porter</a>'),
    ("Website", '<a href="/">anth.us</a>'),
    ("Core offering", "Self-aligning AI systems: custom models, agent harnesses, and evaluation loops with a human in the loop"),
    ("Services", "LLM fine-tuning, agentic AI, MLOps and LLMOps, serverless architecture, AI-assisted operations"),
    ("Track record", "Team together for over a decade; revenue-critical platforms in continuous operation since 2007; "
                     "a call-center QA classifier lab run on Primus for years, across hundreds of scorecards and millions of interactions"),
    ("Platform", '<a href="/platform/primus/">Primus</a>, an MLOps platform'),
    ("Spinoff", "Anthus Microelectronics (B0rd LED-matrix desk display)"),
    ("Contact", '<a href="/ryan/">anth.us/ryan</a>'),
)

_FAQ = (
    ("What does Anthus build?",
     "Production AI systems that improve from feedback: fine-tuned classifiers, agent systems, and the evaluation "
     "and MLOps infrastructure around them. We also operate what we build."),
    ("How is Anthus different from a typical AI consultancy?",
     "We are operators first. The team has run a revenue-critical platform since 2007, through data center failures "
     "and DDoS attacks, before applying the same discipline to AI. We ship systems with human-in-the-loop feedback, not demos."),
    ("What is human-in-the-loop AI?",
     "Experts review and correct the AI’s judgments, and those corrections become training signal. In the "
     'Call Criteria classifier lab, QA specialists guide the models this way, and the scorecards have improved '
     "through reinforcement learning from human feedback (RLHF) over years of production, across hundreds of "
     "scorecards and millions of interactions."),
    ("Do you only work with one model provider?",
     "No. We treat models as replaceable components and design systems so a model can be swapped without "
     "rebuilding the business logic."),
)


def about_page() -> str:
    timeline = '<ol class="tl">' + "".join(
        f'<li><p class="tl__when">{when}</p><div class="tl__what"><h3>{escape(title)}</h3><p>{body}</p></div></li>'
        for when, title, body in _HISTORY
    ) + "</ol>"
    founder = (
        '<p class="founder"><span><strong>Ryan Porter</strong> founded the business and leads Anthus. '
        '<a href="/ryan/">Read his story &rarr;</a></span></p>'
    )
    held = '<ul class="grid grid--thirds">' + "".join(_card(t, f"<p>{b}</p>") for t, b in _HELD_UP) + "</ul>"
    values = '<ul class="principles principles--auto">' + "".join(
        f"<li><span>{i:02d}</span><strong>{escape(t)}</strong><p>{b}</p></li>" for i, (t, b) in enumerate(_VALUES, 1)
    ) + "</ul>"
    loop_cards = '<ul class="grid grid--thirds">' + "".join(
        _card(name, f"<p>{body}</p>", href=href)
        for name, body, href in (
            ("Tactus",
             "Names the three ways a person can be in the loop, supervised, unattended and asynchronous, and makes the "
             "third one programmable: an agent runs on its own and interrupts a human only at a decision point.",
             "/platform/tactus/"),
            ("Kanbus",
             "The memory that lets work move between Claude Code, Codex, or whatever comes next. We’ve held since 2023 "
             "that models are commodities.",
             "/platform/kanbus/"),
            ("Primus",
             "The scorecard where reviewers correct a decision model’s verdicts and their explanations become policy.",
             "/platform/primus/"),
        )
    ) + "</ul>"
    tweet = (
        '<blockquote class="post"><p>Stupid new nightly routine that I never wanted: Pasting “Continue.” into Codex '
        "20 times in a row before I go to bed, in four different sessions. I will look back at this like black and "
        "white television. Rotary phone dials.</p><footer>Ryan Porter (@RyanAlynPorter), "
        '<a href="https://x.com/RyanAlynPorter/status/2019302489011696010">February 5, 2026</a></footer></blockquote>'
    )
    build_today = '<ul class="grid grid--2">' + _card(
        "Cybernetic development",
        "<p>The AI era doesn’t remove the need for operational excellence, it raises the stakes. We use a cybernetic "
        "approach: clear intent, layered safeguards, and production feedback loops that continuously harden the system. "
        "Delegating the work turned out to be easy; observing it is the whole job.</p>",
        extra=_links([("Read Cybernetic Development", "/blog/cybernetic-development/")]),
    ) + _card(
        "Spinoff: Anthus Microelectronics",
        "<p>Running AI agents all day moved the bottleneck from writing code to monitoring and steering the agents. "
        "Sitting at a terminal all day is not the answer, so we built desk displays: handbuilt microelectronics running "
        "a custom, AI-assisted OS. The first product is <strong>B0rd</strong>, a standalone LED-matrix display for "
        "glanceable information (launch countdowns, agent status, notifications, an idle clock) that matching units "
        "keep in sync without pairing or a hub.</p>",
        extra=_links([("B0rd solution page", "/blog/b0rd/"), ("b0rd.info", "https://b0rd.info"),
                      ("Etsy shop", "https://www.etsy.com/shop/AnthusMicronics")]),
    ) + "</ul>"
    who = '<ul class="grid grid--thirds">' + "".join(
        _card(t, f"<p>{b}</p>") for t, b in (
            ("Product and engineering teams", "Putting LLM agents or classifiers into production, not just prototypes."),
            ("Operations and QA organizations",
             'That need AI to make judgments at scale while experts stay in control (the <a href="/blog/call-criteria/">'
             "Call Criteria</a> pattern)."),
            ("Revenue-critical businesses", "Where downtime, security incidents, and silent failures are unacceptable."),
        )
    ) + "</ul>"
    facts = '<dl class="facts">' + "".join(f"<div><dt>{escape(k)}</dt><dd>{v}</dd></div>" for k, v in _FACTS) + "</dl>"
    faq = '<ul class="grid grid--qa">' + "".join(_qa_card(q, escape(a)) for q, a in _FAQ) + "</ul>"
    return _page(
        _page_hero(
            "ABOUT ANTHUS", "About us",
            "We are an AI engineering company that builds and operates self-aligning AI systems (custom models, agent "
            "harnesses, and evaluation loops with a human in the loop) for teams that need them to keep working in production.",
            art=_px("timeline"),
        ),
        _section(
            "01", "History", "Since 2007",
            lead="We came together as a team as the business expanded, and we have worked cohesively for more than a decade.",
            body=timeline + founder, stack=False,
        ),
        _section("02", "Track record", "What held up",
                 lead="An impeccable record in reliability and security, kept through every technology shift: cloud computing, serverless, and now AI.",
                 body=held + '<aside class="opsnote"><div class="opsnote__px">' + _px("relocate") + "</div>"
                 '<div><p class="opsnote__h">When an AWS data center failed</p><p>' + _OPS_FOOTNOTE + "</p></div></aside>",
                 band=True),
        _section(
            "03", "Mission", "What we’re here to do",
            body=(
                '<p class="statement">Deliver <span>reliable, secure, and efficient</span> business solutions using '
                "collaboration between human and artificial intelligence in every aspect of development and operations.</p>"
                '<div class="prose"><p>We build systems that keep working when nobody is watching.</p></div>'
            ),
        ),
        _section("04", "Values", "How we decide", body=values, band=True, section_id="our-values"),
        _section(
            "05", "February 2026", "The night we stopped being the loop",
            body=_prose(
                "When we started using AI to write the code and make the decisions, the chat way of working broke under "
                "the volume. A person had to sit there keeping the agents going or the whole process stopped, and a "
                "person had to hold in their head what was happening across every parallel session in every project for "
                "every client, because nothing else did. The low point is on the record, like everything else we do."
            ) + tweet + _prose("So we stopped being the loop. We ran all of it on our own work first, in public.") + loop_cards,
            section_id="loop",
        ),
        _section("06", "Now", "How we build today", body=build_today, band=True),
        _section("07", "Clients", "Who we work with", body=who),
        _section("08", "Facts", "Key facts", body=facts + '<h3 class="subhead">Questions</h3>' + faq, band=True),
        _cta("What can we develop and operate for you?"),
    )


# --------------------------------------------------------------------------
# AI Solutions
# --------------------------------------------------------------------------

_BUILD = (
    ("Knowledge Bases", "https://github.com/AnthusAI/Biblicus",
     "Ontologies and taxonomies that learn from your data instead of going stale.", "See Biblicus"),
    ("Self-Aligning Automation", "/blog/call-criteria/",
     "Systems that improve from production feedback, with a human in the loop.", "See the Call Criteria case study"),
    ("Agent Systems", "/blog/give-an-agent-a-tool/",
     "Durable, governed agent procedures with sandboxed tools and rollback.", "See the approach"),
    ("Machine Learning and Decision Models", "/blog/domain-specific-turn-detection/",
     "Custom models, fine-tuned classifiers, and hosted decision models like Jev, aligned to your business.", "See the work"),
)

_LIFECYCLE = (
    ("Scope", ("Define the use case",)),
    ("Deploy", ("Deploy a basic proof-of-concept application scaffold",)),
    ("Select model(s)", ("Choose an existing model", "Or train a new model")),
    ("Adapt and align model(s)", ("Prompt engineering", "Fine-tuning", "Human feedback", "Evaluation")),
    ("Application integration", ("Augment the model(s)", "Optimize deployment for inference and long-term management")),
)


def ai_solutions_page(blog: list[ContentNode], images: ImageIndex | None = None) -> str:
    """Engagements / Projects / Integrations from the content tags.

    Engagements: `solutions` + `engagement` (not `integrations`). Projects: other
    `solutions` posts plus published `project` posts. Integrations: `solutions` + `integrations`.
    """
    solutions = [n for n in blog if "solutions" in n.tags and not n.draft]
    engagements = [n for n in solutions if "engagement" in n.tags and "integrations" not in n.tags]
    integrations = [n for n in solutions if "integrations" in n.tags]
    projects = {
        n.slug: n for n in solutions if "engagement" not in n.tags and "integrations" not in n.tags
    }
    projects.update({n.slug: n for n in blog if n.published and "project" in n.tags})
    featured = {n.slug: n for n in blog if n.published and "featured" in n.tags and not n.is_platform
                and not ({"solutions", "posts"} & set(n.tags))}
    by_date = lambda nodes: sorted(nodes, key=lambda n: n.date, reverse=True)  # noqa: E731
    reading = by_date(list({**projects, **featured}.values()))[:6]

    build = '<ul class="grid grid--2">' + "".join(
        _card(t, f"<p>{b}</p>", href=h, extra=f'<span class="card__link" aria-hidden="true">{escape(cta)}</span>')
        for t, h, b, cta in _BUILD
    ) + "</ul>"
    supporting = '<ul class="grid grid--thirds">' + "".join(
        _card(
            name, f"<p>{escape(line)}</p>",
            extra=_links(
                ([("Visit " + name, href)] if ext else [])
                + ([("On anth.us", f"/platform/{name.lower()}/")] if name in anthus_dom.SUPPORTING_PAGES else [])
            ),
        )
        for name, href, line, ext in anthus_dom.SUPPORTING
    ) + "</ul>"
    stages = '<ol class="grid grid--thirds">' + "".join(
        f'<li class="card notch card--static card--stage"><span class="stage__no">{i:02d}</span><h3>{escape(t)}</h3>'
        '<ul class="list">' + "".join(f"<li>{escape(x)}</li>" for x in items) + "</ul></li>"
        for i, (t, items) in enumerate(_LIFECYCLE, 1)
    ) + "</ol>"
    chips = _chips([(n.title, "") for n in by_date(integrations)])
    read_list = '<div class="shorter shorter--flat"><ul>' + "".join(
        f'<li><time>{escape(n.display_date)}</time><a href="{_esc(blog_href(n))}">{escape(n.title)}</a></li>'
        for n in reading
    ) + '</ul><p class="more"><a href="/blog/">All articles</a></p></div>'
    return _page(
        _page_hero(
            "AI SOLUTIONS", "Solving problems using AI",
            "You’re under pressure to deliver AI that works in production, not just in a demo. We build and operate "
            "self-aligning AI systems, and we run our own solutions on the same stack we use for clients.",
            art=_px("self-aligning"),
            actions=_btn("Tell us the problem", "/engage/") + _btn("How an engagement works", "/engage/", ghost=True),
        ),
        _section(
            "01", "Our solutions", "What we built from the work",
            lead="Four in-house solutions, in use on our own work first.",
            body=_products_grid(describe=True), stack=True,
        ),
        _section("02", "Supporting technology", "What the solutions run on", body=supporting, band=True),
        _section("03", "What we build for clients", "Four kinds of system", body=build, stack=True),
        _section(
            "04", "Engagements", "Client work with a business outcome",
            lead="The systems we built, ran, and kept improving in production. The proof is years of production RLHF for "
            "a call-center QA operation: a data flywheel learning from expert feedback across hundreds of scorecards "
            "and millions of interactions.",
            body=_card_grid(by_date(engagements), images, display_date=True)
            + (f'<h3 class="subhead">Integrations we have built</h3>{chips}' if integrations else ""),
            band=True,
        ),
        _section(
            "05", "How we work", "From use case to long-term operation",
            lead="We work under specs, tests, staged rollout, and a person who can say no: "
            "cybernetic development. Every AI application we build follows the same lifecycle. " + OWNERSHIP,
            body=stages + '<p class="more"><a href="/blog/cybernetic-development/">How we govern AI-built systems</a></p>',
            stack=True,
        ),
        _section("06", "Further reading", "Projects and articles", body=read_list, band=True),
        _cta(),
    )


# --------------------------------------------------------------------------
# Ryan
# --------------------------------------------------------------------------

_EXPERIENCE = (
    ("January 2024 – Present", "Anthus AI Solutions", "Lead AI Solutions Architect", "Miami Beach, FL",
     ("Our team has been working together for over a decade, and we have been working on AI solutions for years now. "
      "The Anthus name is the only new thing, as we fully focus on the intersection of software solutions and "
      "artificial intelligence.",), ()),
    ("August 2021 – January 2024", "Tao Group Hospitality", "Vice President of Marketing Technology",
     "New York, NY (remote from Miami Beach, FL)",
     ("Formerly with Hakkasan Group, Angel Management Group, and Venue Driver in an evolving role with the same venture.",),
     ("<strong>Pioneering technical strategy:</strong> developed and operated a critical ticketing system evolving since "
      "2007 into a comprehensive platform for reservation, guest list, and artist booking management.",
      "<strong>Seamless transition and growth:</strong> managed the system’s transition through corporate acquisitions, "
      "maintaining high availability while processing as much as $64 million in revenue per year with no major incidents.",
      "<strong>DevOps and agile leadership:</strong> championed a DevOps culture of rapid iteration and continuous "
      "improvement, aligned closely with business needs.",
      "<strong>Longevity and adaptation:</strong> adapted the platform from early monolithic structures to a modern "
      "serverless distributed architecture, passing AWS Well-Architected audits by multinational corporations.")),
    ("February 2014 – August 2021", "Hakkasan Group", "Vice President of Technology",
     "Las Vegas, NV (remote from Miami Beach, FL)",
     ("Formerly with Angel Management Group, and Venue Driver in an evolving role with the same venture.",),
     ("<strong>Scalable system leadership:</strong> continued advancement of a high-revenue ticketing system on scalable, "
      "fault-tolerant AWS infrastructure, embodying the Well-Architected Framework.",
      "<strong>Data integration initiative:</strong> initiated and delivered an enterprise data warehouse integrating "
      "diverse data systems to support analytics, Salesforce CRM, Marketo and Salesforce Marketing Cloud.")),
    ("October 2013 – February 2014", "Angel Management Group", "Executive Director of Technology",
     "Las Vegas, NV (remote from Miami Beach, FL)",
     ("Formerly with Venue Driver in an evolving role with the same venture. Continuation and expansion of the "
      "existing role at Angel Management Group, which created Venue Driver as a spin-off.",), ()),
    ("2007 – October 2013", "Venue Driver", "CTO", "Miami Beach, FL",
     ("<strong>Startup technology foundation:</strong> built and managed all technology infrastructure for a "
      "hospitality-focused technology startup, evolving the company into a major event ticketing provider.",
      "<strong>Leadership and technical training:</strong> directed software development, web operations, technical "
      "hiring, and training programs, laying the foundation for the eventual acquisition and growth."), ()),
    ("2002 – 2005", "CoolJunkie, LLC", "TechJunkie", "Miami Beach, FL",
     ("A joint venture with Nick McCabe to develop a nightlife production and media company in Miami Beach. The "
      "CoolJunkie.com website and its interactive forums were a pillar of the Miami Beach nightlife scene for years, "
      "before social media. The company also produced events like the BBC Radio One Miami party during the Winter "
      "Music Conference, and events from artists like Pete Tong and Cedric Gervais.",), ()),
    ("1997 – Present", "Endymion Corporation", "President", "Miami Beach, FL",
     ("A small software product company started after graduating, built around a web mail application popular in the "
      "early days of the web, in the days of WebTV and AOL. Developed, licensed and supported a PERL-based web mail "
      "application used by thousands of users, and a Java-based enterprise web mail product.",), ()),
)

_EDUCATION = (
    "Worked as an undergraduate research assistant for Dr. Gerhard X. Ritter and Dr. Mark S. Schmalz on their work in "
    "computer vision using the Image Algebra framework, with funding from the US Department of Defense. One project’s "
    "goal was the automated detection of land mines using multi-spectral imagery, an early predecessor of today’s visual "
    "segmentation models, built on 2D convolution algorithms without modern visual AI. The main job was C++ development.",
    "A related computer vision project aimed at detecting water mines by removing distortion in images from the surface "
    "of the ocean.",
    "Also worked on research by Dr. Panos Livadas on automated code analysis and refactoring tools that foreshadowed "
    "LLM-based coding tools like GitHub Copilot, and as an undergraduate teaching assistant for a class based on the "
    "classic Lisp textbook, The Structure and Interpretation of Computer Programs.",
)


def ryan_page(solutions: list[ContentNode], images: ImageIndex | None = None) -> str:
    """Resume plus portfolio. The featured filter ignores `integrations`, unlike ai-solutions."""
    featured = [n for n in solutions if "featured" in n.tags]
    plain = [n for n in solutions if "featured" not in n.tags and "integrations" not in n.tags]
    integrations = [n for n in solutions if "featured" not in n.tags and "integrations" in n.tags]

    entries = []
    for when, org, role, place, paras, bullets in _EXPERIENCE:
        body = "".join(f"<p>{p}</p>" for p in paras)
        if bullets:
            body += "<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"
        entries.append(
            f'<li><p class="tl__when">{when}</p><div class="tl__what"><h3>{escape(org)}</h3>'
            f'<p class="tl__meta">{escape(role)} · {escape(place)}</p>{body}</div></li>'
        )
    experience = '<ol class="tl tl--wide">' + "".join(entries) + "</ol>"
    education = (
        '<ol class="tl tl--wide"><li><p class="tl__when">1992 – 1997</p><div class="tl__what">'
        '<h3>University of Florida</h3><p class="tl__meta">BS, Computer Science</p>'
        + "".join(f"<p>{escape(p)}</p>" for p in _EDUCATION)
        + "</div></li></ol>"
    )
    photo = (
        '<figure class="hero__photo"><span class="photo-frame"><img class="photo" src="/assets/site/ryan-porter.png" '
        'alt="Ryan Porter, in an illustrated portrait" width="400" height="400"></span></figure>'
    )
    return _page(
        _page_hero(
            "FOUNDER, ANTHUS", "Ryan Porter",
            "Technology leader and architectural innovator with a proven history of developing and operating "
            "mission-critical, high-availability systems that deliver business value. Focused on delivering exciting "
            "AI applications through serverless cloud architectures.",
            art=photo, cursor=False,
        ),
        _section("01", "Experience", "Where I’ve worked", body=experience),
        _section("02", "Education", "Where I studied", body=education, band=True),
        _section("03", "Portfolio", "Systems and projects",
                 body=_card_grid(featured, images, display_date=True) + _card_grid(plain, images, display_date=True, link=False, code=False)),
        _section("04", "Integrations", "What we connect to", body=_card_grid(integrations, images, display_date=True, link=False, code=False), band=True),
        _cta(),
    )


# --------------------------------------------------------------------------
# 404
# --------------------------------------------------------------------------


def not_found_page() -> str:
    return _page(
        _page_hero(
            "ERROR 404", "404: Not found",
            "You just hit a route that doesn’t exist. Try the home page, the articles, or tell us what you were looking for.",
            art=_px("lost-sprite"),
            actions=_btn("Go home", "/") + _btn("Read the articles", "/blog/", ghost=True),
        ),
    )


# --------------------------------------------------------------------------
# Platform: /platform/ and the product-page chrome
# --------------------------------------------------------------------------


def _pills(node: ContentNode) -> str:
    items = [_fm(node, k) for k in ("platform_category", "platform_stage") if _fm(node, k)]
    return '<ul class="pills">' + "".join(f'<li class="pill">{escape(i)}</li>' for i in items) + "</ul>" if items else ""


def _platform_card(node: ContentNode) -> str:
    external = _fm(node, "external_url")
    extra = _links([("Visit site", external)]) if external else '<span class="card__link" aria-hidden="true">Read more</span>'
    return (
        '<li class="card notch card--link">'
        f'<h3><a href="{_esc(platform_href(node))}">{escape(node.title)}</a></h3>'
        f"{_pills(node)}<p>{escape(_fm(node, 'excerpt'))}</p>{extra}</li>"
    )


def _platform_line(node: ContentNode) -> str:
    """Compact entry for the least prominent tier on /platform/: name and one line."""
    return (
        f'<li><a href="{_esc(platform_href(node))}">{escape(node.title)}</a> '
        f"{escape(_fm(node, 'excerpt'))}</li>"
    )


def _platform_cards(nodes: list[ContentNode]) -> str:
    return '<ul class="grid">' + "".join(_platform_card(n) for n in nodes) + "</ul>"


_FLAGSHIP_SLUGS = frozenset({"biblicus"})


def platform_index(platform: list[ContentNode]) -> str:
    """`platform` arrives already sorted by `platform_order`."""
    rest = [n for n in platform if n.slug not in _FLAGSHIP_SLUGS]

    columns = "".join(
        _card(
            title,
            '<ul class="list">' + "".join(f"<li><strong>{name}</strong> {text}</li>" for name, text in items) + "</ul>",
        )
        for title, items in _MAP_COLUMNS
    ) + _card(
        "Operations and media",
        '<ul class="list"><li><strong>Caducus</strong> surfaces operator-facing health and incident signals.</li>'
        "<li><strong>Babulus</strong> and <strong>VideoML</strong> apply the same code-first approach to content and video.</li>"
        "<li>The result is one stack for systems, workflows, and communication.</li></ul>",
    )
    recipes = "".join(_card(title, f"<p>{escape(summary)}</p>") for title, summary in _STACK_RECIPES)
    supporting = '<ul class="grid grid--thirds">' + "".join(
        _card(
            name, f"<p>{escape(line)}</p>",
            extra=_links(
                ([("Visit " + name, href)] if ext else []) + ([("On anth.us", f"/platform/{name.lower()}/")] if name in anthus_dom.SUPPORTING_PAGES else [])
            ),
        )
        for name, href, line, ext in anthus_dom.SUPPORTING
    ) + "</ul>"

    return _page(
        _page_hero(
            "SOLUTIONS AND PLATFORM", "The tools we built doing the work.",
            "<strong>A technology stack that grew out of real delivery work.</strong> "
            "It is not a speculative architecture diagram. This is the stack that emerged from building "
            "RLHF systems, durable agent workflows, retrieval-backed automation, hosted operator applications, "
            "and programmable media pipelines for real engagements. The same controls that matter in production "
            "software matter here: auditability, rollback paths, operator visibility, and clear evaluation loops.",
            art=_px("platform-stack"),
            actions=_btn("See the solutions we deliver", "/ai-solutions/")
            + _btn("Read the cybernetic development thesis", "/blog/cybernetic-development/", ghost=True),
        ),
        _section("01", "Solutions", "Our in-house solutions", body=_products_grid()),
        _section(
            "02", "Supporting technology", "What the solutions run on",
            lead="Smaller tools we use and ship alongside them, all open source.",
            body=supporting + f'<p class="more"><a href="{anthus_dom.GITHUB_ORG}" rel="noopener">All our repositories on GitHub</a></p>', band=True,
        ),
        _section(
            "03", "The rest of the platform", "Also in the platform",
            body='<ul class="also-list">' + "".join(_platform_line(n) for n in rest) + "</ul>",
        ),
        _section(
            "04", "Layers", "How the platform fits together",
            lead="Complete AI systems need more than a model call, so we think about the platform in layers.",
            body='<ul class="grid grid--mini">' + columns + "</ul>"
            + _prose(
                "These are reusable building blocks, not isolated side projects. We combine them differently "
                "depending on the job: QA and evaluation, internal operator tooling, extraction and retrieval "
                "workflows, or outward-facing content systems."
            )
            + '<h3 class="subhead">Common combinations</h3><ul class="grid grid--2">' + recipes + "</ul>",
            band=True,
        ),
        _cta(),
    )


def platform_product_head(node: ContentNode) -> str:
    """Heading block above the Markus-converted product body."""
    external = _fm(node, "external_url")
    visit = (
        f'<a class="btn" href="{_esc(external)}"><span>Visit external site &rarr;</span></a>' if external else ""
    )
    return (
        '<div class="heading ppage-head">'
        '<a class="backlink" href="/platform/">The Anthus Platform</a>'
        '<p class="eyebrow">PART OF THE ANTHUS PLATFORM</p>'
        f"<h1>{escape(node.title)}</h1>{_pills(node)}"
        f'<p class="lead">{escape(_fm(node, "excerpt"))}</p>'
        f'<div class="btn-row">{visit}'
        f'<a class="btn btn--ghost" href="/ai-solutions/"><span>See how it fits our solutions work &rarr;</span></a></div></div>'
    )


def platform_product_tail(node: ContentNode) -> str:
    relationship = PLATFORM_RELATIONSHIPS.get(node.slug)
    if not relationship:
        return ""
    links = _chips([(label, f"/platform/{slug}/") for label, slug in relationship["links"]])
    return (
        '<section class="ptail"><p class="eyebrow">WHERE IT FITS</p>'
        "<h2>Where this fits in the Anthus Platform</h2>"
        f"<p>{escape(relationship['fits'])}</p>{links}"
        '<div class="card notch card--static"><h3>Common combination</h3>'
        f"<p>{escape(relationship['recipe'])}</p></div></section>"
    )


# --------------------------------------------------------------------------
# Engage
# --------------------------------------------------------------------------


def engage_page() -> str:
    examples = '<ul class="grid grid--thirds">' + _card(
        "Classifier lab on Primus",
        "<p>We take a high-volume judgment call your team already makes (a score, a flag, a routing decision) and turn "
        "it into a classifier with confidence gating: the model handles the clear cases and routes the rest to your "
        "reviewers.</p>"
        "<p>We’ve run this pattern for a call-center QA operation across years of production, hundreds of models, and "
        "millions of interactions, with expert feedback compounding into a data flywheel the whole time. You get that "
        "architecture, sized to your judgment task.</p>"
        "<p>The loop itself is now open source as Cyclotron: a cyclotron is "
        "one AI decision that learns from your team’s corrections.</p>",
        extra=_links([("Primus", "https://primus.anth.us"), ("Cyclotron", "https://cyclotron.anth.us/"), ("We build it into your product and run it", "https://cyclotron.anth.us/services")]),
    ) + _card(
        "Factory-run software project",
        "<p>We build your software the way we build our own: work tracked as Kanbus issues in the repository, agents "
        "doing the implementation, and a human approval trail on every merge.</p>"
        "<p>Anthus runs its own projects this way, including this site.</p>",
        extra=_links([("Kanbus", "https://kanb.us")]),
    ) + _card(
        "Newsroom for a publication",
        "<p>We stand up <a href=\"https://p.apyr.us\" rel=\"noopener\">Papyrus</a> as your editorial pipeline: stories move through Kanbus-governed stages from pitch to "
        "draft to published, with a human editor approving each move.</p>"
        "<p>Anth.us runs its own newsroom on it, and the board is public, so you can read the record behind the newest "
        "articles before you buy the pipeline.</p>",
    ) + "</ul>"
    first_month = _steps((
        ("A pilot with fixed scope",
         "One judgment task, one project, or one publication track, scoped before we start. If you don’t know what you "
         "need yet, the first month is discovery, and it ends with a scoped proposal instead of a guess."),
        ("A scorecard or a board you can inspect",
         "The same record we use internally: accuracy by slice, issues moving through Kanbus, or stories moving through "
         "the editorial pipeline."),
        ("A decision point",
         "At the end of the month you have real evidence to decide whether to extend, expand, or stop."),
    ))
    tiers = '<ul class="grid grid--2">' + _card(
        "Open source",
        "<p>The code is public on GitHub. Run it yourself.</p>"
        "<p>Cyclotron, Chatticus, Papyrus and Primus are open source, and so are the technologies under them: "
        "Kanbus, Tactus, Biblicus and Auritus. Each solution has its own site with the repository and a quickstart.</p>",
        extra=_links([("Cyclotron", "https://cyclotron.anth.us/"), ("Primus", "https://primus.anth.us"),
                      ("Papyrus", "https://p.apyr.us"), ("All the solutions", "/ai-solutions/")]),
    ) + _card(
        "We build and run it with you",
        "<p>We deploy it in your AWS account, integrate it with your systems, and operate it. Then we either keep "
        "running it with you or hand it off.</p>"
        "<p>This covers all four solutions, and custom AI work that fits none of them. Tell us the problem and we "
        "start from there.</p>",
        extra=_links([("Tell us the problem", "#tell-us")]),
    ) + "</ul>"
    checklist = (
        '<div class="prose"><p>The form has one open question. Answer these four in it, in a line each. Rough answers '
        "are fine, and “I don’t know yet” is a real answer.</p>"
        "<ol><li><strong>Which solution or problem?</strong> Cyclotron, Chatticus, Papyrus, Primus, or the problem "
        "in your own words.</li>"
        "<li><strong>Rough volume or scale.</strong> Decisions a month, documents, users, whatever fits.</li>"
        "<li><strong>Do you have an AWS account?</strong> Yes or no. We work in yours.</li>"
        "<li><strong>Timeline.</strong> When you need something real in front of your team.</li></ol>"
        f'<div class="btn-row">{_btn("Open the contact form", CONTACT_URL).replace("<a ", "<a data-contact ", 1)}</div></div>'
    )
    return _page(
        _page_hero(
            "ENGAGE ANTHUS", "How an engagement works",
            "Two ways to work with us, and both start with a conversation. Run our open-source solutions yourself, or "
            "have us build and run them with you in your AWS account. Your experts stay in the loop either way. "
            + OWNERSHIP,
            art=_px("engagement-path"),
            actions=_btn("Tell us the problem", "#tell-us"),
        ),
        _section("01", "Two ways in", "Open source, or built and run with you", body=tiers, stack=True),
        _section(
            "02", "Where we start", "Three examples",
            lead="These are shapes engagements often take. They aren’t a menu. Most real problems don’t fit one box, "
            "and we take on AI solutions work of any kind.",
            body=examples, stack=True, band=True,
        ),
        _section("03", "Month one", "What a first month produces", body=first_month),
        _section(
            "04", "Month six", "What month six looks like",
            body=_prose(
                "Picture the same judgment task half a year in. Your reviewers still see cases, but only the ones the "
                "system can’t clear on its own, and that queue has been shrinking each month as the scorecard fills in. "
                "A correction one of them made in week two is now a written policy line the system applies every time.",
                "When someone asks why a verdict changed, you open the record and point at the version, the numbers it "
                "cleared, and the person who approved it. Nothing runs on a guess, and nothing runs on us: the model, "
                "the pipeline, the board, and the record are yours.",
            ),
            band=True,
        ),
        _section("05", "Tell us", "Four things that help us reply", body=checklist, section_id="tell-us"),
        _cta(
            "Bring us the problem.",
            "Tell us the problem, even if it’s half-formed, and we’ll scope the first month together. Anything you "
            "send goes through a short contact form.",
            label="Open the contact form", href=CONTACT_URL,
        ).replace("<a ", "<a data-contact ", 1) + _ENGAGE_SCRIPT,
    )


#: Carries where the visitor came from into the form. `/engage/?from=<page>&solution=<name>` is set on the
#: links that lead here (assets/site-nav.js adds `from`); the form's one free-text question is prefilled with
#: the four qualification prompts, the solution, and the source page, so each enquiry says what brought it in.
_ENGAGE_SCRIPT = """<script>
(function () {
  var q = new URLSearchParams(location.search);
  var from = (q.get('from') || '').slice(0, 120), solution = (q.get('solution') || '').slice(0, 60);
  if (!from && !solution) return;
  var text = decodeURIComponent(%s).replace('Solution or problem: ', 'Solution or problem: ' + solution);
  if (from) text += '(Came from: ' + from + ')';
  document.querySelectorAll('a[data-contact]').forEach(function (a) {
    var u = new URL(a.href);
    u.searchParams.set(%s, text);
    a.href = u.toString();
  });
})();
</script>"""
_ENGAGE_SCRIPT = _ENGAGE_SCRIPT % (repr(quote(FORM_TEMPLATE)).replace("'", '"'), repr(FORM_ENTRY).replace("'", '"'))


# --------------------------------------------------------------------------
# Decision models
# --------------------------------------------------------------------------

_DECISION_QA = (
    ("Can you fine-tune Jev?",
     "No. TypeSafe serves the same Jev weights to every account, so there is no fine-tuning endpoint. You get the same "
     "effect by changing the questions you ask it and fitting a small decision head over its answers, aligned from "
     "reviewer feedback. On 140 labels, one new plain-English question raised accuracy from 77 to 87 percent with the "
     "model unchanged.",
     [("Fine-Tuning Jev: You Can’t. Here’s What Gets You the Same Effect", "/blog/fine-tuning-jev/")]),
    ("How do I align Jev to my own data?",
     "Start classifying immediately, review the decisions as it makes them, and label the ones a reviewer disagrees "
     "with. Those labels refit the decision head and calibrate its confidence, and when disagreements keep coming, "
     "they tell you which question to add. That loop is far cheaper than building a labelled dataset before you start.",
     [("Primus Is a Classifier Lab", "/blog/primus-classifier-lab/")]),
    ("Can you trust Jev’s confidence?",
     "Higher really does mean more likely right, but out of the box it ran about 15 points overconfident on 8,801 "
     "labelled examples. Calibration against a few hundred of your own labels closes most of that gap, and only then "
     "can you set a threshold to auto-accept above and route the rest to a person.",
     [("Can You Trust Jev’s Confidence?", "/blog/can-you-trust-jev-confidence/")]),
    ("Does a decision model change its verdict on a name or a pronoun?",
     "It can. On two thousand real professional bios per job with one pronoun swapped, Jev’s verdict moved on 1 to 4 "
     "bios in 100 and the open-weights Laya’s on 8 to 18, almost always toward the stereotype. Auditing by slice before "
     "and after deployment is how you catch it.",
     [("The One-Word Test", "/blog/one-word-test/")]),
    ("Can I own the classifier instead of paying per request forever?",
     "Yes. Once the hosted model is aligned, you can distill it into a small model you serve yourself. A 66-million-"
     "parameter student trained from an aligned Jev system scored 91.2 percent against the human label, above its "
     "teacher’s 89.0, at 5 to 15 milliseconds an item, with a per-slice ship gate deciding when it was ready. " + OWNERSHIP,
     [("Distilling an Aligned Jev System into a Classifier You Own", "/blog/distilling-jev-into-a-classifier/")]),
    ("Can I run this loop myself?",
     'Yes. The loop is open source as <a href="https://cyclotron.anth.us/">Cyclotron</a>, under the MIT license. A '
     "cyclotron is one AI decision that learns from your reviewers’ corrections: it starts on day one with the "
     "decision model’s general training, refits a small model on each correction, and lets an LLM propose better "
     "questions that code tests before they go live. Run it yourself, have Anthus run it, or have Anthus "
     '<a href="https://cyclotron.anth.us/services">build it into your product</a>.',
     []),
    ("Should I use Jev or an open-weights decision model like Laya?",
     "The same reviewer loop aligns either one. On the same 140 labels and the same questions, Jev led Laya by 4.7 "
     "points alone and 6.8 with the feedback layer, and fully fine-tuning Laya on those labels beat both. Which engine "
     "you pick depends on whether you need to own the weights.",
     [("Jev vs Laya", "/blog/jev-vs-laya/")]),
)


def decision_models_page() -> str:
    def answer(a: str) -> str:
        return a if "<a " in a else escape(a)

    qa = '<ul class="grid grid--qa">' + "".join(
        _qa_card(q, answer(a), links) for q, a, links in _DECISION_QA
    ) + "</ul>"
    loop = _steps((
        ("Start classifying now", "Put the decision model in front of real cases with the questions your reviewers already ask."),
        ("Review and label the disagreements", "Reviewers agree or disagree with verdicts as they happen, and those calls are all the labelling the loop needs."),
        ("Calibrate the confidence", "Fit the stated confidence to observed accuracy so a threshold means what it says."),
        ("Change the questions when refits stall", "Let the system read the disagreements and propose one question; a person approves it."),
        ("Gate every change by slice", "Promote a version only when it clears held-out labels on every slice reviewers care about."),
        ("Distill when you’re ready to own it", "Train a small model from the aligned system and ship it behind the same gate."),
    ))
    return _page(
        _page_hero(
            "DECISION MODELS", "Aligning Jev and other decision models to your data",
            "A decision model like Jev answers a bounded question with a verdict and a confidence, in a fraction of a "
            "second, for a fraction of a cent. It arrives frozen: you can’t fine-tune it, and it doesn’t know your "
            "reviewers’ rules. Everything that makes it fit your business lives in the loop around it. Each step of that "
            "loop has a published measurement behind it, and we run the loop on client judgment tasks.",
            art=_px("verdict-meter"),
        ),
        _section("01", "Questions", "The questions people arrive with", body=qa, stack=True),
        _section(
            "02", "The loop", "The loop, in order", body=loop
            + _prose(
                'Every step is a published experiment on the <a href="/research/">research page</a>, the public '
                'leaderboards are on the <a href="/benchmarks/">benchmarks page</a>, and '
                '<a href="https://primus.anth.us" rel="noopener">Primus</a> is where we run the loop in production.'
            ),
            band=True,
        ),
        _cta(
            "We do this for clients, at scale.",
            "Anthus has run this kind of loop in production for years: reviewers correct the model and say why, the "
            "explanation becomes policy, and the system gets more trustworthy month over month across hundreds of "
            "scorecards and millions of interactions. Bring us the judgment task and we’ll run it with your reviewers in "
            "the loop, and hand you a report you can inspect after the first month. The engine is open source: "
            '<a href="https://cyclotron.anth.us/">Cyclotron</a>.',
            label="See how an engagement works",
        ),
    )


# --------------------------------------------------------------------------
# Benchmarks
# --------------------------------------------------------------------------


def benchmarks_page() -> str:
    cards = '<ul class="grid grid--2">' + _card(
        "Biased-Decisions",
        '<p class="card__sub">Does an AI model’s answer change when one personal detail about a person changes?</p>'
        "<p>Would AI identify a different job for the same person if “he” became “she”? Would it remove the same online "
        "comment after its author said they were gay? Biased-Decisions changes one personal detail in a text, asks the "
        "same question again, and ranks models by how much more often the answer changes than it does after a neutral "
        "control edit of the same size.</p>",
        href="https://biased-decisions.anth.us/",
        extra=_links([("See the results", "https://biased-decisions.anth.us/"),
                      ("Code: AnthusAI/Biased-Decisions", "https://github.com/AnthusAI/Biased-Decisions")]),
    ) + _card(
        "Hard-Decisions",
        '<p class="card__sub">How far can a decision model follow a chain of reasoning before it starts guessing?</p>'
        "<p>On true-or-false questions, every model tested except Jev falls to coin-flip accuracy by five chained "
        "inferences: the open decision models Kev, GLiNER2.5-Decide and Laya, GPT-6 Luna used as a one-shot classifier, "
        "and GLiDE. Jev still answers 89.3% correctly at that depth.</p>",
        href="https://hard-decisions.anth.us/",
        extra=_links([("See the results", "https://hard-decisions.anth.us/")]),
    ) + "</ul>"
    return _page(
        _page_hero(
            "BENCHMARKS", "Benchmarks",
            "We publish two public benchmarks for decision models, the fast AI models that answer a bounded question "
            "with a verdict. Each one shows its method, every model’s results, and the cases behind them, so you can "
            "check a model against the decision you’re about to hand it.",
            art=_px("leaderboard"),
        ),
        '<section class="section section--tight"><div class="container">' + cards
        + '<div class="prose" style="margin-top:2.5rem"><p>The articles that explain these findings are on the '
        '<a href="/research/">research page</a>, and the guide to aligning a decision model to your own data is '
        '<a href="/decision-models/">here</a>.</p></div></div></section>',
        _cta(
            "We do this for clients, at scale.",
            "Anthus has run this kind of loop in production for years: reviewers correct the model and say why, the "
            "explanation becomes policy, and the system gets more trustworthy month over month across hundreds of "
            "scorecards and millions of interactions. Bring us the judgment task and we’ll run it on Primus with your "
            "reviewers in the loop, and hand you a scorecard you can inspect after the first month.",
            label="See how an engagement works",
        ),
    )
