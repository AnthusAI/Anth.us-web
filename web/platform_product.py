"""The product-page chrome: the heading above and the relationships below a platform item's body."""

from __future__ import annotations

from html import escape

import product_availability_labels
from anthus_content import ContentNode
from cards import _esc, _fm
from site_blocks import _pills

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

def _chips(items: list[tuple[str, str]]) -> str:
    return '<ul class="chips">' + "".join(
        f'<li><a class="chip" href="{_esc(h)}">{escape(t)}</a></li>' if h else f'<li><span class="chip">{escape(t)}</span></li>'
        for t, h in items
    ) + "</ul>"

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
        f"<h1>{escape(node.title)}{product_availability_labels.availability_chip_markup(node.title)}</h1>{_pills(node)}"
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

