import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';

const readSource = relativePath => fs.readFileSync(new URL(relativePath, import.meta.url), 'utf8');
const inquirySource = readSource('../web/static-root/engage-inquiry.js');
const navigationSource = readSource('../web/assets/site-nav.js');

const TYPED_VALUES = {name: 'Zelda Typewell', email: 'zelda.typewell@example.test', company: 'Typewell Holdings', message: 'Our unique private problem statement', website: ''};
const RECEIPT_IDENTIFIER = 'receipt-9f8e7d6c';
const ALLOWED_LEAD_PARAMETERS = ['form_id', 'lead_source', 'solution'];

function buildInquiryHarness(responses, {search = '', withGtag = true} = {}) {
  const button = {disabled: true}, receipt = {};
  const error = {parts: [], append(...nodes) { this.parts.push(...nodes); }};
  const elements = [button, {}, {}];
  let submit;
  const form = {dataset: {endpoint: 'https://intake.example.test/intake/demo', noticeVersion: 'contact-v1'},
    querySelector(selector) { return selector === 'button' ? button : selector === '[data-error]' ? error : receipt; },
    querySelectorAll() { return elements; }, addEventListener(_, handler) { submit = handler; }};
  const analyticsCalls = [];
  let identifiers = 0;
  const context = {
    document: {getElementById() { return form; }, createElement(tag) { return {tag}; }},
    crypto: {randomUUID() { return `00000000-0000-4000-8000-${String(++identifiers).padStart(12, '0')}`; }},
    location: {search},
    URLSearchParams, AbortSignal, FormData: class { get(key) { return TYPED_VALUES[key]; } },
    fetch: async () => { const result = responses.shift(); if (result instanceof Error) throw result; return result; },
  };
  if (withGtag) context.gtag = (...args) => analyticsCalls.push(JSON.parse(JSON.stringify(args)));
  vm.runInNewContext(inquirySource, context);
  return {form, analyticsCalls, send: () => submit({preventDefault() {}})};
}

const reply = (status, body) => ({ok: status >= 200 && status < 300, status, json: async () => {
  if (body === undefined) throw new SyntaxError('no body'); return body; }});
const accepted = receipt => reply(202, {receipt, message: 'Received.'});

function assertNoPersonalData(analyticsCalls) {
  const serialized = JSON.stringify(analyticsCalls);
  for (const value of [...Object.values(TYPED_VALUES).filter(Boolean), RECEIPT_IDENTIFIER]) {
    assert.ok(!serialized.includes(value), `payload must not contain ${value}`);
  }
  for (const key of ['name', 'email', 'company', 'message', 'receipt', 'submission_id']) {
    assert.ok(!serialized.includes(`"${key}"`), `payload must not carry a ${key} key`);
  }
}

test('generate_lead fires exactly once on a 202 receipt with only the allowed parameters', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {search: '?from=/ai-solutions/&cta=hero&solution=Primus'});
  await harness.send();
  assert.equal(harness.form.dataset.state, 'sent');
  assert.equal(harness.analyticsCalls.length, 1);
  const [verb, eventName, parameters] = harness.analyticsCalls[0];
  assert.equal(verb, 'event');
  assert.equal(eventName, 'generate_lead');
  assert.deepEqual(Object.keys(parameters).sort(), ALLOWED_LEAD_PARAMETERS);
  assert.deepEqual(parameters, {form_id: 'engage-inquiry', lead_source: '/ai-solutions/#hero', solution: 'Primus'});
  assertNoPersonalData(harness.analyticsCalls);
});

test('lead_source is direct and solution is omitted when the visit carries no attribution', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {search: ''});
  await harness.send();
  assert.deepEqual(harness.analyticsCalls[0][2], {form_id: 'engage-inquiry', lead_source: 'direct'});
});

test('attribution that does not look like a page path or a solution name is not sent', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)],
    {search: '?from=zelda.typewell@example.test&cta=Has Space&solution=a%40b.test'});
  await harness.send();
  assert.deepEqual(harness.analyticsCalls[0][2], {form_id: 'engage-inquiry', lead_source: 'direct'});
  assertNoPersonalData(harness.analyticsCalls);
});

test('a repeated submit that returns the same receipt does not fire a second lead', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER), accepted(RECEIPT_IDENTIFIER)]);
  await harness.send();
  await harness.send();
  assert.equal(harness.analyticsCalls.length, 1);
});

for (const [label, response] of [
  ['400', reply(400, {message: 'Bad email.'})],
  ['429', reply(429, {})],
  ['503', reply(503, {})],
  ['409', reply(409, {})],
  ['202 without a receipt', reply(202, {})],
  ['network failure', new TypeError('offline')],
]) {
  test(`nothing is sent on ${label}`, async () => {
    const harness = buildInquiryHarness([response]);
    await harness.send();
    assert.notEqual(harness.form.dataset.state, 'sent');
    assert.deepEqual(harness.analyticsCalls, []);
  });
}

test('a failed attempt followed by a retry that succeeds fires one lead', async () => {
  const harness = buildInquiryHarness([new TypeError('offline'), reply(503, {}), accepted(RECEIPT_IDENTIFIER)]);
  await harness.send();
  await harness.send();
  assert.equal(harness.analyticsCalls.length, 0);
  await harness.send();
  assert.equal(harness.analyticsCalls.length, 1);
});

test('a confirmed receipt without gtag loads and succeeds without errors', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {withGtag: false});
  await harness.send();
  assert.equal(harness.form.dataset.state, 'sent');
});

function buildAnchor({href, text, ancestors = [], origin = 'https://anth.us'}) {
  const url = new URL(href, origin);
  const anchor = {
    textContent: text, href: url.toString(), origin: url.origin, pathname: url.pathname, search: url.search,
    protocol: url.protocol, hostname: url.hostname, attributes: {},
    setAttribute(name, value) { anchor.attributes[name] = String(value); },
    getAttribute(name) { return name in anchor.attributes ? anchor.attributes[name] : null; },
    ancestors, id: '',
    closest(selector) {
      if (selector === 'a[href]') return anchor;
      const wanted = selector.replace(/^\./, '');
      const match = anchor.ancestors.find(entry => entry.selector === selector || entry.selector === wanted);
      return match ? match.element : null;
    },
  };
  Object.defineProperty(anchor, 'href', {
    get() { return url.toString(); },
    set(value) { const next = new URL(value); url.search = next.search; },
  });
  Object.defineProperty(anchor, 'search', {get() { return url.search; }});
  return anchor;
}

const ancestor = (selector, element = {id: ''}) => ({selector, element});

function attributeLinks(anchors, pathname = '/ai-solutions/') {
  const context = {
    document: {querySelector() { return null; }, querySelectorAll() { return anchors; }, addEventListener() {}},
    location: {pathname, origin: 'https://anth.us', search: ''}, URL, window: {addEventListener() {}},
  };
  vm.runInNewContext(navigationSource, context);
}

test('site navigation adds from and cta to engage links and keeps an existing solution', () => {
  const anchor = buildAnchor({href: '/engage/?solution=Primus', text: 'Work with us on Primus', ancestors: [ancestor('.card')]});
  attributeLinks([anchor], '/ai-solutions/');
  const query = new URL(anchor.href).searchParams;
  assert.equal(query.get('from'), '/ai-solutions/');
  assert.equal(query.get('cta'), 'solution-card');
  assert.equal(query.get('solution'), 'Primus');
});

test('site navigation leaves a link that already names its source alone', () => {
  const anchor = buildAnchor({href: '/engage/?from=/custom/&cta=custom', text: 'Go', ancestors: [ancestor('.hero')]});
  attributeLinks([anchor]);
  const query = new URL(anchor.href).searchParams;
  assert.equal(query.get('from'), '/custom/');
  assert.equal(query.get('cta'), 'custom');
});

test('site navigation records the location on engage and outbound links only', () => {
  const engage = buildAnchor({href: '/engage/', text: 'Go', ancestors: [ancestor('.cta-band')]});
  const outbound = buildAnchor({href: 'https://primus.anth.us', text: 'Visit Primus', ancestors: [ancestor('.card')]});
  const internal = buildAnchor({href: '/about/', text: 'About', ancestors: [ancestor('.card')]});
  attributeLinks([engage, outbound, internal]);
  assert.equal(engage.getAttribute('data-cta-location'), 'band');
  assert.equal(outbound.getAttribute('data-cta-location'), 'solution-card');
  assert.equal(internal.getAttribute('data-cta-location'), null);
  assert.equal(new URL(outbound.href).search, '');
});
