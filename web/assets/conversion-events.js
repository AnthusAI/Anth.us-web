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

  // External product calls to action ("Visit Primus", "Join the beta"): a link that leaves the site for one of
  // our product sites, or whose label says so. Other outbound links (GitHub, LinkedIn) are not conversions.
  var PRODUCT_HOSTS = ["chattic.us", "p.apyr.us", "aurit.us", "kanb.us"];
  var PRODUCT_LABEL_PATTERN = /^(visit\s+\S|join the beta\b)/i;

  function isProductHost(hostname) {
    hostname = (hostname || "").toLowerCase();
    if (hostname === "anth.us" || /\.anth\.us$/.test(hostname)) return hostname !== "www.anth.us";
    return PRODUCT_HOSTS.indexOf(hostname) !== -1;
  }

  function externalProductAnchorFrom(target) {
    var anchor = target && target.closest ? target.closest("a[href]") : null;
    if (!anchor || anchor.origin === window.location.origin) return null;
    if (!/^https?:$/.test(anchor.protocol || "")) return null;
    return isProductHost(anchor.hostname) || PRODUCT_LABEL_PATTERN.test(visibleLabelOf(anchor)) ? anchor : null;
  }

  // Where the element sits, as site-nav.js recorded it. Never the page's own query string: a `cta=` value
  // from an earlier click must not label this one.
  function ctaLocationFromElement(anchor) {
    var recorded = anchor.getAttribute ? anchor.getAttribute("data-cta-location") || "" : "";
    return SAFE_LOCATION_PATTERN.test(recorded) ? recorded : "page";
  }

  // Destination host and path with no scheme, query string or fragment.
  function destinationOf(anchor) {
    var url = new URL(anchor.href);
    return url.hostname + url.pathname;
  }

  function reportEngageLinkActivation(event) {
    if (typeof window.gtag !== "function") return;
    var anchor = engageAnchorFrom(event.target);
    var parameters;
    if (anchor) {
      parameters = {
        cta_text: visibleLabelOf(anchor),
        cta_location: ctaLocationOf(anchor),
        link_url: anchor.pathname,
        transport_type: "beacon"
      };
    } else {
      anchor = externalProductAnchorFrom(event.target);
      if (!anchor) return;
      parameters = {
        cta_text: visibleLabelOf(anchor),
        cta_location: ctaLocationFromElement(anchor),
        link_url: destinationOf(anchor),
        transport_type: "beacon"
      };
    }
    try {
      window.gtag("event", "cta_click", parameters);
    } catch (ignored) {}
  }

  document.addEventListener("click", reportEngageLinkActivation);
  document.addEventListener("auxclick", reportEngageLinkActivation);
})();
