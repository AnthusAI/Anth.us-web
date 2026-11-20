::band{size="bare"}

::raw
<section class="hero"><div class="container hero__grid"><div class="hero__copy"><p class="eyebrow">AI ENGINEERING · SINCE 2007</p>
<h1>AI that keeps working after the demo.<span class="cursor" aria-hidden="true"></span></h1>
<p class="lead">We build custom models, agent systems and knowledge bases, run them in production, and keep them aligned with the people who know the work.</p>
<div class="btn-row"><a class="btn" href="/engage/"><span>Tell us the problem &rarr;</span></a><a class="btn btn--ghost" href="/ai-solutions/"><span>See the work &rarr;</span></a></div>
</div>
<div class="hero__art">
::endraw

::include{kind="block" name="pictogram" id="hero-loop"}

::raw
</div>
</div>
</section>
<div class="proof-strip-wrap"><div class="container"><ul class="proof-strip" aria-label="Proof of work"><li><a href="/blog/call-criteria/">Call Criteria</a></li>
<li><a href="/blog/venue-driver/">Tao Group Hospitality</a></li>
<li><a href="/blog/venue-driver/">Hakkasan Group</a></li>
<li><a href="/ai-solutions/">In production since 2007</a></li>
</ul>
</div>
</div>
<div class="stats-wrap"><div class="container"><ul class="stats"><li><span class="stats__n">$250M</span><span class="stats__l">Processed in production</span></li>
<li><span class="stats__n">180B</span><span class="stats__l">Tokens of production LLM work</span></li>
<li><span class="stats__n">1</span><span class="stats__l">AWS data-center outage in 16 years, recovered without losing revenue</span></li>
<li><span class="stats__n">2007</span><span class="stats__l">Building production systems since</span></li>
</ul>
</div>
</div>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>01</span> <span>/</span> <span>What we do</span></p>
<h2>Four kinds of system. One way of running them.</h2>
<p class="lead">Clients usually arrive asking about one of these. The work rarely stays in one box.</p>
</header>
<div class="section__body"><ul class="grid grid--caps"><li class="card notch card--link"><div class="card__px">
::endraw

::include{kind="block" name="pictogram" id="knowledge-base"}

::raw
</div>
<h3><a href="https://github.com/AnthusAI/Biblicus">Knowledge Bases</a></h3>
<p>Your agents are only as good as what they can look up. We build knowledge bases with ontologies and taxonomies that learn from your data, instead of going stale the week after someone hand-built them.</p>
</li>
<li class="card notch card--link"><div class="card__px">
::endraw

::include{kind="block" name="pictogram" id="self-aligning"}

::raw
</div>
<h3><a href="/blog/call-criteria/">Self-Aligning Automation</a></h3>
<p>Business process automation with a human in the loop. Reviewers correct it and say why; the system turns the explanation into a stated policy and applies it from then on.</p>
</li>
<li class="card notch card--link"><div class="card__px">
::endraw

::include{kind="block" name="pictogram" id="agent-harness"}

::raw
</div>
<h3><a href="/blog/give-an-agent-a-tool/">Agent Systems</a></h3>
<p>A model is half a system. The other half is the harness: the tools it can reach, the procedures it follows, the limits it runs inside, and the ability to work for hours without losing the plot.</p>
</li>
<li class="card notch card--link"><div class="card__px">
::endraw

::include{kind="block" name="pictogram" id="confidence-gate"}

::raw
</div>
<h3><a href="/decision-models/">Machine Learning</a></h3>
<p>Custom classifiers, fine-tuned models, and decision models like Jev, with calibrated confidence that tells you which decisions to trust and which to escalate. We find the cheapest model that clears your bar and run it on AWS.</p>
</li>
</ul>
</div>
</div>
</section>
<section class="section section--band"><div class="container section__grid section__grid--stack"><header class="section__head"><p class="eyebrow"><span>02</span> <span>/</span> <span>Proof</span></p>
<h2>Systems that run for years, not weeks.</h2>
</header>
<div class="section__body"><ul class="grid grid--2"><li class="card notch case card--link"><div class="card__px">
::endraw

::include{kind="block" name="pictogram" id="scorecard"}

::raw
</div>
<h3 class="case__name"><a href="/blog/call-criteria/">Call Criteria</a><svg xmlns="http://www.w3.org/2000/svg" class="sm sm--call-criteria" viewBox="55 59 290 284" aria-hidden="true" focusable="false"><g class="sm-cc-navy" fill="none" stroke-linecap="butt"><path d="M124.2 120.2A69 63 0 0 0 122.6 245.6A139.5 139.5 0 0 1 124.2 120.2Z" fill="currentColor" stroke="none"/><path d="M115.0 246.5A146.8 146.8 0 0 0 222.5 329.1" stroke-width="13.5"/><path d="M304.1 239.7A78.7 78.7 0 1 1 304.1 129.3" stroke-width="20.5"/></g><g class="sm-cc-blue" fill="none" stroke-linecap="butt"><path d="M328.4 263.5A112.7 112.7 0 1 1 328.4 105.5" stroke-width="20.4"/><rect x="217" y="316" width="43" height="21" rx="5" stroke="none"/></g></svg></h3>
<p class="case__ctx">Call-center QA, scored by an outside service’s fine-tuned classifiers.</p>
<dl><div><dt>Problem</dt><dd>Too expensive and too slow to scale to every new scorecard.</dd></div>
<div><dt>What we did</dt><dd>We built their classifier lab on Primus in their own AWS account and ran it for years.</dd></div>
<div><dt>Outcome</dt><dd class="case__out">Hundreds of scorecards, millions of calls scored.</dd></div>
</dl></li>
<li class="card notch case card--link"><div class="card__px">
::endraw

::include{kind="block" name="pictogram" id="venue-system"}

::raw
</div>
<h3 class="case__name"><a href="/blog/venue-driver/">Venue Driver</a><img class="sm sm--venue-driver" src="/assets/site/venue-driver-logo.png" width="119" height="105" alt="" aria-hidden="true"></h3>
<p class="case__ctx">Ticketing, VIP table reservations and guest lists for Las Vegas nightlife.</p>
<dl><div><dt>What it was</dt><dd>A bespoke, serverless, event-driven system (AWS Lambda, Amplify, SQS), operationally mature.</dd></div>
<div><dt>What it integrated</dt><dd>Integrated with Tao Group’s in-house loyalty system, Madison Square Garden Entertainment’s ServiceNow ITSM, and a bespoke data warehouse and business intelligence system.</dd></div>
<div><dt>Outcome</dt><dd class="case__out">In continuous operation since 2007.</dd></div>
</dl></li>
</ul>
<p class="more"><a href="/ai-solutions/">All engagements</a></p>
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>03</span> <span>/</span> <span>Solutions</span></p>
<h2>Solutions we built from the work.</h2>
<p class="lead">Our in-house solutions, from a stack that grew out of real delivery work.</p>
</header>
<div class="section__body">
::endraw

::include{kind="block" name="products-grid"}

::include{kind="block" name="supporting-row"}

::raw
<p class="more"><a href="/platform/">The whole platform</a> <a href="https://github.com/AnthusAI" rel="noopener">Our repositories on GitHub</a></p>
</div>
</div>
</section>
<section class="section" id="primus-proof"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>04</span> <span>/</span> <span>In production</span></p>
<h2>Built and run for years.</h2>
</header>
<div class="section__body"><div class="prose-block"><p>Primus is the MLOps platform behind Call Criteria&#x27;s in-house classifier lab: one scorecard after another, evaluated, deployed and improved with reviewer feedback, running in their own AWS account.</p>
<p>We built it, then operated it for them for years. It is free and open source.</p>
</div>
<div class="btn-row"><a class="btn" href="/articles/call-criteria/"><span>Read the Call Criteria story &rarr;</span></a><a class="btn" href="https://primus.anth.us" rel="noopener"><span>See Primus &rarr;</span></a></div>
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>05</span> <span>/</span> <span>Articles</span></p>
<h2>Latest from the lab.</h2>
</header>
<div class="section__body">
::endraw

::include{kind="listing" collection="articles" count="6" card="text:code=0" layout="bare" tag="ul" class="grid grid--list"}

::raw
<p class="more"><a href="/blog/">All articles</a></p>
</div>
</div>
</section>
<section class="section section--band cta-band"><div class="container cta-band__in"><div><p class="eyebrow">PRESS START</p>
<h2>Bring us the problem.</h2>
<p class="lead">Even if you can’t yet say what you need. Working that out is part of the first month, and it’s often the most useful part.</p>
</div>
<div class="btn-row"><a class="btn" href="/engage/"><span>Tell us the problem &rarr;</span></a></div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>06</span> <span>/</span> <span>News</span></p>
<h2>Recent posts.</h2>
</header>
<div class="section__body">
::endraw

::include{kind="listing" collection="posts" count="3" card="mini" layout="bare" tag="ul" class="mini-grid"}

::raw
<div class="shorter shorter--flat shorter--cols">
::endraw

::include{kind="listing" collection="posts" skip="3" count="7" card="line" layout="bare" tag="ul"}

::raw
</div>
<p class="more"><a href="/posts/">All posts</a></p>
</div>
</div>
</section>
::endraw
