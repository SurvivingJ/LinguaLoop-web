/*
 * One-time "Which language do you read best?" prompt (2026-11-11).
 *
 * Word explanations use users.native_language_id. A learner who never set it
 * used to get every explanation in the language being learned; the server now
 * defaults to English (services/vocabulary/gloss_lookup.py), and this asks
 * once. Choosing saves that language; skipping or closing saves the browser's
 * language when it is a supported one, else English, so the prompt never
 * comes back. Loaded by base.html on app pages (not login / onboarding).
 */
(function () {
  'use strict';

  // users.native_language_id values (dim_languages): zh 1, en 2, ja 3.
  const SUPPORTED = { zh: 1, en: 2, ja: 3 };
  const DONE_KEY = 'nativeLanguagePromptDone';

  function browserLanguageId(languages) {
    const list = languages || [];
    for (let i = 0; i < list.length; i++) {
      const code = String(list[i] || '').toLowerCase().split('-')[0];
      if (SUPPORTED[code]) return SUPPORTED[code];
    }
    return SUPPORTED.en;
  }

  function markDone() {
    try {
      localStorage.setItem(DONE_KEY, '1');
    } catch {
      /* storage blocked: the server-side value still stops the prompt */
    }
  }

  function isDone() {
    try {
      return localStorage.getItem(DONE_KEY) === '1';
    } catch {
      return false;
    }
  }

  function hasToken() {
    try {
      return !!(localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token'));
    } catch {
      return false;
    }
  }

  function save(languageId) {
    markDone();
    return window
      .authFetch('/api/users/native-language', {
        method: 'PATCH',
        body: JSON.stringify({ language_id: languageId }),
      })
      .catch(function () {});
  }

  function show() {
    const el = document.getElementById('nativeLanguageModal');
    if (!el || !window.bootstrap || !window.bootstrap.Modal) return;
    let chosen = false;
    const modal = window.bootstrap.Modal.getOrCreateInstance(el);
    el.querySelectorAll('[data-native-lang]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        chosen = true;
        save(parseInt(btn.getAttribute('data-native-lang'), 10));
        modal.hide();
      });
    });
    el.addEventListener('hidden.bs.modal', function () {
      // Skip, the close button or the backdrop: use the browser's language.
      if (!chosen) save(browserLanguageId(navigator.languages || [navigator.language]));
    });
    modal.show();
  }

  function maybePrompt() {
    if (isDone() || !hasToken() || typeof window.authFetch !== 'function') return Promise.resolve(false);
    return window
      .authFetch('/api/users/native-language')
      .then(function (res) {
        return res && res.ok ? res.json() : null;
      })
      .then(function (body) {
        if (!body) return false;
        const data = body.data || body;
        if (data.native_language_id) {
          markDone();
          return false;
        }
        show();
        return true;
      })
      .catch(function () {
        return false;
      });
  }

  window.LinguaNativePrompt = { browserLanguageId: browserLanguageId, maybePrompt: maybePrompt };
  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(maybePrompt, 1200);
  });
})();
