(() => {
  const form = document.getElementById('engage-inquiry');
  if (!form) return;
  if (!globalThis.crypto?.randomUUID) {
    // The submit button stays disabled without an idempotency key, so say so and offer email instead of
    // leaving a button that silently does nothing.
    const unsupportedError = form.querySelector('[data-error]');
    const address = form.dataset.fallbackEmail || '';
    if (unsupportedError) {
      if (address) {
        const mailLink = document.createElement('a');
        mailLink.href = 'mailto:' + address;
        mailLink.textContent = address;
        unsupportedError.textContent = 'This form can’t run in your browser. Please email ';
        unsupportedError.append(mailLink, ' instead.');
      } else {
        unsupportedError.textContent = 'This form can’t run in your browser. Please try another browser.';
      }
    }
    form.dataset.state = 'unsupported';
    return;
  }
  // Time since the form was rendered, sent as the optional `elapsed_ms` intake field. Prospectus
  // only uses it as a weak spam signal after the note is stored; it never changes the reply.
  const clock = () => (typeof globalThis.performance?.now === 'function' ? globalThis.performance.now() : Date.now());
  const renderedAt = clock();
  const MAX_ELAPSED_MS = 86400000;
  function elapsedSinceRender() {
    const elapsed = Math.round(clock() - renderedAt);
    return Number.isFinite(elapsed) ? Math.min(Math.max(elapsed, 0), MAX_ELAPSED_MS) : 0;
  }
  const button = form.querySelector('button');
  const error = form.querySelector('[data-error]');
  const receipt = form.querySelector('[data-receipt]');
  let pending = null;
  let sending = false;
  const reportedReceipts = new Set();
  button.disabled = false;

  const fallbackEmail = form.dataset.fallbackEmail || '';
  const uncertainOutcomeLead = 'We couldn’t confirm your note. Try again without changing it';
  const outcomes = {
    network: {lead: uncertainOutcomeLead, keepId: true},
    server: {lead: uncertainOutcomeLead, keepId: true},
    rate: {lead: 'Too many requests right now. Wait a minute, then try again without changing your note', keepId: true},
    conflict: {text: 'We couldn’t file this note automatically. Reload the page and send it again.', keepId: false},
    unavailable: {lead: 'The form is not accepting notes from this page right now. Please try again later', keepId: true},
  };
  function failureKindForStatus(status) {
    if (status === 429) return 'rate';
    if (status === 409) return 'conflict';
    if (status === 403 || status === 404 || status === 415) return 'unavailable';
    return 'server';
  }
  const sourcePathPattern = /^[\w\/.-]{1,100}$/;
  const sourceLocationPattern = /^[a-z0-9_-]{1,40}$/;
  const solutionNamePattern = /^[\w .-]{1,60}$/;
  function leadAttributionFromLocation() {
    const query = new URLSearchParams(location.search);
    const fromPage = query.get('from') || '';
    const callToActionLocation = query.get('cta') || '';
    const solution = query.get('solution') || '';
    const pageSource = sourcePathPattern.test(fromPage) ? fromPage : '';
    const locationSource = sourceLocationPattern.test(callToActionLocation) ? callToActionLocation : '';
    const leadSource = pageSource || locationSource
      ? (pageSource || 'direct') + (locationSource ? '#' + locationSource : '')
      : 'direct';
    const attribution = {form_id: 'engage-inquiry', lead_source: leadSource};
    if (solutionNamePattern.test(solution)) attribution.solution = solution;
    return attribution;
  }
  function reportLeadOnce(receiptId) {
    if (reportedReceipts.has(receiptId)) return;
    reportedReceipts.add(receiptId);
    if (typeof globalThis.gtag !== 'function') return;
    try { globalThis.gtag('event', 'generate_lead', leadAttributionFromLocation()); } catch {}
  }
  async function readJson(response) {
    try { return await response.json(); } catch { return {}; }
  }
  function showFailure(kind, detail) {
    const outcome = outcomes[kind];
    if (!outcome.keepId) pending = null;
    if (detail || outcome.text || !fallbackEmail) {
      error.textContent = detail || outcome.text || outcome.lead + '.';
    } else {
      const link = document.createElement('a');
      link.href = 'mailto:' + fallbackEmail;
      link.textContent = fallbackEmail;
      error.textContent = outcome.lead + ', or email ';
      error.append(link, '.');
    }
    form.dataset.state = 'error';
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
    // A retry of the same note keeps its receipt and its first timing.
    if (!pending || pending.data !== data) pending = {data, id: crypto.randomUUID(), elapsed: elapsedSinceRender()};
    sending = true;
    form.dataset.state = 'sending';
    button.disabled = true;
    error.textContent = '';
    try {
      let response;
      try {
        response = await fetch(form.dataset.endpoint, {
          method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'omit',
          body: JSON.stringify({...JSON.parse(data), submission_id: pending.id, elapsed_ms: pending.elapsed}),
          signal: AbortSignal.timeout(20000),
        });
      } catch {
        showFailure('network');
        return;
      }
      const result = await readJson(response);
      if (response.ok && typeof result.receipt === 'string' && result.receipt.trim()) {
        receipt.textContent = 'Thanks, we have your note. Receipt ' + result.receipt;
        form.querySelectorAll('input, textarea, button').forEach(field => { field.disabled = true; });
        pending = null;
        form.dataset.state = 'sent';
        reportLeadOnce(result.receipt.trim());
      } else if (response.status === 400 && typeof result.message === 'string' && result.message) {
        showFailure('server', result.message + ' Please correct it and send again.');
      } else {
        showFailure(response.ok ? 'server' : failureKindForStatus(response.status));
      }
    } finally {
      sending = false;
    }
  });
})();
