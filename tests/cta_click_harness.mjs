// Runs the real site-nav.js and the real Papyrus events script (read from a rendered page) against fake links, and
// prints every gtag call each click produced. Input on stdin: {navigationSource, eventsScript, pathname, links}.
import vm from 'node:vm';
import fs from 'node:fs';

const {navigationSource, eventsScript, pathname, links} = JSON.parse(fs.readFileSync(0, 'utf8'));
const ORIGIN = 'https://anth.us';

function buildAnchor({href, text, within}) {
  const url = new URL(href, ORIGIN);
  const attributes = {};
  const anchor = {
    textContent: text, origin: url.origin, pathname: url.pathname, protocol: url.protocol, hostname: url.hostname,
    setAttribute(name, value) { attributes[name] = String(value); },
    getAttribute(name) { return name in attributes ? attributes[name] : null; },
    closest(selector) {
      if (selector === 'a[href]') return anchor;
      return within.includes(selector) ? {id: ''} : null;
    },
  };
  Object.defineProperty(anchor, 'href', {get() { return url.toString(); }, set(value) { url.search = new URL(value).search; }});
  Object.defineProperty(anchor, 'search', {get() { return url.search; }});
  return anchor;
}

const anchors = links.map(buildAnchor);
const listeners = {click: [], auxclick: []};
const calls = [];
const context = {
  document: {
    querySelector() { return null; }, querySelectorAll() { return anchors; },
    addEventListener(type, handler) { (listeners[type] ||= []).push(handler); },
  },
  location: {pathname, origin: ORIGIN, search: '', href: ORIGIN + pathname},
  window: {addEventListener() {}}, URL, dataLayer: [],
};
context.window.gtag = context.gtag = (...args) => calls.push(JSON.parse(JSON.stringify(args)));
vm.runInNewContext(navigationSource, context);
vm.runInNewContext(eventsScript, context);

const results = anchors.map(anchor => {
  calls.length = 0;
  for (const handler of listeners.click) handler({target: anchor});
  return calls.map(([verb, name, parameters]) => ({verb, name, parameters}));
});
console.log(JSON.stringify(results));
