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
  const PRODUCE_OK_PREFIX = 'prestudy_produce_ok:';
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
    try {
      s = decodeURIComponent(s);
    } catch {
      /* keep raw */
    }
    return MARKER_PREFIX + s;
  }

  function readJson(key) {
    try {
      return JSON.parse(root.sessionStorage.getItem(key) || 'null');
    } catch {
      return null;
    }
  }

  function isPrestudied(slug, now) {
    const m = readJson(markerKey(slug));
    return !!(m && m.at && (now || Date.now()) - m.at < WINDOW_MS);
  }

  function clearMarker(slug) {
    try {
      root.sessionStorage.removeItem(markerKey(slug));
    } catch {
      /* storage blocked */
    }
  }

  function followupUrl(slug, opts) {
    const o = opts || {};
    const p = new URLSearchParams({
      mode: 'followup',
      type: o.type === 'listening' ? 'listening' : 'reading',
    });
    if (o.returnTo) p.set('return', o.returnTo);
    return '/test/' + encodeURIComponent(slug) + '/prestudy?' + p.toString();
  }

  // A Produce request the next daily-session translation slot should honour.
  function setProduceRequest(slug, testId) {
    try {
      root.sessionStorage.setItem(
        PRODUCE_KEY,
        JSON.stringify({ slug: String(slug), test_id: testId || null, at: Date.now() })
      );
    } catch {
      /* storage blocked */
    }
  }

  function takeProduceRequest(now) {
    const r = readJson(PRODUCE_KEY);
    try {
      root.sessionStorage.removeItem(PRODUCE_KEY);
    } catch {
      /* storage blocked */
    }
    return r && r.slug && r.at && (now || Date.now()) - r.at < WINDOW_MS ? r : null;
  }

  // Whether Produce can open a passage on this test (the prestudy payload's
  // produce_available), left by the prestudy page for the result screen. Kept
  // apart from the prestudied marker, which is cleared on submit.
  function setProduceAvailable(slug, ok) {
    try {
      root.sessionStorage.setItem(
        PRODUCE_OK_PREFIX + markerKey(slug).slice(MARKER_PREFIX.length),
        JSON.stringify({ ok: !!ok, at: Date.now() })
      );
    } catch {
      /* storage blocked: the result screen asks the server */
    }
  }

  // true / false when the prestudy page left an answer in the last 6 hours, else null.
  function knownProduceAvailable(slug, now) {
    const r = readJson(PRODUCE_OK_PREFIX + markerKey(slug).slice(MARKER_PREFIX.length));
    return r && r.at && (now || Date.now()) - r.at < WINDOW_MS ? !!r.ok : null;
  }

  // Same rule as POST .../prestudy/produce (services/prestudy.produce_available).
  function fetchProduceAvailable(slug) {
    if (typeof root.authFetch !== 'function') return Promise.resolve(false);
    return root
      .authFetch('/api/tests/' + encodeURIComponent(slug) + '/prestudy/produce-available')
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .then(function (j) {
        const d = (j && j.data) || j || {};
        return d.produce_available === true;
      })
      .catch(function () {
        return false;
      });
  }

  /**
   * Add the post-test action under a result banner.
   *   container  element to append to
   *   o.slug, o.type ('reading'|'listening'), o.wrong (number of wrong answers),
   *   o.prestudied (bool), o.returnTo ('session' or undefined),
   *   o.produceAvailable (bool, optional): whether Produce can run on this test.
   *     With no wrong answers the only offer is Produce, so it is shown only
   *     when this is true. When the caller does not pass it, the answer the
   *     prestudy page left is used, else the server is asked once
   *     (GET .../prestudy/produce-available) and the offer appears when it says yes.
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
    container.appendChild(box);
    if (o.prestudied) {
      const note = doc.createElement('span');
      note.className = 'small text-muted';
      note.textContent = t(
        'prestudy.result_prestudied',
        null,
        'Prestudied: this attempt counted at half weight.'
      );
      box.appendChild(note);
    }
    if (wrong) {
      // the follow-up page itself ends without Produce when there is none
      box.insertBefore(actionButton(doc, o, wrong), box.firstChild);
      return box;
    }
    const known =
      typeof o.produceAvailable === 'boolean' ? o.produceAvailable : knownProduceAvailable(o.slug);
    const add = function (ok) {
      if (ok && box.isConnected !== false)
        box.insertBefore(actionButton(doc, o, 0), box.firstChild);
    };
    if (known !== null) add(known);
    else box.ready = fetchProduceAvailable(o.slug).then(add);
    return box;
  }

  function actionButton(doc, o, wrong) {
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
        .catch(function (e) {
          console.warn('[prestudy] before-leave failed:', e);
        })
        .then(function () {
          root.location.href = btn.href;
        });
    });
    return btn;
  }

  root.LinguaPrestudyLinks = {
    markerKey: markerKey,
    isPrestudied: isPrestudied,
    clearMarker: clearMarker,
    followupUrl: followupUrl,
    setProduceRequest: setProduceRequest,
    takeProduceRequest: takeProduceRequest,
    renderResultActions: renderResultActions,
    setProduceAvailable: setProduceAvailable,
    knownProduceAvailable: knownProduceAvailable,
    WINDOW_MS: WINDOW_MS,
  };
})(typeof window !== 'undefined' ? window : globalThis);
