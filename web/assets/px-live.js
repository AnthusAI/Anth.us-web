/* px-live: run pictogram animations only while on screen and the tab is visible.
 * Adds/removes .is-live on every .px figure. Vanilla, no deps, safe with defer. */
(function () {
  function init() {
    var figs = [].slice.call(document.querySelectorAll('.px'));
    if (!figs.length) return;
    if (!('IntersectionObserver' in window)) {
      figs.forEach(function (f) { f.classList.add('is-live'); });
      return;
    }
    var seen = new Set();
    function apply(f) {
      f.classList.toggle('is-live', seen.has(f) && !document.hidden);
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) seen.add(e.target); else seen.delete(e.target);
        apply(e.target);
      });
    }, { threshold: 0.2 });
    figs.forEach(function (f) { io.observe(f); });
    document.addEventListener('visibilitychange', function () { figs.forEach(apply); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
