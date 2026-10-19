/* Progressive enhancement for the Prospectus contact intake form.
 *
 * Request: POST <endpoint> as application/json with submission_id (a UUID used as the
 * idempotency/receipt key), name, email, company, message, website (honeypot),
 * notice_version ("contact-v1"), marketing_opt_in (false), page_path and campaign.
 * Success is HTTP 202 with {receipt, message}. Retries after an uncertain outcome
 * reuse the same submission_id as long as the content is unchanged. */
(() => {
  const form = document.getElementById('engage-inquiry');
  if (!form || !globalThis.crypto?.randomUUID) return;
  const button = form.querySelector('button');
  const error = form.querySelector('[data-error]');
  const receipt = form.querySelector('[data-receipt]');
  let pending = null;
  let sending = false;
  button.disabled = false;

  const RETRY = 'We couldn’t confirm your note. Try again without changing it.';
  const outcomes = {
    network: {text: RETRY, keepId: true},
    server: {text: RETRY, keepId: true},
    rate: {text: 'Too many requests right now. Wait a minute, then try again without changing your note.', keepId: true},
    conflict: {text: 'We couldn’t file this note automatically. Reload the page and send it again.', keepId: false},
    unavailable: {text: 'The form is not accepting notes from this page right now. Please try again later.', keepId: true},
  };
  function classify(status) {
    if (status === 429) return 'rate';
    if (status === 409) return 'conflict';
    if (status === 403 || status === 404 || status === 415) return 'unavailable';
    return 'server';
  }
  async function readJson(response) {
    try { return await response.json(); } catch { return {}; }
  }
  function fail(kind, detail) {
    const outcome = outcomes[kind];
    if (!outcome.keepId) pending = null;
    error.textContent = detail || outcome.text;
    button.disabled = false;
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (sending) return;
    const fields = new FormData(form);
    const campaign = {};
    const query = new URLSearchParams(location.search);
    for (const name of ['utm_source', 'utm_medium', 'utm_campaign']) {
      const value = query.get(name);
      if (value && /^[\w .-]{1,120}$/.test(value)) campaign[name] = value;
    }
    const data = JSON.stringify({
      name: String(fields.get('name') || ''), email: String(fields.get('email') || ''),
      company: String(fields.get('company') || ''), message: String(fields.get('message') || ''),
      website: String(fields.get('website') || ''), notice_version: form.dataset.noticeVersion,
      marketing_opt_in: false, page_path: '/engage', campaign,
    });
    if (!pending || pending.data !== data) pending = {data, id: crypto.randomUUID()};
    sending = true;
    button.disabled = true;
    error.textContent = '';
    try {
      let response;
      try {
        response = await fetch(form.dataset.endpoint, {
          method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'omit',
          body: JSON.stringify({...JSON.parse(data), submission_id: pending.id}),
          signal: AbortSignal.timeout(20000),
        });
      } catch {
        fail('network');
        return;
      }
      const result = await readJson(response);
      if (response.ok && typeof result.receipt === 'string' && result.receipt.trim()) {
        receipt.textContent = 'Thanks, we have your note. Receipt ' + result.receipt;
        form.querySelectorAll('input, textarea, button').forEach(field => { field.disabled = true; });
        pending = null;
      } else if (response.status === 400 && typeof result.message === 'string' && result.message) {
        fail('server', result.message + ' Please correct it and send again.');
      } else {
        fail(response.ok ? 'server' : classify(response.status));
      }
    } finally {
      sending = false;
    }
  });
})();
