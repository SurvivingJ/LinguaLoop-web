/**
 * Runs synchronously in <head> on every page (templates/base.html), before
 * first paint: theme, CJK web fonts, i18n preload, and the silent session
 * renewal that must start before any page request is sent.
 *
 * Server data arrives in the <script type="application/json" id="lingua-boot">
 * block that precedes this file.
 */
(function () {
  'use strict';

  let boot = {};
  try {
    const el = document.getElementById('lingua-boot');
    if (el) boot = JSON.parse(el.textContent) || {};
  } catch (e) {
    boot = {};
  }
  window.LINGUA_BOOT = boot;
  window.LINGUA_METADATA = boot.metadata || null;
  window.LINGUA_I18N_VERSIONS = boot.i18nVersions || {};

  function stored(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  // ---- Theme: applied before first paint to avoid a flash of the default.
  const theme = stored('linguadojo-theme');
  if (theme && theme !== 'default') {
    document.documentElement.setAttribute('data-theme', theme);
  }

  // ---- CJK web fonts: only the family for the study / UI language.
  const FAMILY = { zh: 'Noto+Sans+SC:wght@400;500;700', ja: 'Noto+Sans+JP:wght@400;500;700' };
  const LANGS = (boot.metadata && boot.metadata.languages) || [];
  const requested = {};
  function codeForStudyLanguage(id) {
    for (let i = 0; i < LANGS.length; i++) {
      if (String(LANGS[i].id) === String(id)) return LANGS[i].language_code;
    }
    return null;
  }
  function ensureFont(code) {
    if (!code || !FAMILY[code] || requested[code]) return;
    requested[code] = true;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.media = 'print'; // load without blocking rendering ...
    link.onload = function () {
      this.media = 'all'; // ... then apply
    };
    link.href = 'https://fonts.googleapis.com/css2?family=' + FAMILY[code] + '&display=swap';
    document.head.appendChild(link);
  }
  window.LinguaFonts = {
    ensure: ensureFont,
    ensureForStudyLanguage: function (id) {
      ensureFont(codeForStudyLanguage(id));
    },
  };
  ensureFont(codeForStudyLanguage(stored('selectedLanguageId')));
  ensureFont(stored('linguadojo-ui-lang'));

  // ---- i18n preload: base.html preloads en.json (always needed as the
  // fallback); the UI language is only known here. Mirrors detectLanguage()
  // and the URL built in i18n-manager.js.
  const versions = window.LINGUA_I18N_VERSIONS;
  let uiLang = stored('linguadojo-ui-lang');
  if (!uiLang || !versions[uiLang]) uiLang = (navigator.language || '').substring(0, 2);
  if (uiLang !== 'en' && versions[uiLang]) {
    const preload = document.createElement('link');
    preload.rel = 'preload';
    preload.as = 'fetch';
    preload.crossOrigin = 'anonymous';
    preload.href = '/static/i18n/' + uiLang + '.json?v=' + versions[uiLang];
    document.head.appendChild(preload);
  }

  // ---- Session renewal -----------------------------------------------------
  const PUBLIC_PATHS = ['/', '/login', '/signup', '/logout'];
  // One budget for "how long may a silent renewal take": the failsafe below
  // and authFetch (pages/base.js) both use it.
  const RENEWAL_BUDGET_MS = 6000;

  /**
   * Expiry of a JWT in epoch ms; 0 when missing or unparseable, Infinity when
   * the token carries no exp claim.
   */
  function tokenExpiryMs(jwt) {
    if (!jwt) return 0;
    try {
      let b64 = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      // JWT payloads are unpadded base64url; atob() needs the padding back.
      b64 += '==='.slice((b64.length + 3) % 4);
      const claims = JSON.parse(atob(b64));
      if (!claims.exp) return Infinity;
      return claims.exp * 1000;
    } catch (e) {
      return 0;
    }
  }

  function isPublicPath(path) {
    return PUBLIC_PATHS.indexOf(path) !== -1;
  }

  window.LinguaAuthBoot = {
    RENEWAL_BUDGET_MS: RENEWAL_BUDGET_MS,
    tokenExpiryMs: tokenExpiryMs,
    isPublicPath: isPublicPath,
  };

  // When the user lands on a protected page with no usable JWT in storage, try
  // the HttpOnly cookies (/api/auth/refresh-token, then
  // /api/auth/device-restore) BEFORE bouncing to /login: they are invisible to
  // JS, so they must be tried rather than inferred.
  //
  // Only #main-content is hidden, never <body>: the masthead, nav and
  // skip-link stay reachable, and a polite live region announces the status.
  // The failsafe always settles the flow, so nobody is trapped behind hidden
  // content.
  if (isPublicPath(window.location.pathname)) return;

  let token = null;
  try {
    token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
  } catch (e) {
    token = null;
  }
  // A present token with more than 30 s left is good as it is. An expired one
  // is the restart case (localStorage kept it across a browser close): renew
  // now, before a raw (non-authFetch) request 401s.
  if (token && tokenExpiryMs(token) > Date.now() + 30000) return;

  const paintBlock = document.createElement('style');
  paintBlock.id = '__lingua_block_paint';
  paintBlock.textContent = '#main-content{visibility:hidden}';
  document.documentElement.appendChild(paintBlock);

  function setStatus(message) {
    function build() {
      if (!document.body) return;
      let el = document.getElementById('__lingua_auth_status');
      if (!el) {
        el = document.createElement('div');
        el.id = '__lingua_auth_status';
        el.className = 'auth-restore-status';
        el.setAttribute('role', 'status');
        el.setAttribute('aria-live', 'polite');
        document.body.appendChild(el);
      }
      el.textContent = message;
    }
    if (document.body) build();
    else document.addEventListener('DOMContentLoaded', build);
  }

  function revealContent() {
    const paint = document.getElementById('__lingua_block_paint');
    if (paint) paint.remove();
    const status = document.getElementById('__lingua_auth_status');
    if (status) status.remove();
  }

  setStatus('Checking your session…');

  function bounceToLogin() {
    // Protected content stays hidden; the status message is the non-blank
    // fallback while the redirect happens.
    setStatus('Redirecting to login…');
    window.location.href = '/login';
  }

  let settled = false;
  const timeoutId = setTimeout(function () {
    if (!settled) {
      settled = true;
      bounceToLogin();
    }
  }, RENEWAL_BUDGET_MS);

  function storeToken(jwt, user, remembered) {
    if (remembered) {
      // device-restore always lands a remembered device -> localStorage.
      ['jwt_token', 'refresh_token', 'user_data'].forEach(function (k) {
        sessionStorage.removeItem(k);
      });
      localStorage.setItem('jwt_token', jwt);
      if (user) localStorage.setItem('user_data', JSON.stringify(user));
    } else {
      // Plain refresh preserves the existing storage tier.
      const store = sessionStorage.getItem('jwt_token') ? sessionStorage : localStorage;
      store.setItem('jwt_token', jwt);
      if (user) store.setItem('user_data', JSON.stringify(user));
    }
  }
  function succeed() {
    if (settled) return;
    settled = true;
    clearTimeout(timeoutId);
    revealContent();
  }
  function fail() {
    if (settled) return;
    settled = true;
    clearTimeout(timeoutId);
    bounceToLogin();
  }

  // Published so authFetch waits for this renewal instead of firing page
  // requests with the stale token and racing it with refreshes of its own
  // (refresh tokens rotate: parallel refreshes collide). Refresh cookie first
  // (cheap, no trusted-device rotation), device cookie second.
  window.__ldAuthRenewal = fetch('/api/auth/refresh-token', {
    method: 'POST',
    credentials: 'include',
  })
    .then(function (r) {
      return r.ok ? r.json() : null;
    })
    .then(function (data) {
      if (data && data.success && data.jwt_token) {
        // refresh-token returns no user; existing user_data stays put.
        storeToken(data.jwt_token, null, false);
        succeed();
        return true;
      }
      return false;
    })
    .catch(function () {
      return false;
    })
    .then(function (done) {
      if (done || settled) return;
      return fetch('/api/auth/device-restore', {
        method: 'POST',
        credentials: 'same-origin',
      })
        .then(function (r) {
          if (!r.ok) throw new Error('device-restore status ' + r.status);
          return r.json();
        })
        .then(function (data) {
          if (!data || !data.success || !data.jwt_token) {
            throw new Error('device-restore returned no jwt');
          }
          storeToken(data.jwt_token, data.user, true);
          succeed();
        })
        .catch(function () {
          fail();
        });
    });
})();
