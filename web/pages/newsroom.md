::band{size="bare"}

::raw
<section class="hero hero--page"><div class="container hero__grid"><div class="hero__copy"><p class="eyebrow">NEWSROOM</p>
<h1>Inside the newsroom<span class="cursor" aria-hidden="true"></span></h1>
<p class="lead">What we are reading, what Cyclotron recommends, and what became a story. We keep a running list of sources. A decision model called Cyclotron estimates which ones we will want, and we make the final call.</p>
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>01</span> <span>/</span> <span>Latest story</span></p>
<h2>The newest story.</h2>
<p class="lead">Our most recent piece of writing.</p>
</header>
<div class="section__body">
::endraw

::include{kind="listing" sections="articles" count="1" card="text" layout="bare" tag="ul" class="grid grid--list"}

::raw
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>02</span> <span>/</span> <span>Recently accepted</span></p>
<h2>What we accepted lately.</h2>
<p class="lead">Sources that passed our review most recently, newest first. Each card says whether an editor or the system accepted it.</p>
</header>
<div class="section__body">
::endraw

::include{kind="references" select="recent" count="6" card="tile"}

::raw
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>03</span> <span>/</span> <span>More stories</span></p>
<h2>Earlier stories.</h2>
<p class="lead">The pieces we wrote before the latest one.</p>
</header>
<div class="section__body">
::endraw

::include{kind="listing" sections="articles" skip="1" count="4" card="mini" layout="bare" tag="ul" class="mini-grid"}

::raw
<p class="more"><a href="/blog/">All articles</a></p>
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>04</span> <span>/</span> <span>Highest confidence</span></p>
<h2>What Cyclotron was surest about.</h2>
<p class="lead">Accepted sources, ranked by how confident Cyclotron was that we would accept them. Confidence is its estimate, not a verdict.</p>
</header>
<div class="section__body">
::endraw

::include{kind="references" select="confident" count="6" card="row"}

::raw
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>05</span> <span>/</span> <span>Recommended, not yet accepted</span></p>
<h2>Waiting for our review.</h2>
<p class="lead">Sources Cyclotron expects us to accept. Nobody has decided yet, and we may decide otherwise.</p>
</header>
<div class="section__body">
::endraw

::include{kind="references" select="recommended" count="6" card="row" empty="Nothing is waiting for review right now."}

::raw
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>06</span> <span>/</span> <span>Conversations</span></p>
<h2>What we are discussing.</h2>
<p class="lead">Comments on public sources and published stories, most recently active first. Authors appear under a public handle or as the Editor.</p>
</header>
<div class="section__body">
::endraw

::include{kind="threads" select="recent" count="6" layout="list" empty="No conversations yet."}

::raw
</div>
</div>
</section>
::endraw
