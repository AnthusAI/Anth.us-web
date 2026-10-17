import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source = fs.readFileSync(new URL('../web/static-root/engage-inquiry.js', import.meta.url), 'utf8');
function setup(responses) {
  const button = {disabled: true}, error = {}, receipt = {};
  const fields = {name:'Ada',email:'ada@example.test',company:'',message:'A pilot',website:''};
  const elements = [button, {}, {}];
  let submit;
  const form = {dataset:{endpoint:'https://intake.example.test',noticeVersion:'contact-v1'},
    querySelector(s) { return s === 'button' ? button : s === '[data-error]' ? error : receipt; },
    querySelectorAll() { return elements; }, addEventListener(_, handler) {submit=handler;}};
  const calls = [];
  let ids = 0;
  const context = {document:{getElementById(){return form;}},crypto:{randomUUID(){return `id-${++ids}`;}},
    location:{search:'?utm_source=site&utm_campaign=pilot&email=private&from=secret'},
    URLSearchParams, AbortSignal, FormData: class {get(key){return fields[key];}},
    fetch:async(url, options)=>{calls.push({url,...options});const result=responses.shift(); if(result instanceof Error)throw result;return result;}};
  vm.runInNewContext(source, context);
  return {button,error,receipt,fields,calls,elements,send:()=>submit({preventDefault(){}})};
}
const response = (receipt, ok=true) => ({ok,json:async()=>({receipt})});
test('retries preserve identity; success requires receipt and omits credentials', async()=>{
  const app=setup([new TypeError('offline'),response('received-1')]);
  assert.equal(app.button.disabled,false);
  await app.send(); assert.match(app.error.textContent,/couldn’t confirm/); assert.equal(app.button.disabled,false);
  await app.send();
  const first=JSON.parse(app.calls[0].body), second=JSON.parse(app.calls[1].body);
  assert.equal(first.submission_id,second.submission_id);
  assert.deepEqual(first.campaign,{utm_source:'site',utm_campaign:'pilot'});
  assert.equal(first.marketing_opt_in,false);
  assert.equal(first.page_path,'/engage');
  assert.equal(app.calls[0].credentials,'omit');
  assert.match(app.receipt.textContent,/received-1/);
  assert.ok(app.elements.every(x=>x.disabled));
});
test('unconfirmed 200 stays an error; edits start a new submission', async()=>{
  const app=setup([response(undefined),response('receipt-2')]);
  await app.send(); assert.match(app.error.textContent,/couldn’t confirm/); assert.equal(app.receipt.textContent,undefined);
  app.fields.message='Changed inquiry'; await app.send();
  assert.notEqual(JSON.parse(app.calls[0].body).submission_id,JSON.parse(app.calls[1].body).submission_id);
});
test('HTTP errors never claim receipt', async()=>{
  const app=setup([response('not-accepted',false)]); await app.send();
  assert.equal(app.receipt.textContent,undefined); assert.equal(app.button.disabled,false);
});
