/* Anth.us masthead nav: collapse to a hamburger on narrow viewports.
 *
 * The Gatsby site uses `priority-plus`, which measures the rendered nav and
 * moves whatever overflows into a dropdown. Papyrus's Markus shell decides
 * geometry before render and this build ships no measurement library, so the
 * static equivalent is a plain breakpoint toggle: below 720px the links
 * collapse behind a hamburger, above it they lay out inline. The links are in
 * the markup either way, so this is progressive enhancement only — with
 * JavaScript off, CSS wraps the nav onto a second line and everything stays
 * reachable.
 */
(function () {
  "use strict";

  var BREAKPOINT = 720;

  function init() {
    var nav = document.querySelector(".markus-site-nav");
    if (!nav || nav.dataset.anthusNav === "ready") {
      return;
    }
    nav.dataset.anthusNav = "ready";

    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "anthus-nav-toggle";
    toggle.setAttribute("aria-label", "Toggle site navigation");
    toggle.setAttribute("aria-expanded", "false");
    toggle.innerHTML = '<span class="hamburger"></span>';
    nav.parentNode.insertBefore(toggle, nav);

    function apply() {
      var narrow = window.innerWidth < BREAKPOINT;
      toggle.hidden = !narrow;
      if (!narrow) {
        nav.removeAttribute("data-collapsed");
        toggle.setAttribute("aria-expanded", "false");
      } else if (!nav.hasAttribute("data-collapsed")) {
        nav.setAttribute("data-collapsed", "");
      }
    }

    toggle.addEventListener("click", function () {
      var collapsed = nav.hasAttribute("data-collapsed");
      if (collapsed) {
        nav.removeAttribute("data-collapsed");
      } else {
        nav.setAttribute("data-collapsed", "");
      }
      toggle.setAttribute("aria-expanded", collapsed ? "true" : "false");
    });

    apply();
    window.addEventListener("resize", apply);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
