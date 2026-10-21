::band{size="bare"}

::raw
<section class="hero hero--page"><div class="container hero__grid"><div class="hero__copy"><p class="eyebrow">BENCHMARKS</p>
<h1>Benchmarks<span class="cursor" aria-hidden="true"></span></h1>
<p class="lead">We publish two public benchmarks for decision models, the fast AI models that answer a bounded question with a verdict. Each one shows its method, every model’s results, and the cases behind them, so you can check a model against the decision you’re about to hand it.</p>
</div>
<div class="hero__art">
::endraw

::include{kind="block" name="pictogram" id="leaderboard"}

::raw
</div>
</div>
</section>
<section class="section section--tight"><div class="container"><ul class="grid grid--2"><li class="card notch  card--link"><h3><a href="https://biased-decisions.anth.us/">Biased-Decisions</a></h3>
<p class="card__sub">Does an AI model’s answer change when one personal detail about a person changes?</p>
<p>Would AI identify a different job for the same person if “he” became “she”? Would it remove the same online comment after its author said they were gay? Biased-Decisions changes one personal detail in a text, asks the same question again, and ranks models by how much more often the answer changes than it does after a neutral control edit of the same size.</p>
<div class="card__links"><a href="https://biased-decisions.anth.us/">See the results</a><a href="https://github.com/AnthusAI/Biased-Decisions">Code: AnthusAI/Biased-Decisions</a></div>
</li>
<li class="card notch  card--link"><h3><a href="https://hard-decisions.anth.us/">Hard-Decisions</a></h3>
<p class="card__sub">How far can a decision model follow a chain of reasoning before it starts guessing?</p>
<p>On true-or-false questions, every model tested except Jev falls to coin-flip accuracy by five chained inferences: the open decision models Kev, GLiNER2.5-Decide and Laya, GPT-6 Luna used as a one-shot classifier, and GLiDE. Jev still answers 89.3% correctly at that depth.</p>
<div class="card__links"><a href="https://hard-decisions.anth.us/">See the results</a></div>
</li>
</ul>
<div class="prose" style="margin-top:2.5rem"><p>The articles that explain these findings are on the <a href="/research/">research page</a>, and the guide to aligning a decision model to your own data is <a href="/decision-models/">here</a>.</p>
</div>
</div>
</section>
<section class="section section--band cta-band"><div class="container cta-band__in"><div><p class="eyebrow">PRESS START</p>
<h2>We do this for clients, at scale.</h2>
<p class="lead">Anthus has run this kind of loop in production for years: reviewers correct the model and say why, the explanation becomes policy, and the system gets more trustworthy month over month across hundreds of scorecards and millions of interactions. Bring us the judgment task and we’ll run it on Primus with your reviewers in the loop, and hand you a scorecard you can inspect after the first month.</p>
</div>
<div class="btn-row"><a class="btn" href="/engage/"><span>See how an engagement works &rarr;</span></a></div>
</div>
</section>
::endraw
