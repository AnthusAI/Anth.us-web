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
 * (`/engage/?from=<page>`) and the part of the page it sits in (`cta=<location>`), and the Engage page
 * passes both to the contact form and to the lead event. A link may already name a solution
 * (`?solution=<name>`).
 *
 * Every Engage link and every link that leaves the site also gets `data-cta-location`, computed from where
 * the element sits in this page. Papyrus's shared GA4 listener (markus_renderer/analytics_events.py)
 * sends the call-to-action click event for any link carrying it, with this value as `cta_location`, so a product call to action reports
 * its own location and never a `cta=` value carried in from an earlier click. This site sends no such event itself. */
(function () {
  "use strict";
  var onEngagePage = /^\/engage\//.test(location.pathname);
  var locationSelectors = [
    [".site-header", "header"],
    [".site-footer", "footer"],
    [".hero", "hero"],
    [".cta-band", "band"],
    [".engage-box", "article"],
    [".card", "solution-card"]
  ];
  function ctaLocationFor(anchor) {
    for (var i = 0; i < locationSelectors.length; i++) {
      if (anchor.closest(locationSelectors[i][0])) return locationSelectors[i][1];
    }
    var section = anchor.closest("section[id]");
    return section ? section.id.toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 40) || "page" : "page";
  }
  var links = document.querySelectorAll('a[href]');
  for (var i = 0; i < links.length; i++) {
    var a = links[i];
    var sameSite = a.origin === location.origin;
    var toEngage = sameSite && /^\/engage(\/|\/index\.html|\.html)?$/.test(a.pathname);
    var offSite = !sameSite && /^https?:$/.test(a.protocol || "");
    if (!toEngage && !offSite) continue;
    var where = ctaLocationFor(a);
    a.setAttribute("data-cta-location", where);
    if (!toEngage || onEngagePage) continue;
    var u = new URL(a.href);
    if (a.search.indexOf("from=") === -1) u.searchParams.set("from", location.pathname);
    if (!u.searchParams.has("cta")) u.searchParams.set("cta", where);
    a.href = u.toString();
  }
})();

/* Where the visit came from, kept for the contact form. Ads and links from other sites usually land on a
 * page other than Engage, and the Engage links above replace the address, so the UTM values would be gone
 * by the time a visitor writes. The landing page's UTM values (or, without any, the referring site as
 * `utm_source=<host>`, `utm_medium=referral`) go to sessionStorage under `anthus-campaign`; the Engage form
 * sends them as the note's campaign. Only the first referral of a tab is kept; a later page with UTM values
 * replaces it. Values the intake would refuse are never stored. Nothing here is sent anywhere by itself. */
(function () {
  "use strict";
  var KEY = "anthus-campaign";
  var NAMES = ["utm_source", "utm_medium", "utm_campaign"];
  var VALUE = /^[\w .-]{1,120}$/;
  try {
    var store = window.sessionStorage;
    if (!store) return;
    var query = new URLSearchParams(location.search);
    var found = {}, any = false;
    NAMES.forEach(function (name) {
      var value = query.get(name);
      if (value && VALUE.test(value)) { found[name] = value; any = true; }
    });
    if (any) { store.setItem(KEY, JSON.stringify(found)); return; }
    if (store.getItem(KEY) || !document.referrer) return;
    var from = new URL(document.referrer);
    if (/^https?:$/.test(from.protocol) && from.origin !== location.origin && VALUE.test(from.hostname))
      store.setItem(KEY, JSON.stringify({utm_source: from.hostname, utm_medium: "referral"}));
  } catch (e) {}
})();
