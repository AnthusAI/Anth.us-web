import cf from "cloudfront";

const redirectStore = cf.kvs();

const PATTERN_REDIRECT_RULES = [
  { pattern: /^\/blog\/page\/([^/]+)\/$/, target: "/articles/page/$1/" },
  { pattern: /^\/blog\/page\/([^/]+)\/index\.html$/, target: "/articles/page/$1/" },
  { pattern: /^\/blog\/([^/]+)\/$/, target: "/articles/$1/" },
  { pattern: /^\/blog\/([^/]+)\/index\.html$/, target: "/articles/$1/" },
  { pattern: /^\/biased-decisions(?:\/(.*))?$/, target: "https://biased-decisions.anth.us/$1" },
];

const SERVED_HTML_FILES = ["/404.html"];

function permanentRedirect(location) {
  return {
    statusCode: 301,
    statusDescription: "Moved Permanently",
    headers: { location: { value: location } },
  };
}

async function exactRedirectTarget(uri) {
  try {
    const target = await redirectStore.get(uri);
    return target ? String(target) : null;
  } catch (error) {
    return null;
  }
}

function patternRedirectTarget(uri) {
  for (let index = 0; index < PATTERN_REDIRECT_RULES.length; index++) {
    const rule = PATTERN_REDIRECT_RULES[index];
    const match = rule.pattern.exec(uri);
    if (match !== null) {
      const captured = match[1] === undefined ? "" : match[1];
      return rule.target.replace("$1", function () {
        return captured;
      });
    }
  }
  return null;
}

function lastSegmentHasExtension(uri) {
  return uri.substring(uri.lastIndexOf("/") + 1).indexOf(".") !== -1;
}

function isDirectoryIndexFile(uri) {
  return uri === "/index.html" || uri.endsWith("/index.html");
}

function staticHostingResult(request) {
  const uri = request.uri;
  if (uri.endsWith("/")) {
    request.uri = uri + "index.html";
    return request;
  }
  if (uri === "/404") {
    request.uri = "/404.html";
    return request;
  }
  if (lastSegmentHasExtension(uri)) {
    if (uri.endsWith(".html") && !isDirectoryIndexFile(uri) && SERVED_HTML_FILES.indexOf(uri) === -1) {
      return permanentRedirect(uri.substring(0, uri.length - ".html".length) + "/");
    }
    return request;
  }
  return permanentRedirect(uri + "/");
}

async function handler(event) {
  const request = event.request;
  const exactTarget = await exactRedirectTarget(request.uri);
  if (exactTarget !== null) {
    return permanentRedirect(exactTarget);
  }
  const patternTarget = patternRedirectTarget(request.uri);
  if (patternTarget !== null) {
    return permanentRedirect(patternTarget);
  }
  return staticHostingResult(request);
}
