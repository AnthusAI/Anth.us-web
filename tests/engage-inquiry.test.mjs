import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source = fs.readFileSync(new URL('../web/static-root/engage-inquiry.js', import.meta.url), 'utf8');
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function setup(responses) {
  const button = {disabled: true}, error = {}, receipt = {};
  const fields = {name:'Test Person',email:'person@example.test',company:'',message:'A synthetic pilot',website:''};
  const elements = [button, {}, {}];
  let submit;
  const form = {dataset:{endpoint:'https://intake.example.test/intake/demo',noticeVersion:'contact-v1'},
    querySelector(s) { return s === 'button' ? button : s === '[data-error]' ? error : receipt; },
    querySelectorAll() { return elements; }, addEventListener(_, handler) {submit=handler;}};
  const calls = [];
  let ids = 0;
  const context = {document:{getElementById(){return form;}},
    crypto:{randomUUID(){return `00000000-0000-4000-8000-${String(++ids).padStart(12,'0')}`;}},
    location:{search:'?utm_source=site&utm_campaign=pilot&email=private&from=secret'},
    URLSearchParams, AbortSignal, FormData: class {get(key){return fields[key];}},
    fetch:async(url, options)=>{calls.push({url,...options});const result=responses.shift(); if(result instanceof Error)throw result;return result;}};
  vm.runInNewContext(source, context);
  return {button,error,receipt,fields,calls,elements,send:()=>submit({preventDefault(){}})};
}
const reply = (status, body) => ({ok: status >= 200 && status < 300, status, json: async () => {
  if (body === undefined) throw new SyntaxError('no body'); return body; }});
const accepted = receipt => reply(202, {receipt, message: 'Demo request received.'});

test('posts the Prospectus contract: JSON, contact-v1, UUID idempotency key, no credentials', async () => {
  const app = setup([accepted('r-1')]);
  assert.equal(app.button.disabled, false);
  await app.send();
  const [call] = app.calls, body = JSON.parse(call.body);
  assert.equal(call.url, 'https://intake.example.test/intake/demo');
  assert.equal(call.method, 'POST');
  assert.equal(call.headers['Content-Type'], 'application/json');
  assert.equal(call.credentials, 'omit');
  assert.deepEqual(Object.keys(body).sort(), ['campaign','company','email','marketing_opt_in','message','name','notice_version','page_path','submission_id','website']);
  assert.equal(body.notice_version, 'contact-v1');
  assert.match(body.submission_id, UUID);
  assert.equal(body.marketing_opt_in, false);
  assert.equal(body.page_path, '/engage');
  assert.deepEqual(body.campaign, {utm_source: 'site', utm_campaign: 'pilot'});
  assert.match(app.receipt.textContent, /r-1/);
  assert.ok(app.elements.every(x => x.disabled));
});

test('202 with a receipt is the only success', async () => {
  const app = setup([reply(202, {}), reply(200, {receipt: '  '})]);
  await app.send(); assert.match(app.error.textContent, /couldn’t confirm/); assert.equal(app.receipt.textContent, undefined);
  await app.send(); assert.equal(app.receipt.textContent, undefined); assert.equal(app.button.disabled, false);
});

test('network failure and 5xx retry with the same idempotency key', async () => {
  const app = setup([new TypeError('offline'), reply(503, {message: 'Retry the same receipt.'}), accepted('r-2')]);
  await app.send(); assert.match(app.error.textContent, /couldn’t confirm/); assert.equal(app.button.disabled, false);
  await app.send(); assert.match(app.error.textContent, /couldn’t confirm/);
  await app.send();
  const ids = app.calls.map(c => JSON.parse(c.body).submission_id);
  assert.equal(new Set(ids).size, 1);
  assert.match(app.receipt.textContent, /r-2/);
});

test('429 asks the visitor to wait and keeps the same key', async () => {
  const app = setup([reply(429, {message: 'Too Many Requests'}), accepted('r-3')]);
  await app.send(); assert.match(app.error.textContent, /Too many requests/); assert.equal(app.button.disabled, false);
  assert.equal(app.receipt.textContent, undefined);
  await app.send();
  assert.equal(JSON.parse(app.calls[0].body).submission_id, JSON.parse(app.calls[1].body).submission_id);
});

test('400 shows the server validation message and edits start a new submission', async () => {
  const app = setup([reply(400, {message: 'Enter a valid email address so we can reply.'}), accepted('r-4')]);
  await app.send();
  assert.match(app.error.textContent, /Enter a valid email address/); assert.equal(app.receipt.textContent, undefined);
  app.fields.email = 'fixed@example.test'; await app.send();
  assert.notEqual(JSON.parse(app.calls[0].body).submission_id, JSON.parse(app.calls[1].body).submission_id);
});

test('409 conflict drops the key so the next send is a fresh submission', async () => {
  const app = setup([reply(409, {message: 'Contact needs private duplicate review.'}), accepted('r-5')]);
  await app.send(); assert.match(app.error.textContent, /Reload the page/); assert.equal(app.receipt.textContent, undefined);
  await app.send();
  assert.notEqual(JSON.parse(app.calls[0].body).submission_id, JSON.parse(app.calls[1].body).submission_id);
});

test('403/415 and non-JSON error bodies never claim a receipt', async () => {
  const app = setup([reply(403, {message: 'This form origin is not allowed.'}), reply(502)]);
  await app.send(); assert.match(app.error.textContent, /not accepting notes/); assert.equal(app.receipt.textContent, undefined);
  await app.send(); assert.match(app.error.textContent, /couldn’t confirm/); assert.equal(app.button.disabled, false);
});

test('a second click while sending does not post twice', async () => {
  const app = setup([accepted('r-6')]);
  const first = app.send(); const second = app.send();
  await Promise.all([first, second]);
  assert.equal(app.calls.length, 1);
});
