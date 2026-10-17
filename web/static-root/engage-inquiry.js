/* Progressive enhancement. The Google Form remains available on every outcome. */
(() => {
  const form = document.getElementById('engage-inquiry');
  if (!form || !globalThis.crypto?.randomUUID) return;
  const button = form.querySelector('button');
  const error = form.querySelector('[data-error]');
  const receipt = form.querySelector('[data-receipt]');
  let pending = null;
  let sending = false;
  button.disabled = false;
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
      const response = await fetch(form.dataset.endpoint, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'omit',
        body: JSON.stringify({...JSON.parse(data), submission_id: pending.id}),
        signal: AbortSignal.timeout(20000),
      });
      const result = await response.json();
      if (!response.ok || typeof result.receipt !== 'string' || !result.receipt.trim()) {
        throw new Error('No confirmed receipt');
      }
      receipt.textContent = 'Thanks, we have your note. Receipt ' + result.receipt;
      form.querySelectorAll('input, textarea, button').forEach(field => { field.disabled = true; });
      pending = null;
    } catch {
      error.textContent = 'We couldn’t confirm your note. Try again without changing it, or use the contact form below.';
      button.disabled = false;
    } finally {
      sending = false;
    }
  });
})();
