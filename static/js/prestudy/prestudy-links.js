// static/js/prestudy/prestudy-links.js
// Shared glue for test prestudy (wiki/features/test-prestudy.md) on the pages
// that take a test: the standalone test page (templates/test.html) and the
// daily-session reading/listening player.
//
//   - the "prestudied" marker the prestudy page leaves in sessionStorage, sent
//     as `prestudied: true` on submit (the server verifies it against
//     prestudy_sessions once that table exists);
//   - the post-test action: a follow-up prime on the words behind wrong answers,
//     then Produce (dual translation of the passage window with the most
//     primed words).
//
// Classic script: exposes window.LinguaPrestudyLinks.
(function (root) {
  'use strict';

  const MARKER_PREFIX = 'prestudy:';
  const PRODUCE_KEY = 'prestudy_produce';
  const WINDOW_MS = 6 * 3600 * 1000;
  const COMPREHENSION = ['reading', 'listening'];

  function t(key, params, fallback) {
    if (root.LinguaI18n && typeof root.LinguaI18n.t === 'function') {
      const v = root.LinguaI18n.t(key, params);
      if (v && v !== key) return v;
    }
    return fallback || key;
  }

  function markerKey(slug) {
    let s = String(slug || '');
    try { s = decodeURIComponent(s); } catch { /* keep raw */ }
    return MARKER_PREFIX + s;
  }

  function readJson(key) {
    try { return JSON.parse(root.sessionStorage.getItem(key) || 'null'); } catch { return null; }
  }

  function isPrestudied(slug, now) {
    const m = readJson(markerKey(slug));
    return !!(m && m.at && ((now || Date.now()) - m.at) < WINDOW_MS);
  }

  function clearMarker(slug) {
    try { root.sessionStorage.removeItem(markerKey(slug)); } catch { /* storage blocked */ }
  }

  function followupUrl(slug, opts) {
    const o = opts || {};
    const p = new URLSearchParams({ mode: 'followup', type: o.type === 'listening' ? 'listening' : 'reading' });
    if (o.returnTo) p.set('return', o.returnTo);
    return '/test/' + encodeURIComponent(slug) + '/prestudy?' + p.toString();
  }

  // A Produce request the next daily-session translation slot should honour.
  function setProduceRequest(slug, testId) {
    try {
      root.sessionStorage.setItem(PRODUCE_KEY, JSON.stringify({ slug: String(slug), test_id: testId || null, at: Date.now() }));
    } catch { /* storage blocked */ }
  }

  function takeProduceRequest(now) {
    const r = readJson(PRODUCE_KEY);
    try { root.sessionStorage.removeItem(PRODUCE_KEY); } catch { /* storage blocked */ }
    return r && r.slug && r.at && ((now || Date.now()) - r.at) < WINDOW_MS ? r : null;
  }

  /**
   * Add the post-test action under a result banner.
   *   container  element to append to
   *   o.slug, o.type ('reading'|'listening'), o.wrong (number of wrong answers),
   *   o.prestudied (bool), o.returnTo ('session' or undefined),
   *   o.beforeLeave async () => void, awaited before navigating (the session
   *   player persists the test's completion there).
   * Returns the element, or null when there is nothing to offer.
   */
  function renderResultActions(container, o) {
    if (!container || !o || !o.slug || COMPREHENSION.indexOf(o.type) === -1) return null;
    const wrong = Number(o.wrong) || 0;
    if (!wrong && !o.prestudied) return null;
    const doc = container.ownerDocument || root.document;
    const box = doc.createElement('div');
    box.className = 'prestudy-result-actions d-flex flex-wrap align-items-center gap-2 mt-2';
    box.dataset.prestudyActions = '1';
    const btn = doc.createElement('a');
    btn.className = 'btn btn-outline-primary btn-sm';
    btn.href = followupUrl(o.slug, { type: o.type, returnTo: o.returnTo });
    btn.textContent = wrong
      ? t('prestudy.result_followup', null, 'Review the words you missed (about 2 min)')
      : t('prestudy.result_produce', null, 'Translate a passage from this test (about 5 min)');
    btn.addEventListener('click', function (ev) {
      if (!o.beforeLeave) return;
      ev.preventDefault();
      btn.classList.add('disabled');
      Promise.resolve()
        .then(o.beforeLeave)
        .catch(function (e) { console.warn('[prestudy] before-leave failed:', e); })
        .then(function () { root.location.href = btn.href; });
    });
    box.appendChild(btn);
    if (o.prestudied) {
      const note = doc.createElement('span');
      note.className = 'small text-muted';
      note.textContent = t('prestudy.result_prestudied', null, 'Prestudied: this attempt counted at half weight.');
      box.appendChild(note);
    }
    container.appendChild(box);
    return box;
  }

  root.LinguaPrestudyLinks = {
    markerKey: markerKey,
    isPrestudied: isPrestudied,
    clearMarker: clearMarker,
    followupUrl: followupUrl,
    setProduceRequest: setProduceRequest,
    takeProduceRequest: takeProduceRequest,
    renderResultActions: renderResultActions,
    WINDOW_MS: WINDOW_MS,
  };
})(typeof window !== 'undefined' ? window : globalThis);
