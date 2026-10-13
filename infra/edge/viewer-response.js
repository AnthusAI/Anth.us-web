const HTML_CACHE_CONTROL = "public, max-age=0, s-maxage=60, must-revalidate";
const ASSET_CACHE_CONTROL = "public, max-age=0, s-maxage=31536000";

const CONTENT_TYPE_BY_STORED_TYPE = {
  "text/html; charset=utf-8": "text/html",
  "application/xml": "text/xml",
  "text/plain; charset=utf-8": "text/plain",
};

function handler(event) {
  const response = event.response;
  const headers = response.headers;
  const stored = headers["content-type"] ? headers["content-type"].value : "";
  if (CONTENT_TYPE_BY_STORED_TYPE[stored] !== undefined) {
    headers["content-type"] = { value: CONTENT_TYPE_BY_STORED_TYPE[stored] };
  }
  if (response.statusCode !== 200) {
    delete headers["cache-control"];
    return response;
  }
  const isHtml = headers["content-type"] !== undefined && headers["content-type"].value === "text/html";
  headers["cache-control"] = { value: isHtml ? HTML_CACHE_CONTROL : ASSET_CACHE_CONTROL };
  return response;
}
