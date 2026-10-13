const HTML_CACHE_CONTROL = "public, max-age=0, s-maxage=60, must-revalidate";
const ASSET_CACHE_CONTROL = "public, max-age=0, s-maxage=31536000";
const UTF8_SUFFIX = "; charset=utf-8";

function previousContentType(stored) {
  const withoutCharset = stored.endsWith(UTF8_SUFFIX) ? stored.substring(0, stored.length - UTF8_SUFFIX.length) : stored;
  return withoutCharset === "application/xml" ? "text/xml" : withoutCharset;
}

function handler(event) {
  const response = event.response;
  const headers = response.headers;
  if (headers["content-type"] !== undefined) {
    headers["content-type"] = { value: previousContentType(headers["content-type"].value) };
  }
  if (response.statusCode !== 200) {
    delete headers["cache-control"];
    return response;
  }
  const isHtml = headers["content-type"] !== undefined && headers["content-type"].value === "text/html";
  headers["cache-control"] = { value: isHtml ? HTML_CACHE_CONTROL : ASSET_CACHE_CONTROL };
  return response;
}
