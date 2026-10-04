/* Anth.us masthead nav.
 *
 * The production Gatsby site runs `priority-plus` over the `.js-p-target`
 * nav list (src/components/header.js), which measures the rendered nav with
 * IntersectionObserver and moves whatever overflows into a dropdown behind a
 * hamburger toggle. That library is vendored verbatim beside this file as
 * `priority-plus.js` (ISC, priority-plus 1.5.1, jayfreestone) and its CSS is
 * already part of the compiled theme — layout.scss @imports it, so the
 * `.p-plus*` rules in web/css/anthus-theme.css are the real ones.
 *
 * Initialising it here with the same `innerToggleTemplate` is what makes the
 * narrow-viewport nav behave identically to production instead of being
 * approximated by a CSS breakpoint.
 */
(function () {
  "use strict";

  function init() {
    var target = document.querySelector(".js-p-target");
    if (!target || target.dataset.pPlus === "ready") {
      return;
    }
    if (typeof window.priorityPlus !== "function") {
      // Vendored script missing or blocked: the <ul> is plain markup, so every
      // link stays reachable and CSS wraps it. Fail quiet, not broken.
      return;
    }
    target.dataset.pPlus = "ready";
    try {
      window.priorityPlus(target, {
        innerToggleTemplate: '<div class="hamburger"></div>',
      });
    } catch (error) {
      if (window.console && window.console.error) {
        window.console.error("Error initializing priorityPlus:", error);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
