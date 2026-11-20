::band{size="bare"}

::raw
<section class="hero hero--page"><div class="container hero__grid"><div class="hero__copy"><p class="eyebrow">SOLUTIONS AND PLATFORM</p>
<h1>The tools we built doing the work.<span class="cursor" aria-hidden="true"></span></h1>
<p class="lead"><strong>A technology stack that grew out of real delivery work.</strong> It is not a speculative architecture diagram. This is the stack that emerged from building RLHF systems, durable agent workflows, retrieval-backed automation, hosted operator applications, and programmable media pipelines for real engagements. The same controls that matter in production software matter here: auditability, rollback paths, operator visibility, and clear evaluation loops.</p>
<div class="btn-row"><a class="btn" href="/ai-solutions/"><span>See the solutions we deliver &rarr;</span></a><a class="btn btn--ghost" href="/blog/cybernetic-development/"><span>Read the cybernetic development thesis &rarr;</span></a></div>
</div>
<div class="hero__art">
::endraw

::include{kind="block" name="pictogram" id="platform-stack"}

::raw
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>01</span> <span>/</span> <span>Solutions</span></p>
<h2>Our in-house solutions</h2>
</header>
<div class="section__body">
::endraw

::include{kind="block" name="products-grid"}

::raw
</div>
</div>
</section>
<section class="section section--band"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>02</span> <span>/</span> <span>Supporting technology</span></p>
<h2>What the solutions run on</h2>
<p class="lead">Smaller tools we use and ship alongside them, all open source.</p>
</header>
<div class="section__body">
::endraw

::include{kind="block" name="supporting-cards"}

::raw
<p class="more"><a href="https://github.com/AnthusAI" rel="noopener">All our repositories on GitHub</a></p>
</div>
</div>
</section>
<section class="section"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>03</span> <span>/</span> <span>The rest of the platform</span></p>
<h2>Also in the platform</h2>
</header>
<div class="section__body"><ul class="also-list">
::endraw

::include{kind="block" name="platform-lines" depends="platform"}

::raw
</ul>
</div>
</div>
</section>
<section class="section section--band"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>04</span> <span>/</span> <span>Layers</span></p>
<h2>How the platform fits together</h2>
<p class="lead">Complete AI systems need more than a model call, so we think about the platform in layers.</p>
</header>
<div class="section__body"><ul class="grid grid--mini"><li class="card notch  card--static"><h3>Runtime and control plane</h3>
<ul class="list"><li><strong>Korporus</strong> standardizes the shell and hosting model for platform-powered services.</li>
<li><strong>Chatticus</strong> gives people and bots a shared room with approvals.</li>
<li><strong>Primus</strong> manages evaluation, feedback loops, and MLOps.</li>
<li><strong>Kanbus</strong> keeps work orchestration and project memory durable.</li>
</ul>
</li>
<li class="card notch  card--static"><h3>Agent execution and data</h3>
<ul class="list"><li><strong>Tactus</strong> defines durable, sandboxed agent procedures.</li>
<li><strong>Antharchy</strong> is the agentic Linux desktop for long-running bot work.</li>
<li><strong>Biblicus</strong> turns corpora into extractable, retrievable knowledge.</li>
<li><strong>Virtuus</strong> makes structured JSON data queryable on disk.</li>
</ul>
</li>
<li class="card notch  card--static"><h3>Operations and media</h3>
<ul class="list"><li><strong>Caducus</strong> surfaces operator-facing health and incident signals.</li>
<li><strong>Babulus</strong> and <strong>VideoML</strong> apply the same code-first approach to content and video.</li>
<li>The result is one stack for systems, workflows, and communication.</li>
</ul>
</li>
</ul>
<div class="prose"><p>These are reusable building blocks, not isolated side projects. We combine them differently depending on the job: QA and evaluation, internal operator tooling, extraction and retrieval workflows, or outward-facing content systems.</p>
</div>
<h3 class="subhead">Common combinations</h3>
<ul class="grid grid--2"><li class="card notch  card--static"><h3>Research-to-output pipeline</h3>
<p>Biblicus collects and extracts the corpus, Tactus encodes the procedure, Babulus and VideoML generate the outward-facing output, and Korporus provides the place to run it as a service.</p>
</li>
<li class="card notch  card--static"><h3>Governed agent application</h3>
<p>Tactus defines the durable procedure, Primus measures and improves it, Kanbus tracks work and operator state, and Caducus helps humans see what is going wrong in production.</p>
</li>
<li class="card notch  card--static"><h3>Platform-native internal tooling</h3>
<p>Korporus supplies the shared shell while solution-specific modules from Primus, Kanbus, Biblicus, and future tools appear as interoperable applications instead of one-off surfaces.</p>
</li>
<li class="card notch  card--static"><h3>Multi-user agent workplace</h3>
<p>Chatticus is the shared room for people and named bots, Antharchy is the agentic desktop those bots can run, and Tactus encodes the durable procedures they execute with human approval boundaries.</p>
</li>
</ul>
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
::endraw
