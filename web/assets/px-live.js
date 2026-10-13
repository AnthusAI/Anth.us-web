/* px-live: run pictogram and solution-mark animations only while on screen and the tab is visible.
 * Adds/removes .is-live on every .px figure and .sm mark. Vanilla, no deps, safe with defer.
 *
 * Motion is SMIL inside the SVGs (user units, so browser text zoom cannot misplace it):
 *  - .px figures start running at load (their negative begin shows an informative frame); this script pauses
 *    them with svg.pauseAnimations() and resumes only the visible svg (the hero has a wide and a tall one).
 *  - .sm marks use begin="indefinite": started with beginElement() when live, ended when not, so the logo pose
 *    shows otherwise.
 *  - prefers-reduced-motion: the animation elements are removed, leaving each sprite on its static pose.
 *  - Without JavaScript the pictograms simply run. */
(function () {
  var SEL = 'animate, animateTransform, animateMotion, set';
  function svgsOf(f) { return f.tagName.toLowerCase() === 'svg' ? [f] : [].slice.call(f.querySelectorAll('svg')); }
  function shown(s) { return s.getClientRects().length > 0; }
  function anims(f) { return [].slice.call(f.querySelectorAll(SEL)); }

  function init() {
    var figs = [].slice.call(document.querySelectorAll('.px, .sm'));
    if (!figs.length) return;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      figs.forEach(function (f) { anims(f).forEach(function (a) { a.parentNode.removeChild(a); }); });
      return;
    }
    function sync(f, live) {
      if (f.classList.contains('sm')) {
        if (live && !f.__on) { anims(f).forEach(function (a) { a.beginElement(); }); f.__on = true; }
        else if (!live && f.__on) { anims(f).forEach(function (a) { a.endElement(); }); f.__on = false; }
        return;
      }
      svgsOf(f).forEach(function (s) {
        if (!s.pauseAnimations) return;
        if (live && shown(s)) s.unpauseAnimations(); else s.pauseAnimations();
      });
    }
    figs.forEach(function (f) {  // start every figure paused at time 0, so all are in step
      if (f.classList.contains('px')) svgsOf(f).forEach(function (s) {
        if (s.pauseAnimations) { try { s.setCurrentTime(0); } catch (e) {} s.pauseAnimations(); }
      });
    });
    var seen = new Set();
    function apply(f) {
      var live = seen.has(f) && !document.hidden;
      f.classList.toggle('is-live', live);
      sync(f, live);
    }
    if (!('IntersectionObserver' in window)) {
      figs.forEach(function (f) { seen.add(f); apply(f); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) seen.add(e.target); else seen.delete(e.target);
        apply(e.target);
      });
    }, { threshold: 0.2 });
    figs.forEach(function (f) { io.observe(f); });
    document.addEventListener('visibilitychange', function () { figs.forEach(apply); });
    var tick = 0;  // the hero swaps its wide and tall svg at a breakpoint: re-sync which one runs
    window.addEventListener('resize', function () {
      if (tick) return;
      tick = window.requestAnimationFrame(function () { tick = 0; figs.forEach(apply); });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
