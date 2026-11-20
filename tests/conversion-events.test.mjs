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

function buildInquiryHarness(responses, {search = '', withGtag = true, sessionStorage} = {}) {
  const handlers = {};
  const button = {disabled: true}, receipt = {};
  const error = {parts: [], append(...nodes) { this.parts.push(...nodes); }};
  const elements = [button, {}, {}];
  let submit;
  const form = {dataset: {endpoint: 'https://intake.example.test/intake/demo', noticeVersion: 'contact-v1'},
    querySelector(selector) { return selector === 'button' ? button : selector === '[data-error]' ? error : receipt; },
    querySelectorAll() { return elements; }, addEventListener(type, handler) { handlers[type] = handler; if (type === "submit") submit = handler; }};
  const analyticsCalls = [];
  const bodies = [];
  let identifiers = 0;
  const context = {
    document: {getElementById() { return form; }, createElement(tag) { return {tag}; }},
    crypto: {randomUUID() { return `00000000-0000-4000-8000-${String(++identifiers).padStart(12, '0')}`; }},
    location: {search},
    URLSearchParams, AbortSignal, FormData: class { get(key) { return TYPED_VALUES[key]; } },
    fetch: async (_, options) => { bodies.push(JSON.parse(options.body)); const result = responses.shift(); if (result instanceof Error) throw result; return result; },
  };
  if (sessionStorage) context.sessionStorage = sessionStorage;
  if (withGtag) context.gtag = (...args) => analyticsCalls.push(JSON.parse(JSON.stringify(args)));
  vm.runInNewContext(inquirySource, context);
  const named = name => analyticsCalls.filter(call => call[1] === name);
  return {form, analyticsCalls, named, get leadCalls() { return named('generate_lead'); }, handlers,
    type: (name = 'message') => handlers.input?.({target: {name}}),
    bodies, send: () => submit({preventDefault() {}})};
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
  assert.equal(harness.leadCalls.length, 1);
  const [verb, eventName, parameters] = harness.leadCalls[0];
  assert.equal(verb, 'event');
  assert.equal(eventName, 'generate_lead');
  assert.deepEqual(Object.keys(parameters).sort(), ALLOWED_LEAD_PARAMETERS);
  assert.deepEqual(parameters, {form_id: 'engage-inquiry', lead_source: '/ai-solutions/#hero', solution: 'Primus'});
  assertNoPersonalData(harness.analyticsCalls);
});

test('lead_source is direct and solution is omitted when the visit carries no attribution', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {search: ''});
  await harness.send();
  assert.deepEqual(harness.leadCalls[0][2], {form_id: 'engage-inquiry', lead_source: 'direct'});
});

test('attribution that does not look like a page path or a solution name is not sent', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)],
    {search: '?from=zelda.typewell@example.test&cta=Has Space&solution=a%40b.test'});
  await harness.send();
  assert.deepEqual(harness.leadCalls[0][2], {form_id: 'engage-inquiry', lead_source: 'direct'});
  assertNoPersonalData(harness.analyticsCalls);
});

test('a repeated submit that returns the same receipt does not fire a second lead', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER), accepted(RECEIPT_IDENTIFIER)]);
  await harness.send();
  await harness.send();
  assert.equal(harness.leadCalls.length, 1);
});

for (const [label, response] of [
  ['400', reply(400, {message: 'Bad email.'})],
  ['429', reply(429, {})],
  ['503', reply(503, {})],
  ['409', reply(409, {})],
  ['202 without a receipt', reply(202, {})],
  ['network failure', new TypeError('offline')],
]) {
  test(`no generate_lead on ${label}`, async () => {
    const harness = buildInquiryHarness([response]);
    await harness.send();
    assert.notEqual(harness.form.dataset.state, 'sent');
    assert.deepEqual(harness.leadCalls, []);
  });
}

test('a failed attempt followed by a retry that succeeds fires one lead', async () => {
  const harness = buildInquiryHarness([new TypeError('offline'), reply(503, {}), accepted(RECEIPT_IDENTIFIER)]);
  await harness.send();
  await harness.send();
  assert.equal(harness.leadCalls.length, 0);
  await harness.send();
  assert.equal(harness.leadCalls.length, 1);
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

// Funnel events (success events before the conversion, and the failure signal).
const FUNNEL_PARAMETERS = {form_id: 'engage-inquiry', lead_source: '/ai-solutions/#hero', solution: 'Primus'};
const ATTRIBUTED = '?from=/ai-solutions/&cta=hero&solution=Primus';

test('engage_view fires once when the form loads, with the lead attribution only', () => {
  const harness = buildInquiryHarness([], {search: ATTRIBUTED});
  assert.deepEqual(harness.named('engage_view').map(call => call[2]), [FUNNEL_PARAMETERS]);
  assert.equal(harness.analyticsCalls.length, 1);
});

test('lead_form_start fires once on the first typing, never for the hidden website field', () => {
  const harness = buildInquiryHarness([], {search: ATTRIBUTED});
  harness.type('website');
  assert.equal(harness.named('lead_form_start').length, 0);
  harness.type('name'); harness.type('email'); harness.type('message');
  assert.deepEqual(harness.named('lead_form_start').map(call => call[2]), [FUNNEL_PARAMETERS]);
});

test('the funnel runs in order on a successful note: view, start, submit, lead', async () => {
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {search: ATTRIBUTED});
  harness.type();
  await harness.send();
  assert.deepEqual(harness.analyticsCalls.map(call => call[1]), ['engage_view', 'lead_form_start', 'lead_form_submit', 'generate_lead']);
  for (const call of harness.analyticsCalls) assert.deepEqual(call[2], FUNNEL_PARAMETERS);
  assertNoPersonalData(harness.analyticsCalls);
});

test('a retry of the same note is one lead_form_submit; each failure reports its kind', async () => {
  const harness = buildInquiryHarness([new TypeError('offline'), reply(503, {}), accepted(RECEIPT_IDENTIFIER)]);
  await harness.send(); await harness.send(); await harness.send();
  assert.equal(harness.named('lead_form_submit').length, 1);
  assert.deepEqual(harness.named('lead_form_error').map(call => call[2]),
    [{form_id: 'engage-inquiry', error_kind: 'network'}, {form_id: 'engage-inquiry', error_kind: 'server'}]);
  assert.equal(harness.leadCalls.length, 1);
});

test('a validation reply reports error_kind validation without the server message', async () => {
  const harness = buildInquiryHarness([reply(400, {message: 'Enter a valid email address so we can reply.'})]);
  await harness.send();
  assert.deepEqual(harness.named('lead_form_error').map(call => call[2]), [{form_id: 'engage-inquiry', error_kind: 'validation'}]);
  assert.ok(!JSON.stringify(harness.analyticsCalls).includes('valid email'));
});

const storage = initial => {
  const values = {...initial};
  return {getItem: key => (key in values ? values[key] : null), setItem: (key, value) => { values[key] = String(value); }, values};
};

test('the note carries the campaign kept from the landing page when the Engage address has none', async () => {
  const kept = storage({'anthus-campaign': JSON.stringify({utm_source: 'machines-on-machines', utm_medium: 'house-ad', utm_campaign: 'busywork'})});
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {search: '?from=/ai-solutions/&cta=hero', sessionStorage: kept});
  await harness.send();
  assert.deepEqual(harness.bodies[0].campaign, {utm_source: 'machines-on-machines', utm_medium: 'house-ad', utm_campaign: 'busywork'});
});

test('UTM values on the Engage address win over the kept campaign', async () => {
  const kept = storage({'anthus-campaign': JSON.stringify({utm_source: 'older'})});
  const harness = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {search: '?utm_source=newsletter', sessionStorage: kept});
  await harness.send();
  assert.deepEqual(harness.bodies[0].campaign, {utm_source: 'newsletter'});
});

test('a kept campaign the intake would refuse is dropped, and broken storage never blocks the note', async () => {
  const bad = storage({'anthus-campaign': JSON.stringify({utm_source: 'a@b.test', utm_medium: 'ok', utm_term: 'x', utm_campaign: 'x'.repeat(121)})});
  const first = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {sessionStorage: bad});
  await first.send();
  assert.deepEqual(first.bodies[0].campaign, {utm_medium: 'ok'});
  const broken = {getItem() { throw new Error('denied'); }};
  const second = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {sessionStorage: broken});
  await second.send();
  assert.deepEqual(second.bodies[0].campaign, {});
  assert.equal(second.form.dataset.state, 'sent');
  const garbage = buildInquiryHarness([accepted(RECEIPT_IDENTIFIER)], {sessionStorage: storage({'anthus-campaign': '{not json'})});
  await garbage.send();
  assert.equal(garbage.form.dataset.state, 'sent');
});

function landOn({search = '', referrer = '', kept = {}} = {}) {
  const store = storage(kept);
  const context = {
    document: {querySelector() { return null; }, querySelectorAll() { return []; }, addEventListener() {}, referrer},
    location: {pathname: '/ai-solutions/', origin: 'https://anth.us', search}, URL, URLSearchParams,
    window: {addEventListener() {}, sessionStorage: store},
  };
  vm.runInNewContext(navigationSource, context);
  return store.values['anthus-campaign'] ? JSON.parse(store.values['anthus-campaign']) : null;
}

test('a landing page keeps its UTM values for the Engage form', () => {
  assert.deepEqual(landOn({search: '?utm_source=machines-on-machines&utm_medium=house-ad&utm_campaign=busywork&utm_term=x'}),
    {utm_source: 'machines-on-machines', utm_medium: 'house-ad', utm_campaign: 'busywork'});
});

test('without UTM values the first referring site is kept as a referral, and only the first', () => {
  assert.deepEqual(landOn({referrer: 'https://machines-on-machines.anth.us/some/story/'}), {utm_source: 'machines-on-machines.anth.us', utm_medium: 'referral'});
  assert.deepEqual(landOn({referrer: 'https://news.example.test/', kept: {'anthus-campaign': '{"utm_source":"first"}'}}), {utm_source: 'first'});
  assert.equal(landOn({referrer: 'https://anth.us/'}), null, 'a page of this site is not a referral');
  assert.equal(landOn({}), null);
});

test('UTM values the intake would refuse are never kept', () => {
  assert.equal(landOn({search: '?utm_source=a%40b.test'}), null);
});
