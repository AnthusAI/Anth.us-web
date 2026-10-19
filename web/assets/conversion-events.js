(function () {
  "use strict";
  var ENGAGE_PATH_PATTERN = /^\/engage(\/|\/index\.html|\.html)?$/;
  var MAXIMUM_LABEL_LENGTH = 100;
  var SAFE_LOCATION_PATTERN = /^[a-z0-9_-]{1,40}$/;

  function visibleLabelOf(anchor) {
    var label = (anchor.textContent || "").replace(/\s+/g, " ").replace(/\s*\u2192\s*$/, "").trim();
    return label.slice(0, MAXIMUM_LABEL_LENGTH);
  }

  function engageAnchorFrom(target) {
    var anchor = target && target.closest ? target.closest("a[href]") : null;
    if (!anchor || anchor.origin !== window.location.origin) return null;
    return ENGAGE_PATH_PATTERN.test(anchor.pathname) ? anchor : null;
  }

  function ctaLocationOf(anchor) {
    var named = new URL(anchor.href).searchParams.get("cta") || "";
    return SAFE_LOCATION_PATTERN.test(named) ? named : "page";
  }

  function reportEngageLinkActivation(event) {
    if (typeof window.gtag !== "function") return;
    var anchor = engageAnchorFrom(event.target);
    if (!anchor) return;
    try {
      window.gtag("event", "cta_click", {
        cta_text: visibleLabelOf(anchor),
        cta_location: ctaLocationOf(anchor),
        link_url: anchor.pathname,
        transport_type: "beacon"
      });
    } catch (ignored) {}
  }

  document.addEventListener("click", reportEngageLinkActivation);
  document.addEventListener("auxclick", reportEngageLinkActivation);
})();
