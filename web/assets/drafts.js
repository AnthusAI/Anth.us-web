/* drafts: reveal the hidden `.drafts-review` sections when the URL has `?drafts`.
 * Remembered for the session (sessionStorage) so pagination and tag links keep
 * showing drafts; `?drafts=0` turns it off. No UI links to this. */
(function () {
  var key = 'anthus-drafts', on = false, m = /[?&]drafts(?:=([^&#]*))?/.exec(location.search);
  try {
    if (m) {
      on = m[1] !== '0';
      if (on) sessionStorage.setItem(key, '1'); else sessionStorage.removeItem(key);
    } else {
      on = sessionStorage.getItem(key) === '1';
    }
  } catch (e) { on = !!m && m[1] !== '0'; }
  if (!on) return;
  function show() {
    [].forEach.call(document.querySelectorAll('.drafts-review'), function (el) { el.hidden = false; });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show); else show();
})();
