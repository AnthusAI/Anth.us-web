::band{size="bare"}

::raw
<section class="hero hero--page"><div class="container hero__grid"><div class="hero__copy"><p class="eyebrow">DECISION MODELS</p>
<h1>Aligning Jev and other decision models to your data<span class="cursor" aria-hidden="true"></span></h1>
<p class="lead">A decision model like Jev answers a bounded question with a verdict and a confidence, in a fraction of a second, for a fraction of a cent. It arrives frozen: you can’t fine-tune it, and it doesn’t know your reviewers’ rules. Everything that makes it fit your business lives in the loop around it. Each step of that loop has a published measurement behind it, and we run the loop on client judgment tasks.</p>
</div>
<div class="hero__art">
::endraw

::include{kind="block" name="pictogram" id="verdict-meter"}

::raw
</div>
</div>
</section>
<section class="section"><div class="container section__grid section__grid--stack"><header class="section__head"><p class="eyebrow"><span>01</span> <span>/</span> <span>Questions</span></p>
<h2>The questions people arrive with</h2>
</header>
<div class="section__body"><ul class="grid grid--qa"><li class="card notch card--qa card--static"><h3>Can you fine-tune Jev?</h3>
<p>No. TypeSafe serves the same Jev weights to every account, so there is no fine-tuning endpoint. You get the same effect by changing the questions you ask it and fitting a small decision head over its answers, aligned from reviewer feedback. On 140 labels, one new plain-English question raised accuracy from 77 to 87 percent with the model unchanged.</p>
<div class="card__links"><a href="/blog/fine-tuning-jev/">Fine-Tuning Jev: You Can’t. Here’s What Gets You the Same Effect</a></div>
</li>
<li class="card notch card--qa card--static"><h3>How do I align Jev to my own data?</h3>
<p>Start classifying immediately, review the decisions as it makes them, and label the ones a reviewer disagrees with. Those labels refit the decision head and calibrate its confidence, and when disagreements keep coming, they tell you which question to add. That loop is far cheaper than building a labelled dataset before you start.</p>
<div class="card__links"><a href="/blog/primus-classifier-lab/">Primus Is a Classifier Lab</a></div>
</li>
<li class="card notch card--qa card--static"><h3>Can you trust Jev’s confidence?</h3>
<p>Higher really does mean more likely right, but out of the box it ran about 15 points overconfident on 8,801 labelled examples. Calibration against a few hundred of your own labels closes most of that gap, and only then can you set a threshold to auto-accept above and route the rest to a person.</p>
<div class="card__links"><a href="/blog/can-you-trust-jev-confidence/">Can You Trust Jev’s Confidence?</a></div>
</li>
<li class="card notch card--qa card--static"><h3>Does a decision model change its verdict on a name or a pronoun?</h3>
<p>It can. On two thousand real professional bios per job with one pronoun swapped, Jev’s verdict moved on 1 to 4 bios in 100 and the open-weights Laya’s on 8 to 18, almost always toward the stereotype. Auditing by slice before and after deployment is how you catch it.</p>
<div class="card__links"><a href="/blog/one-word-test/">The One-Word Test</a></div>
</li>
<li class="card notch card--qa card--static"><h3>Can I own the classifier instead of paying per request forever?</h3>
<p>Yes. Once the hosted model is aligned, you can distill it into a small model you serve yourself. A 66-million-parameter student trained from an aligned Jev system scored 91.2 percent against the human label, above its teacher’s 89.0, at 5 to 15 milliseconds an item, with a per-slice ship gate deciding when it was ready. You own and keep everything we build for you. Our solutions are open source and stay open. Integration code specific to your project is yours and private, and anything it depends on in our public projects stays public.</p>
<div class="card__links"><a href="/blog/distilling-jev-into-a-classifier/">Distilling an Aligned Jev System into a Classifier You Own</a></div>
</li>
<li class="card notch card--qa card--static"><h3>Can I run this loop myself?</h3>
<p>Yes. The loop is open source as <a href="https://cyclotron.anth.us/">Cyclotron</a>, under the MIT license. A cyclotron is one AI decision that learns from your reviewers’ corrections: it starts on day one with the decision model’s general training, refits a small model on each correction, and lets an LLM propose better questions that code tests before they go live. Run it yourself, have Anthus run it, or have Anthus <a href="https://cyclotron.anth.us/services">build it into your product</a>.</p>
</li>
<li class="card notch card--qa card--static"><h3>Should I use Jev or an open-weights decision model like Laya?</h3>
<p>The same reviewer loop aligns either one. On the same 140 labels and the same questions, Jev led Laya by 4.7 points alone and 6.8 with the feedback layer, and fully fine-tuning Laya on those labels beat both. Which engine you pick depends on whether you need to own the weights.</p>
<div class="card__links"><a href="/blog/jev-vs-laya/">Jev vs Laya</a></div>
</li>
</ul>
</div>
</div>
</section>
<section class="section section--band"><div class="container section__grid"><header class="section__head"><p class="eyebrow"><span>02</span> <span>/</span> <span>The loop</span></p>
<h2>The loop, in order</h2>
</header>
<div class="section__body"><ol class="steps"><li><div><strong>Start classifying now</strong><p>Put the decision model in front of real cases with the questions your reviewers already ask.</p>
</div>
</li>
<li><div><strong>Review and label the disagreements</strong><p>Reviewers agree or disagree with verdicts as they happen, and those calls are all the labelling the loop needs.</p>
</div>
</li>
<li><div><strong>Calibrate the confidence</strong><p>Fit the stated confidence to observed accuracy so a threshold means what it says.</p>
</div>
</li>
<li><div><strong>Change the questions when refits stall</strong><p>Let the system read the disagreements and propose one question; a person approves it.</p>
</div>
</li>
<li><div><strong>Gate every change by slice</strong><p>Promote a version only when it clears held-out labels on every slice reviewers care about.</p>
</div>
</li>
<li><div><strong>Distill when you’re ready to own it</strong><p>Train a small model from the aligned system and ship it behind the same gate.</p>
</div>
</li>
</ol>
<div class="prose"><p>Every step is a published experiment on the <a href="/research/">research page</a>, the public leaderboards are on the <a href="/benchmarks/">benchmarks page</a>, and <a href="https://primus.anth.us" rel="noopener">Primus</a> is where we run the loop in production.</p>
</div>
</div>
</div>
</section>
<section class="section section--band cta-band"><div class="container cta-band__in"><div><p class="eyebrow">PRESS START</p>
<h2>We do this for clients, at scale.</h2>
<p class="lead">Anthus has run this kind of loop in production for years: reviewers correct the model and say why, the explanation becomes policy, and the system gets more trustworthy month over month across hundreds of scorecards and millions of interactions. Bring us the judgment task and we’ll run it with your reviewers in the loop, and hand you a report you can inspect after the first month. The engine is open source: <a href="https://cyclotron.anth.us/">Cyclotron</a>.</p>
</div>
<div class="btn-row"><a class="btn" href="/engage/"><span>See how an engagement works &rarr;</span></a></div>
</div>
</section>
::endraw
