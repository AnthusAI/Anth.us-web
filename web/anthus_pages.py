"""Markus equivalents of the Anth.us bespoke pages and listing templates.

Each generator here replaces one Gatsby page or template. Copy is lifted from
the real components rather than rewritten, so the staging site reads like
anth.us and not like a placeholder:

| Gatsby source                      | Generator                 | Output                     |
| ---------------------------------- | ------------------------- | -------------------------- |
| ``src/pages/index.js``             | ``homepage``              | ``index.md``               |
| ``src/pages/about.js``             | ``about_page``            | ``about.md``               |
| ``src/pages/ai-solutions.js``      | ``ai_solutions_page``     | ``ai-solutions.md``        |
| ``src/pages/platform.js``          | ``platform_index``        | ``platform/index.md``      |
| ``src/pages/ryan.js``              | ``ryan_page``             | ``ryan.md``                |
| ``src/pages/404.js``               | ``not_found_page``        | ``404.md``                 |
| ``src/templates/blog.jsx``         | ``articles_index``        | ``articles/index.md``      |
| ``src/templates/posts-list.jsx``   | ``posts_pages``           | ``posts/index.md`` + pages |
| ``src/templates/blog-tag.jsx``     | ``tag_pages``             | ``tags/<tag>.md``          |
| ``src/templates/platform-product`` | ``platform_product_head`` | per-product page header    |

Hero and capability imagery comes from ``web/assets/site/``, which is
committed in this repo: those files live in the **Anth.us** repo's
``src/images``/``static`` trees, not in the content submodule, and the Amplify
build has no access to a sibling checkout.
"""

from __future__ import annotations

from anthus_content import ContentNode, ImageIndex

CONTACT_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdWlt4KpwPSBHzg3o8fikHcfrzxo5rCcV-0-zDt815NZ1tcyg/viewform?usp=sf_link"
)

SITE_TITLE = "Anthus"
SITE_DESCRIPTION = (
    "Anthus builds and operates self-aligning AI systems — custom models, agent "
    "harnesses, and evaluation loops with a human in the loop, grounded in 14 "
    "years of production operations."
)

# gatsby-config.mjs siteMetadata.menuLinks, mapped onto static output paths.
MENU = (
    ("AI Solutions", "ai-solutions.html"),
    ("Platform", "platform/index.html"),
    ("About", "about.html"),
    ("Articles", "articles/index.html"),
    ("Posts", "posts/index.html"),
)


def _front(title: str, description: str) -> list[str]:
    return [
        "---",
        f'title: "{title}"',
        f'description: "{description}"',
        "---",
        "",
    ]


def _card(node: ContentNode, *, href: str, image: str | None, show_date: bool = True) -> list[str]:
    lines = [':::card{span="full"}', f"### [{node.title}]({href})", ""]
    if image:
        lines.append(f"[![{node.title}]({image})]({href})")
        lines.append("")
    if show_date and node.display_date:
        lines.append(f"*{node.display_date}*")
        lines.append("")
    excerpt = node.excerpt_text
    if excerpt and excerpt.strip() != node.title.strip():
        lines.append(excerpt)
        lines.append("")
    lines.append(":::")
    return lines


def _preview(node: ContentNode, images: ImageIndex) -> str | None:
    raw = node.front_matter.get("preview_image")
    if not raw:
        return None
    return images.resolve_path(str(raw), relative_to=node.source)


def article_href(node: ContentNode) -> str:
    return f"/articles/{node.slug}.html"


def platform_href(node: ContentNode) -> str:
    return f"/platform/{node.slug}.html"


# --------------------------------------------------------------------------
# Homepage — src/pages/index.js
# --------------------------------------------------------------------------

_CAPABILITIES = (
    (
        "Knowledge Bases",
        "https://github.com/AnthusAI/Biblicus",
        "/assets/site/smart-process-automation.png",
        "Knowledge bases with learned ontologies and taxonomies",
        "Your agents are only as good as what they can look up. We build knowledge "
        "bases with **ontologies and taxonomies that learn from your data**, "
        "refining their own structure instead of going stale the week after "
        "someone hand-built them.",
    ),
    (
        "Self-Aligning Automation",
        "/articles/call-criteria.html",
        "/assets/site/ai-enabled-projects.png",
        "Unattended automation with a human in the loop",
        "Unattended business process automation with a human in the loop. "
        "Reviewers correct it and say why; the system **turns the explanation "
        "into a stated policy** and applies it from then on.",
    ),
    (
        "Agent Systems",
        "/articles/give-an-agent-a-tool.html",
        "/assets/site/ai-agent.png",
        "Agent systems, tools, and orchestration",
        "A model is half a system. The other half is the harness: the tools it "
        "can reach, the procedures it follows, the limits it runs inside, and "
        "the ability to work for hours **without losing the plot**.",
    ),
    (
        "Machine Learning",
        "/articles/domain-specific-turn-detection.html",
        "/assets/site/ai-software-feature.png",
        "Custom and fine-tuned machine learning models",
        "Custom classifiers, fine-tuned models, and **calibrated confidence** "
        "that tells you which decisions to trust and which to escalate. We find "
        "the cheapest model that clears your bar, prove that it clears it, and "
        "run it in production on AWS — training, serving, and evaluation included.",
    ),
)


def homepage(*, articles: list[ContentNode], posts: list[ContentNode], images: ImageIndex) -> str:
    # Markus renders the front-matter title as the document's single <h1> and
    # the description as the lede, so the hero headline and subhead go there
    # rather than in the body — a body `# …` would emit a second <h1>.
    lines = _front(
        "Depend on proven experts",
        "We solve your business problems with AI, then run it securely in production.",
    )

    # The Gatsby hero is an absolutely-positioned text overlay on a full-bleed
    # image. Markus has no overlay primitive, so the static equivalent is the
    # same headline and subhead (above, from front matter) followed by the
    # hero image and the call to action.
    lines += [
        ':::figure{src="/assets/site/serverless-ai-software-solutions.png" alt="Anthus"}',
        ":::",
        "",
        f"[Tell us the problem]({CONTACT_URL})",
        "",
        # `metric` is a leaf directive, so it opens with two colons and has no
        # closing fence. Writing it as `:::metric{…}` makes the parser treat it
        # as an unterminated container and the whole page fails to convert.
        ':::two-up{ratio="1:1"}',
        ":::column",
        '::metric{value="$250M+" label="revenue processed at scale, at nearly 100% uptime"}',
        ":::",
        ":::column",
        '::metric{value="180B" label="tokens of production LLM workload"}',
        ":::",
        ":::",
        "",
        "AI in production, not just in demos.",
        "",
        "## What We Do",
        "",
        ':::card-grid{columns="2"}',
    ]
    for title, url, image, alt, description in _CAPABILITIES:
        lines += [
            ":::card",
            f"### [{title}]({url})",
            "",
            f"[![{alt}]({image})]({url})",
            "",
            description,
            ":::",
        ]
    lines += [
        ":::",
        "",
        "Clients usually arrive asking about one of these. **The work rarely stays in one box.**",
        "",
        "## Our Approach: Cybernetic Development",
        "",
        "AI is an engine for generating code. The differentiator is the governor: "
        "the constraints, feedback loops, and judgment that keep systems reliable "
        "in production.",
        "",
        "Modern failures increasingly look less like isolated “bugs” and more like "
        "operational, multi-system breakdowns. Great unit tests help — but they "
        "don’t cover every emergent scenario. So we build layered defenses and "
        "close the loop with real-world feedback.",
        "",
        "- Specs first: define behavior before implementation.",
        "- Defense in depth: sandboxed tools, CI gates, staged rollouts, and fast rollback.",
        "- Operational feedback: telemetry and incident-driven regressions that tighten the loop over time.",
        "- Simplify and delete: reduce degrees of freedom to eliminate entire classes of failure.",
        "",
        f"[Contact us]({CONTACT_URL}) · [Read Cybernetic Development](/articles/cybernetic-development.html)",
        "",
        ':::callout{kind="note" title="PART OF — The Anthus Platform"}',
        "Solve complex business problems with AI and ML using a proven, reusable "
        "technology stack that grew out of real delivery work — runtime, agent "
        "execution, knowledge, observability, and media, with the enterprise "
        "controls that matter in production.",
        "",
        "[Explore the platform](/platform/index.html)",
        ":::",
        "",
    ]

    b0rd = next((node for node in articles if node.slug == "b0rd"), None)
    if b0rd is not None:
        lines += [
            ':::callout{kind="tip" title="SPINOFF — B0rd, desk displays for agent monitoring"}',
            "### [Glanceable signal when agents run all day](/articles/b0rd.html)",
            "",
            "**Anthus Microelectronics** grew out of the same workflow problem: when "
            "coding agents run for hours, the bottleneck moves to monitoring and "
            "steering them. B0rd is a standalone LED-matrix desk display — launch "
            "countdowns, agent status, notifications, an idle clock — readable from "
            "across the room. Handbuilt hardware running a handbuilt (AI-assisted) "
            "OS. Matching units stay in sync without pairing or a hub.",
            "",
            "- Standalone appliance — browser setup, no app store",
            "- Glanceable cues for long-running agent sessions",
            "- In sync by design across matching units",
            "",
            "[Read the B0rd story](/articles/b0rd.html) · "
            "[b0rd.info](https://b0rd.info) · "
            "[Etsy shop](https://www.etsy.com/shop/AnthusMicronics)",
            ":::",
            "",
        ]

    lines += [
        "## Case studies",
        "",
        ':::card-grid{columns="2"}',
        ":::card",
        "### [Call Criteria](/articles/call-criteria.html)",
        "",
        "**100% of calls reviewed**, up from a sample. Call Criteria's human QA "
        "couldn't scale without scaling headcount, so we built a self-evolving "
        "RLHF system: reviewers correct the AI and say why, and the system turns "
        "the explanation into policy it applies from then on.",
        ":::",
        ":::card",
        "### [Venue Driver](/articles/venue-driver.html)",
        "",
        "**16 years of continuous operation** across Las Vegas nightlife. When an "
        "AWS data center failed catastrophically, we relocated the entire system "
        "within hours — ticket scanning at the nightclubs never stopped.",
        ":::",
        ":::",
        "",
        "See our [solution patterns](/ai-solutions.html).",
        "",
        "## Recent Articles",
        "",
        ':::card-grid{columns="6"}',
    ]
    for node in articles[:4]:
        href = str(node.front_matter.get("external_url") or article_href(node))
        lines += _card(node, href=href, image=_preview(node, images))
    lines += [
        ":::",
        "",
        "Please see our [Articles](/articles/index.html) for more.",
        "",
        "## Recent Posts",
        "",
    ]
    for node in posts[:4]:
        lines += _post_row(node, images)
    lines += ["", "Please see our [Posts](/posts/index.html) for more.", ""]
    return "\n".join(lines) + "\n"


def _post_row(node: ContentNode, images: ImageIndex) -> list[str]:
    """One short-post row: title, optional excerpt, date. Matches posts-list.jsx."""
    href = article_href(node)
    lines = [f"### [{node.title}]({href})", ""]
    image = _preview(node, images)
    if image:
        lines += [f"[![{node.title}]({image})]({href})", ""]
    excerpt = node.excerpt_text
    if excerpt and excerpt.strip() != node.title.strip():
        lines += [excerpt, ""]
    if node.display_date:
        lines += [f"*{node.display_date}* — [more…]({href})", ""]
    return lines


# --------------------------------------------------------------------------
# Listings
# --------------------------------------------------------------------------


def articles_index(articles: list[ContentNode], images: ImageIndex) -> str:
    lines = _front(
        "Blog articles",
        "Depend on proven experts with a history of operational excellence for "
        "reliable serverless AI solutions on AWS and Azure.",
    )
    lines.append(':::card-grid{columns="6"}')
    for node in articles:
        lines += _card(node, href=f"{node.slug}.html", image=_preview(node, images))
    lines.append(":::")
    return "\n".join(lines) + "\n"


def posts_pages(posts: list[ContentNode], images: ImageIndex, per_page: int) -> dict[str, str]:
    """Paginated short-post listings.

    Gatsby serves page 2 at ``/posts/2/``. Static output cannot create that
    path without a directory per page, so pages after the first are
    ``/posts/page-2.html``. Page 1 stays ``/posts/``.
    """
    pages: dict[str, str] = {}
    total = max(1, -(-len(posts) // per_page))
    for page in range(1, total + 1):
        chunk = posts[(page - 1) * per_page : page * per_page]
        title = "Recent Posts" if page == 1 else f"Posts — Page {page}"
        lines = _front(
            title,
            "Short posts on AI, software, and operations — focused on practical "
            "lessons and reliable systems.",
        )
        for node in chunk:
            lines += _post_row_rel(node, images)
        if total > 1:
            lines += ["", "---", ""]
            nav = []
            if page > 1:
                nav.append(f"[← Previous]({_posts_page_href(page - 1)})")
            nav.append(f"Page {page} of {total}")
            if page < total:
                nav.append(f"[Next →]({_posts_page_href(page + 1)})")
            lines.append(" · ".join(nav))
            lines.append("")
        name = "index.md" if page == 1 else f"page-{page}.md"
        pages[name] = "\n".join(lines) + "\n"
    return pages


def _posts_page_href(page: int) -> str:
    return "/posts/index.html" if page == 1 else f"/posts/page-{page}.html"


def _post_row_rel(node: ContentNode, images: ImageIndex) -> list[str]:
    return _post_row(node, images)


def tag_pages(tags: dict[str, list[ContentNode]]) -> dict[str, str]:
    """``blog-tag.jsx`` equivalents.

    Gatsby mounts these at ``/blog/<tag>``, which shares a namespace with post
    slugs; this build uses its own ``tags/`` collection so a tag can never
    shadow an article. ``anthus_urls.legacy_rules`` 301s ``/blog/<tag>/`` here,
    except where a tag name collides with an article slug — production serves
    the article at that URL, so the redirect does too.
    """
    # Papyrus's collection discovery only accepts lowercase slugs, and the
    # corpus tags both `AI` and `ai` (plus other case variants). Those are the
    # same tag to a reader, so they are merged here rather than letting one
    # silently overwrite the other's page — which is what happened first.
    merged: dict[str, tuple[str, list[ContentNode]]] = {}
    for tag, nodes in tags.items():
        slug = tag.strip().lower().replace(" ", "-")
        label, existing = merged.get(slug, (tag.strip(), []))
        combined = {node.slug: node for node in existing}
        combined.update({node.slug: node for node in nodes})
        # Prefer the casing used by the larger group as the display label.
        if len(nodes) > len(existing):
            label = tag.strip()
        merged[slug] = (label, list(combined.values()))

    pages: dict[str, str] = {}
    for slug, (label, nodes) in sorted(merged.items()):
        lines = _front(
            f"Articles tagged with: {label}",
            f"Anth.us articles tagged {label}.",
        )
        for node in sorted(nodes, key=lambda n: (n.date, n.slug), reverse=True):
            lines.append(f"- [{node.title}]({article_href(node)})")
        lines.append("")
        pages[f"{slug}.md"] = "\n".join(lines) + "\n"

    lines = _front("Tags", "Every tag used across Anth.us articles.")
    for slug, (label, nodes) in sorted(merged.items()):
        lines.append(f"- [{label}]({slug}.html) ({len(nodes)})")
    lines.append("")
    pages["index.md"] = "\n".join(lines) + "\n"
    return pages


# --------------------------------------------------------------------------
# Platform — src/pages/platform.js and src/templates/platform-product.jsx
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
        "Tactus defines the durable procedure, Plexus measures and improves it, "
        "Kanbus tracks work and operator state, and Caducus helps humans see what "
        "is going wrong in production.",
    ),
    (
        "Platform-native internal tooling",
        "Korporus supplies the shared shell while product-specific modules from "
        "Plexus, Kanbus, Biblicus, and future tools appear as interoperable "
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
    "plexus": {
        "fits": "Plexus is the MLOps and evaluation spine of the platform. It helps the other building blocks behave like governable production systems instead of isolated demos.",
        "links": [
            ("Works with Tactus procedures", "tactus"),
            ("Turns Biblicus feedback into evaluation inputs", "biblicus"),
            ("Runs inside broader Korporus surfaces", "korporus"),
        ],
        "recipe": "Example: pair Plexus with Tactus for durable procedures, Biblicus for evidence-backed inputs, and Caducus for operator monitoring.",
    },
    "tactus": {
        "fits": "Tactus is the procedural core. It gives the rest of the platform a durable way to describe tool-using agent behavior.",
        "links": [
            ("Evaluated through Plexus", "plexus"),
            ("Grounded by Biblicus corpora", "biblicus"),
            ("Hosted inside Korporus", "korporus"),
        ],
        "recipe": "Example: use Tactus to encode a repeatable research workflow, Biblicus for the corpus, and Plexus for regression checks before deployment.",
    },
    "kanbus": {
        "fits": "Kanbus supplies durable workflow memory so humans and agents can coordinate real delivery work instead of operating in a stateless loop.",
        "links": [
            ("Pairs with Tactus for execution", "tactus"),
            ("Feeds work cadence into Plexus", "plexus"),
            ("Appears in Korporus as an operator surface", "korporus"),
        ],
        "recipe": "Example: combine Kanbus, Tactus, and Plexus to manage backlogs, execute procedures, and continuously improve the resulting system.",
    },
    "korporus": {
        "fits": "Korporus is the standard container for platform-powered applications. It is where multiple Anthus components can show up together as one service.",
        "links": [
            ("Hosts Plexus-powered applications", "plexus"),
            ("Hosts Tactus-driven workflows", "tactus"),
            ("Benefits from Caducus operator visibility", "caducus"),
        ],
        "recipe": "Example: use Korporus as the shell around a Tactus workflow, a Plexus control plane, and a Babulus authoring surface for a complete internal platform app.",
    },
    "biblicus": {
        "fits": "Biblicus is the evidence layer. It gives other Anthus components something inspectable and rebuildable to reason over.",
        "links": [
            ("Grounds Tactus procedures", "tactus"),
            ("Feeds signals into Plexus", "plexus"),
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
            ("Supports Plexus-governed systems", "plexus"),
            ("Uses Virtuus-backed local data", "virtuus"),
        ],
        "recipe": "Example: add Caducus to a Korporus and Plexus deployment when humans need to triage incidents and understand evolving agent behavior.",
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


def _platform_cards(nodes: list[ContentNode]) -> list[str]:
    lines = [':::card-grid{columns="2"}']
    for node in nodes:
        href = f"{node.slug}.html"
        lines += [":::card", f"### [{node.title}]({href})", ""]
        pills = [
            str(node.front_matter.get(key))
            for key in ("platform_category", "platform_stage")
            if node.front_matter.get(key)
        ]
        if pills:
            lines += [" · ".join(f"`{pill}`" for pill in pills), ""]
        excerpt = node.excerpt_text
        if excerpt:
            lines += [excerpt, ""]
        actions = [f"[Read more]({href})"]
        external = node.front_matter.get("external_url")
        if external:
            actions.append(f"[Visit site]({external})")
        lines += [" · ".join(actions), ":::"]
    lines.append(":::")
    return lines


def platform_index(platform: list[ContentNode]) -> str:
    published = [node for node in platform if node.published]
    lines = _front(
        "The Anthus Platform",
        "Explore the Anthus Platform: the runtime, orchestration, MLOps, "
        "knowledge, observability, and media systems behind our AI-native "
        "delivery work.",
    )
    lines += [
        "**A technology stack that grew out of real delivery work.** It is not a "
        "speculative architecture diagram. This is the internal product line that "
        "emerged from building RLHF systems, durable agent workflows, "
        "retrieval-backed automation, hosted operator applications, and "
        "programmable media pipelines for real engagements. The same enterprise "
        "controls that matter in production software also matter here: "
        "auditability, rollback paths, operator visibility, and clear evaluation "
        "loops.",
        "",
        "[See the solutions we deliver](/ai-solutions.html) · "
        "[Read the cybernetic development thesis](/articles/cybernetic-development.html)",
        "",
        "## How the platform fits together",
        "",
        "We think about the platform in layers because complete AI systems need "
        "more than a model call. Korporus is the host shell. Chatticus is the "
        "shared room for people and bots. Antharchy is the agentic desktop those "
        "bots can run. Tactus defines the durable procedure. Kanbus keeps workflow "
        "memory and state. Plexus closes the evaluation loop. Biblicus and Virtuus "
        "make evidence and structured data portable. Caducus gives operators "
        "visibility. Babulus and VideoML apply the same discipline to narrative "
        "and media output.",
        "",
        "These are reusable building blocks, not isolated side projects. We combine "
        "them differently depending on the job: QA and evaluation, internal "
        "operator tooling, extraction and retrieval workflows, or outward-facing "
        "content systems.",
        "",
        ':::card-grid{columns="3"}',
        ':::card{title="Runtime and control plane"}',
        "- `Korporus` standardizes the shell and hosting model for platform-powered services.",
        "- `Chatticus` gives people and bots a shared room with approvals.",
        "- `Plexus` manages evaluation, feedback loops, and MLOps.",
        "- `Kanbus` keeps work orchestration and project memory durable.",
        ":::",
        ':::card{title="Agent execution and data"}',
        "- `Tactus` defines durable, sandboxed agent procedures.",
        "- `Antharchy` is the agentic Linux desktop for long-running bot work.",
        "- `Biblicus` turns corpora into extractable, retrievable knowledge.",
        "- `Virtuus` makes structured JSON data queryable on disk.",
        ":::",
        ':::card{title="Operations and media"}',
        "- `Caducus` surfaces operator-facing health and incident signals.",
        "- `Babulus` and `VideoML` apply the same code-first approach to content and video.",
        "- The result is one stack for systems, workflows, and communication.",
        ":::",
        ":::",
        "",
        ':::card-grid{columns="2"}',
    ]
    for title, summary in _STACK_RECIPES:
        lines += [f':::card{{title="{title}"}}', summary, ":::"]
    lines += [":::", ""]

    featured = [node for node in published if node.slug in {"tactus", "videoml"}]
    if featured:
        lines += [
            "## Featured platform technologies",
            "",
            "Tactus and VideoML deserve separate attention because they express the "
            "broader Anthus point of view: treat complex operational systems as "
            "code, keep them inspectable, and make agent collaboration governable.",
            "",
        ]
        lines += _platform_cards(featured)
        lines.append("")

    grouped: dict[str, list[ContentNode]] = {}
    for node in published:
        category = str(node.front_matter.get("platform_category") or "Platform")
        grouped.setdefault(category, []).append(node)
    ordered = [c for c in _CATEGORY_ORDER if grouped.get(c)]
    ordered += [c for c in sorted(grouped) if c not in _CATEGORY_ORDER]
    for category in ordered:
        lines += [f"## {category}", ""]
        lines += _platform_cards(grouped[category])
        lines.append("")
    return "\n".join(lines) + "\n"


def platform_product_head(node: ContentNode) -> str:
    """The ``platform-product.jsx`` chrome that wraps a product's MDX body."""
    lines = [
        "[← Back to Anthus Platform](index.html)",
        "",
        "*PART OF — The Anthus Platform*",
        "",
    ]
    pills = [
        str(node.front_matter.get(key))
        for key in ("platform_category", "platform_stage")
        if node.front_matter.get(key)
    ]
    if pills:
        lines += [" · ".join(f"`{pill}`" for pill in pills), ""]
    excerpt = node.excerpt_text
    if excerpt:
        lines += [f"**{excerpt}**", ""]
    actions = []
    external = node.front_matter.get("external_url")
    if external:
        actions.append(f"[Visit external site]({external})")
    actions.append("[See how it fits our solutions work](/ai-solutions.html)")
    lines += [" · ".join(actions), ""]
    return "\n".join(lines)


def platform_product_tail(node: ContentNode) -> str:
    relationship = PLATFORM_RELATIONSHIPS.get(node.slug)
    if not relationship:
        return ""
    lines = ["", "## Where this fits in the Anthus Platform", "", relationship["fits"], ""]
    for label, slug in relationship["links"]:
        lines.append(f"- [{label}]({slug}.html)")
    lines += [
        "",
        ':::callout{kind="tip" title="Common combination"}',
        relationship["recipe"],
        ":::",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# About — src/pages/about.js
# --------------------------------------------------------------------------

_VALUES = (
    (
        "Prioritize Solutions Over Tools",
        "Investing in products and services only delivers business value if you're "
        "in the business of products and services. **We're in the business of "
        "solutions**.",
    ),
    (
        "Focus on Business Logic",
        "The only code you should be writing is the business logic that solves real "
        "problems. [Don't waste time reinventing wheels.](/articles/langchain-by-example.html)",
    ),
    (
        "Continuously Improve",
        "Enable rapid, iterative change through CI/CD and DevOps — then let the "
        "systems improve themselves. **Self-optimizing classifiers and "
        "self-steering agent systems** get better from production feedback without "
        "waiting for an engineer to notice.",
    ),
    (
        "Implement Infrastructure as Code",
        "Leverage DevOps to implement Infrastructure as Code, and **MLOps and "
        "LLMOps** to do the same for the models. Every part of a production "
        "system — including training runs and evaluations — should be created by "
        "code so it's reproducible, not clicked together by hand.",
    ),
    (
        "Commodify AI Models",
        "Treat AI models as replaceable, not magic black boxes. In a world with no "
        "moats, [don't invest too much in any given castle.](/articles/a-world-with-no-moats.html)",
    ),
    (
        "Optimize Resource Usage",
        "Balance efficiency with cost-effectiveness. When intelligence is cheap, "
        "the goal shifts from conserving compute to conserving context and "
        "cognitive load.",
    ),
)


def about_page() -> str:
    lines = _front(
        "About us",
        "Anthus builds and operates self-aligning AI systems, grounded in 14 years "
        "of production operations — the reliability and security behind a "
        "multi-million-dollar platform, now applied to AI.",
    )
    lines += [
        ':::figure{src="/assets/site/ryan-porter.png" alt="About Anthus"}',
        ":::",
        "",
        "In 2009, [Ryan Porter](/ryan.html) developed an innovative event ticket "
        "sales system for a [Tiësto world tour]"
        "(https://en.wikipedia.org/wiki/Kaleidoscope_World_Tour), sparking a "
        "business that generated up to $64 million annually for **over fourteen "
        "years.** We came together as a team as the business expanded, going from "
        "a tiny startup to a department within a large multinational corporation, "
        "[Tao Group Hospitality](https://taogroup.com). We have worked cohesively "
        "for more than a decade, safeguarding an impeccable record in "
        "**reliability and security**.",
        "",
        "Throughout our journey, we not only integrated various third-party "
        "platforms — including Salesforce, Marketo, Salesforce Marketing Cloud, "
        "Mailchimp, and Paytronix into our system but also successfully navigated "
        "through multiple technological revolutions. From embracing **cloud "
        "computing** to harnessing **serverless architectures** and deploying "
        "**artificial intelligence** applications, we continuously adapted and "
        "innovated while maintaining operational excellence and security. Even "
        "amidst rigorous audits from top-tier firms and scrutiny from our parent "
        "company, Madison Square Garden Entertainment, our innovative approaches "
        "to service management maturity and risk management consistently earned "
        "approval.",
        "",
        "Our endurance over more than fourteen years is a testament to our "
        "commitment and capability in preventing business interruptions arising "
        "from downtime, software malfunctions, security incidents, or data losses. "
        "**The hackers never got us**, despite being a [prime target]"
        "(https://twitter.com/RyanAlynPorter/status/890982980721790976). When a "
        "catastrophic failure struck an entire AWS data center, we relocated the "
        "entire system to a new data center within hours, ensuring that ticket "
        "scanning at nightclubs proceeded without a hitch. We have navigated "
        "through massive DDoS attacks, primary database server failures, silent "
        "failures in third-party systems, and everything else you could imagine. "
        "We always **kept the revenue flowing**. Then we smoothly handed it off to "
        "the next team with no business interruption or impairment.",
        "",
        "## Our Mission",
        "",
        ':::pull-quote{tone="primary"}',
        "Deliver **reliable, secure, and efficient** business solutions using "
        "collaboration between human and **artificial intelligence** in every "
        "aspect of **development and operations**. We build systems that keep "
        "working when nobody is watching.",
        ":::",
        "",
        "## Our Values",
        "",
    ]
    for title, description in _VALUES:
        lines += [f"**{title}**", "", description, ""]
    lines += [
        "## How We Build Today",
        "",
        "The AI era doesn’t remove the need for operational excellence — it raises "
        "the stakes. We use a cybernetic approach: clear intent, layered "
        "safeguards, and production feedback loops that continuously harden the "
        "system. Read more in [Cybernetic Development]"
        "(/articles/cybernetic-development.html).",
        "",
        "## Spinoffs",
        "",
        "Running AI agents all day created a problem of its own: the bottleneck "
        "moved from writing the code to monitoring and steering the agents running "
        "it. Sitting in front of a terminal all day is not the answer. That "
        "workflow problem became a hardware venture. We spun up **Anthus "
        "Microelectronics** to build the desk displays that grew out of it — "
        "handbuilt microelectronics running a custom handbuilt (AI-assisted) OS, "
        "real and handmade even where AI accelerated the build.",
        "",
        "The first product is **B0rd**: a standalone LED-matrix desk display for "
        "glanceable information — launch countdowns, agent status, notifications, "
        "an idle clock — that you can read from across the room instead of a "
        "screen you have to sit in front of. Matching units even stay in sync "
        "without pairing or a hub. See the [B0rd solution page]"
        "(/articles/b0rd.html), visit [b0rd.info](https://b0rd.info) for the "
        "product site, or browse the [Etsy shop]"
        "(https://www.etsy.com/shop/AnthusMicronics).",
        "",
        "Now, we bring our depth of experience and technical agility to your "
        "projects. **What can we develop and operate for you?**",
        "",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# AI Solutions — src/pages/ai-solutions.js
# --------------------------------------------------------------------------


def ai_solutions_page(solutions: list[ContentNode], images: ImageIndex) -> str:
    featured = [
        node
        for node in solutions
        if "featured" in node.tags and "integrations" not in node.tags
    ]
    portfolio = [
        node
        for node in solutions
        if "featured" not in node.tags and "integrations" not in node.tags
    ]
    integrations = [node for node in solutions if "integrations" in node.tags]

    lines = _front("Solving Problems Using AI", SITE_DESCRIPTION)
    lines += [
        ':::figure{src="/assets/site/ai-software-solutions.png" alt="AI software solutions"}',
        ":::",
        "",
        "You're under pressure to deliver AI that works in production, not just in "
        "a demo. Anthus builds and operates self-aligning AI systems — custom "
        "models, agent harnesses, and evaluation loops with a human in the loop, "
        "grounded in 14 years of production operations. Our Call Criteria work is "
        "the proof: two years of production RLHF, a data flywheel that keeps "
        "learning from expert feedback, serving real QA at scale.",
        "",
        "## What We Build",
        "",
        "- **Knowledge Bases** — ontologies and taxonomies that learn from your "
        "data instead of going stale. [See Biblicus](https://github.com/AnthusAI/Biblicus).",
        "- **Self-Aligning Automation** — systems that improve from production "
        "feedback, with a human in the loop. "
        "[See the Call Criteria case study](/articles/call-criteria.html).",
        "- **Agent Systems** — durable, governed agent procedures with sandboxed "
        "tools and rollback. [See the approach](/articles/give-an-agent-a-tool.html).",
        "- **Machine Learning** — custom models and fine-tuned classifiers aligned "
        "to your business. [See the work](/articles/domain-specific-turn-detection.html).",
        "",
        "## Our Approach: Cybernetic Development",
        "",
        "We don’t just build AI features — we build the governors that make them "
        "safe to operate: clear specifications, layered verification, staged "
        "releases, and feedback loops that incorporate production learnings.",
        "",
        "- Specs first: define behavior before implementation.",
        "- Defense in depth: sandboxed tools, CI gates, staged rollouts, and fast rollback.",
        "- Operational feedback: telemetry and incident-driven regressions that tighten the loop over time.",
        "- Simplify and delete: reduce degrees of freedom to eliminate entire classes of failure.",
        "",
        "Learn more in our article on [Cybernetic Development]"
        f"(/articles/cybernetic-development.html), or [contact us]({CONTACT_URL}) to "
        "talk through your goals and constraints.",
        "",
        f"Ready to revolutionize your business? [Let's talk about what we can do for you.]({CONTACT_URL})",
        "",
        "## Featured Solutions",
        "",
        "Our recent work showcases AI-driven solutions that demonstrate "
        "production-ready implementations of agentic AI, RLHF systems, and "
        "intelligent automation:",
        "",
    ]
    lines += _solutions_list(featured, images, with_image=True)
    lines += [
        "",
        "## Portfolio",
        "",
        "Our journey spans decades of solving complex business challenges, from "
        "serverless architectures to AI-enabled systems:",
        "",
    ]
    lines += _solutions_list(portfolio, images, with_image=True)
    lines += ["", "## Integrations", ""]
    lines += _solutions_list(integrations, images, with_image=False)
    lines += [
        "",
        "## The Process",
        "",
        ':::figure{src="/assets/site/Anthus AI Application Lifecycle.png" '
        'alt="AI Application Lifecycle" caption="The Anthus AI application lifecycle"}',
        ":::",
        "",
    ]
    return "\n".join(lines) + "\n"


def _solutions_list(
    nodes: list[ContentNode], images: ImageIndex, *, with_image: bool
) -> list[str]:
    """``solutions.js`` equivalent.

    The Gatsby component only links an entry when it is tagged ``featured``
    (``linkToPage`` is false on every call site), so unfeatured entries render
    as a plain heading. That is preserved here.
    """
    lines: list[str] = [':::card-grid{columns="6"}']
    for node in nodes:
        featured = "featured" in node.tags
        href = article_href(node)
        lines.append(':::card{span="full"}')
        lines.append(f"### [{node.title}]({href})" if featured else f"### {node.title}")
        lines.append("")
        image = _preview(node, images) if with_image else None
        if image:
            lines += [f"![{node.title}]({image})", ""]
        if node.display_date:
            lines += [f"*{node.display_date}*", ""]
        excerpt = node.excerpt_text
        if excerpt:
            lines += [excerpt, ""]
        lines.append(":::")
    lines.append(":::")
    return lines


# --------------------------------------------------------------------------
# Ryan — src/pages/ryan.js
# --------------------------------------------------------------------------

_EXPERIENCE = (
    (
        "Anthus AI Solutions",
        "Lead AI Solutions Architect",
        "January 2024 – Present",
        "Miami Beach, FL",
        [
            "Our team has been working together for over a decade, and we have been "
            "working on AI solutions for years now. The Anthus name is the only new "
            "thing, as we fully focus on the intersection of software solutions and "
            "artificial intelligence."
        ],
        [],
    ),
    (
        "Tao Group Hospitality",
        "Vice President of Marketing Technology",
        "August 2021 – January 2024",
        "New York, NY (remote from Miami Beach, FL)",
        [
            "Formerly with Hakkasan Group, Angel Management Group, and Venue Driver "
            "in an evolving role with the same venture."
        ],
        [
            "**Pioneering Technical Strategy:** Developed and operated a critical "
            "ticketing system evolving over **14 years** into a comprehensive "
            "platform encompassing reservation, guest list, and artist booking "
            "management, pivotal for business operations across various stakeholder "
            "domains.",
            "**Seamless Transition and Growth:** Managed the system's seamless "
            "transition through corporate acquisitions, maintaining operational "
            "excellence and high availability, processing as much as **$64 million "
            "in revenue per month** with **no major incidents.**",
            "**DevOps and Agile Leadership:** Championed a DevOps culture, promoting "
            "rapid iteration, continuous improvement, and agile methodologies, "
            "aligning closely with business needs and fostering a responsive, "
            "collaborative IT environment.",
            "**Longevity and Adaptation:** Adapted the platform through shifting "
            "market conditions and technological paradigms, from early-stage "
            "monolithic structures to a modern serverless distributed architecture, "
            "passing AWS Well-Architected audits by multinational corporations.",
        ],
    ),
    (
        "Hakkasan Group",
        "Vice President of Technology",
        "February 2014 – August 2021",
        "Las Vegas, NV (remote from Miami Beach, FL)",
        [
            "Formerly with Angel Management Group, and Venue Driver in an evolving "
            "role with the same venture."
        ],
        [
            "**Scalable System Leadership:** Continued advancement of a high-revenue "
            "ticketing system, emphasizing scalable, fault-tolerant infrastructure "
            "on AWS, embodying the Well-Architected Framework principles.",
            "**Data Integration Initiative:** Initiated and delivered a successful "
            "**enterprise data warehouse** project, integrating diverse data systems "
            "to support analytics, Salesforce CRM, Marketo and Salesforce Marketing "
            "Cloud for marketing operations.",
        ],
    ),
    (
        "Angel Management Group",
        "Executive Director of Technology",
        "October 2013 – February 2014",
        "Las Vegas, NV (remote from Miami Beach, FL)",
        ["Formerly with Venue Driver in an evolving role with the same venture."],
        [
            "**Strategic Technology Expansion:** Continuation and expansion of "
            "existing role after Angel Management Group acquired Venue Driver."
        ],
    ),
    (
        "Venue Driver",
        "CTO",
        "2007 – October 2013",
        "Miami Beach, FL",
        [
            "**Startup Technology Foundation:** Built and managed all technology "
            "infrastructure for a hospitality-focused technology startup, evolving "
            "the company into a major event ticketing provider processing "
            "substantial monthly revenue."
        ],
        [
            "**Leadership and Technical Training:** Directed all aspects of "
            "technology including software development, web operations, technical "
            "hiring, and training programs, laying the foundation for eventual "
            "acquisition and growth."
        ],
    ),
    (
        "CoolJunkie, LLC",
        "TechJunkie",
        "2002 – 2005",
        "Miami Beach, FL",
        [
            "Entered into a joint venture with Nick McCabe to develop a nightlife "
            "production and media company in Miami Beach, FL. The successful "
            "CoolJunkie.com website with its interactive forums was a pillar of the "
            "Miami Beach nightlife scene for years in the days before social media. "
            "The company also produced events like the BBC Radio One Miami party "
            "during the Winter Music Conference, and events from artists like Pete "
            "Tong, Cedric Gervais and many others."
        ],
        [],
    ),
    (
        "Endymion Corporation",
        "President",
        "1997 – Present",
        "Miami Beach, FL",
        [
            "Started a small software product company after graduating, based around "
            "a web mail application that was popular in the early days of the web, "
            "in the days of WebTV and AOL. Developed, licensed and supported a "
            "PERL-based web mail application that was used by thousands of users, "
            "and a Java-based enterprise web mail product."
        ],
        [],
    ),
    (
        "University of Florida",
        "BS, Computer Science",
        "1992 – 1997",
        "",
        [
            "Worked as an undergraduate research assistant for Dr. Gerhard X. Ritter "
            "and Dr. Mark S. Schmalz helping with their innovative work on "
            "**computer vision** using the Image Algebra framework. With funding "
            "from the US Department of Defense. One project's goal was the "
            "**automated detection** of land mines using multi-spectral imagery. An "
            "early predecessor of today's visual segmentation models. The project "
            "was incredibly successful despite relying on 2D convolution algorithms, "
            "without the benefit of modern visual AI models. My main job was C++ "
            "development.",
            "A related computer vision project aimed at detecting water mines by "
            "removing distortion in images from the surface of the ocean.",
            "Also worked on other research projects, including work by Dr. Panos "
            "Livadas on automated code analysis and refactoring tools that "
            "foreshadowed LLM-based coding tools like GitHub Copilot.",
            "Also worked as an undergraduate teaching assistant for a class based on "
            "the classic Lisp textbook, The Structure and Interpretation of Computer "
            "Programs.",
        ],
        [],
    ),
)


def ryan_page(solutions: list[ContentNode], images: ImageIndex) -> str:
    featured = [node for node in solutions if "featured" in node.tags]
    portfolio = [
        node
        for node in solutions
        if "featured" not in node.tags and "integrations" not in node.tags
    ]
    integrations = [
        node
        for node in solutions
        if "featured" not in node.tags and "integrations" in node.tags
    ]

    lines = _front(
        "Ryan Porter",
        "Ryan Porter — accomplished technology leader and architectural innovator, "
        "building and operating mission-critical AI systems at Anthus.",
    )
    lines += [
        "Accomplished **technology leader and architectural innovator** with a "
        "proven history of developing and operating mission-critical, "
        "high-availability systems that deliver business value. Focused on "
        "delivering exciting AI applications through serverless cloud "
        "architectures.",
        "",
    ]
    for title, subtitle, dates, location, paragraphs, bullets in _EXPERIENCE:
        meta = " · ".join(part for part in (dates, location) if part)
        lines += [f"## {title}", "", f"**{subtitle}**", "", f"*{meta}*", ""]
        for paragraph in paragraphs:
            lines += [paragraph, ""]
        for bullet in bullets:
            lines.append(f"- {bullet}")
        if bullets:
            lines.append("")
    lines += ["## Portfolio", ""]
    lines += _solutions_list(featured, images, with_image=True)
    lines.append("")
    lines += _solutions_list(portfolio, images, with_image=False)
    lines += ["", "## Integrations", ""]
    lines += _solutions_list(integrations, images, with_image=False)
    lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# 404 — src/pages/404.js
# --------------------------------------------------------------------------


def not_found_page() -> str:
    lines = _front("404: Not Found", "That page does not exist.")
    lines += [
        "You just hit a route that doesn't exist... the sadness.",
        "",
        "[Go back to the homepage](/index.html)",
        "",
    ]
    return "\n".join(lines) + "\n"
