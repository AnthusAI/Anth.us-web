/* Anth.us header menu: below 78rem the nav collapses behind a MENU button.
 * Without JavaScript the nav is a plain, wrapping list (the `js` class that
 * enables the collapsed layout is added by an inline script in <head>). */
(function () {
  "use strict";
  var header = document.querySelector(".site-header");
  var toggle = header && header.querySelector(".site-menu-toggle");
  if (!toggle) return;

  function set(open) {
    header.setAttribute("data-open", open ? "true" : "false");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  toggle.addEventListener("click", function () {
    set(header.getAttribute("data-open") !== "true");
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && header.getAttribute("data-open") === "true") {
      set(false);
      toggle.focus();
    }
  });
  header.addEventListener("click", function (event) {
    if (event.target.closest && event.target.closest(".site-nav a")) set(false);
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth >= 1248) set(false);
  });
})();

/* Intent from the click: a link to the Engage page carries the page it was clicked on
 * (`/engage/?from=<page>`), and the Engage page passes it to the contact form. A link may already
 * name a solution (`?solution=<name>`). */
(function () {
  "use strict";
  if (/^\/engage\//.test(location.pathname)) return;
  var links = document.querySelectorAll('a[href]');
  for (var i = 0; i < links.length; i++) {
    var a = links[i];
    if (a.origin !== location.origin || !/^\/engage(\/|\/index\.html|\.html)?$/.test(a.pathname)) continue;
    if (a.search.indexOf("from=") !== -1) continue;
    var u = new URL(a.href);
    u.searchParams.set("from", location.pathname);
    a.href = u.toString();
  }
})();
