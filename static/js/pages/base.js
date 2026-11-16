// -------------------------------------------------------------------
// Token storage: remembered devices use localStorage (survives browser
// restarts); unremembered devices use sessionStorage (cleared on tab
// close).
//
// Many existing templates read `localStorage.getItem('jwt_token')`
// directly. To avoid touching every call site, we install a narrow
// shim that makes those three auth keys fall back to sessionStorage
// when not present in localStorage. New code should use `_getStored`.
// -------------------------------------------------------------------
(function installAuthStorageShim() {
  const FALLBACK_KEYS = new Set(['jwt_token', 'refresh_token', 'user_data']);
  const origLocalGetItem = localStorage.getItem.bind(localStorage);
  const origSessionGetItem = sessionStorage.getItem.bind(sessionStorage);
  // Override only on the localStorage instance — sessionStorage is left alone.
  localStorage.getItem = function (key) {
    const v = origLocalGetItem(key);
    if (v !== null) return v;
    if (FALLBACK_KEYS.has(key)) return origSessionGetItem(key);
    return null;
  };
})();

function _tokenStore() {
  return sessionStorage.getItem('jwt_token') ? sessionStorage : localStorage;
}
function _getStored(key) {
  return sessionStorage.getItem(key) || localStorage.getItem(key);
}
function _clearAllTokens() {
  ['jwt_token', 'refresh_token', 'user_data'].forEach((k) => {
    sessionStorage.removeItem(k);
    localStorage.removeItem(k);
  });
}

// Global configuration - accessible from all pages
function _parseUserData() {
  try {
    return JSON.parse(_getStored('user_data') || '{}');
  } catch (e) {
    // Corrupt storage shouldn't permanently break page load —
    // drop the bad value and return an empty object.
    try {
      localStorage.removeItem('user_data');
    } catch (_) {}
    try {
      sessionStorage.removeItem('user_data');
    } catch (_) {}
    return {};
  }
}
window.LINGUADOJO = {
  API_BASE: (window.LINGUA_BOOT && window.LINGUA_BOOT.apiBase) || '/',
  JWT_TOKEN: _getStored('jwt_token'),
  USER_DATA: _parseUserData(),
};

/**
 * Ask the server to silently re-authenticate this browser via the
 * trusted-device cookie. Returns true on success and writes the new
 * access token to localStorage. Used as the last resort before
 * bouncing the user to /login.
 */
async function _tryDeviceRestore() {
  try {
    const r = await fetch('/api/auth/device-restore', {
      method: 'POST',
      credentials: 'same-origin',
    });
    if (!r.ok) return false;
    const data = await r.json();
    if (!data.success || !data.jwt_token) return false;
    // device-restore always lands the user on a remembered device,
    // so write to localStorage and wipe sessionStorage.
    ['jwt_token', 'refresh_token', 'user_data'].forEach((k) => sessionStorage.removeItem(k));
    localStorage.setItem('jwt_token', data.jwt_token);
    // Refresh token is an HttpOnly cookie, not JS-readable storage.
    if (data.user) localStorage.setItem('user_data', JSON.stringify(data.user));
    window.LINGUADOJO.JWT_TOKEN = data.jwt_token;
    return true;
  } catch (e) {
    console.error('device-restore error:', e);
    return false;
  }
}

/**
 * Authenticated fetch wrapper with automatic token refresh.
 * On 401: try the Supabase refresh token first; if that fails, try
 * the trusted-device cookie; only then bounce to /login.
 */
// One token renewal at a time, shared by every request that hit 401.
// Refresh tokens rotate on use, so N parallel refreshes would race each
// other (and cost N round trips). Resolves to the new JWT or null.
let _renewalInFlight = null;
function _renewTokenOnce() {
  if (_renewalInFlight) return _renewalInFlight;
  _renewalInFlight = (async () => {
    // ---- Step 1: try the HttpOnly refresh cookie --------------
    // The refresh token is never in JS storage; it rides as an
    // HttpOnly cookie. credentials:'include' sends it; the server
    // rotates it and returns only the new access token in the body.
    try {
      const refreshResponse = await fetch('/api/auth/refresh-token', {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        if (data && data.jwt_token) {
          const store = _tokenStore();
          store.setItem('jwt_token', data.jwt_token);
          window.LINGUADOJO.JWT_TOKEN = data.jwt_token;
          return data.jwt_token;
        }
      }
    } catch (e) {
      console.error('refresh-token error:', e);
    }
    // ---- Step 2: try the trusted-device cookie ----------------
    if (await _tryDeviceRestore()) return window.LINGUADOJO.JWT_TOKEN;
    return null;
  })();
  _renewalInFlight.finally(() => {
    _renewalInFlight = null;
  });
  return _renewalInFlight;
}

// Same budget as the head script's failsafe (pages/base-head.js).
const _authBoot = window.LinguaAuthBoot || {};
const RENEWAL_BUDGET_MS = _authBoot.RENEWAL_BUDGET_MS || 6000;

// Proactive renewal: refresh shortly before the access token's `exp`, so an
// expiry mid-page does not cost a 401 + refresh + retry on the next request.
const RENEWAL_LEAD_MS = 60000;
let _proactiveTimer = null;
function _scheduleProactiveRenewal() {
  clearTimeout(_proactiveTimer);
  _proactiveTimer = null;
  if (typeof _authBoot.tokenExpiryMs !== 'function') return;
  if (_authBoot.isPublicPath(window.location.pathname)) return;
  const expiry = _authBoot.tokenExpiryMs(_getStored('jwt_token'));
  if (!expiry || expiry === Infinity) return;
  // setTimeout delays are 32-bit; a longer wait just re-arms.
  const delay = Math.min(Math.max(expiry - RENEWAL_LEAD_MS - Date.now(), 0), 0x7fffffff);
  _proactiveTimer = setTimeout(_proactiveRenewal, delay);
}
async function _proactiveRenewal() {
  _proactiveTimer = null;
  // The head script may be renewing already (page opened with a stale token).
  if (window.__ldAuthRenewal) await window.__ldAuthRenewal.catch(() => {});
  const expiry = _authBoot.tokenExpiryMs(_getStored('jwt_token'));
  if (!expiry) return;
  if (expiry - Date.now() > RENEWAL_LEAD_MS) {
    // Renewed elsewhere (head script, a 401 path, another tab), or re-armed.
    _scheduleProactiveRenewal();
    return;
  }
  const fresh = await _renewTokenOnce();
  // Re-arm only for a token that outlives the lead, so a failed renewal or
  // a very short-lived token cannot spin; authFetch's 401 path still covers it.
  if (fresh && _authBoot.tokenExpiryMs(fresh) - Date.now() > RENEWAL_LEAD_MS) {
    _scheduleProactiveRenewal();
  }
}
_scheduleProactiveRenewal();
// Timers are throttled or suspended in background tabs and across sleep.
document.addEventListener('visibilitychange', function () {
  if (document.visibilityState === 'visible') _scheduleProactiveRenewal();
});

/**
 * Authenticated fetch wrapper with automatic token refresh.
 * On 401: try the Supabase refresh token first; if that fails, try
 * the trusted-device cookie; only then bounce to /login.
 */
window.authFetch = async function (url, options = {}) {
  // The head script may be renewing an expired token right now:
  // wait for it (bounded) rather than send a request bound to 401.
  if (window.__ldAuthRenewal) {
    await Promise.race([
      window.__ldAuthRenewal.catch(() => {}),
      new Promise((r) => setTimeout(r, RENEWAL_BUDGET_MS)),
    ]);
  }
  const token = _getStored('jwt_token');

  options.headers = {
    'Content-Type': 'application/json',
    ...options.headers,
    Authorization: `Bearer ${token}`,
  };

  let response = await fetch(url, options);
  if (response.status !== 401) return response;

  // Another request may already have renewed the token while this
  // one was in flight: retry with it before renewing again.
  const current = _getStored('jwt_token');
  if (current && current !== token) {
    options.headers['Authorization'] = `Bearer ${current}`;
    response = await fetch(url, options);
    if (response.status !== 401) return response;
  }

  const fresh = await _renewTokenOnce();
  if (fresh) {
    options.headers['Authorization'] = `Bearer ${fresh}`;
    return await fetch(url, options);
  }

  // ---- Step 3: give up; send the user to /login -----------------
  _clearAllTokens();
  window.location.href = '/login';
  return response;
};

/**
 * Minimal non-blocking toast (no Bootstrap JS dependency).
 * window.showToast(message, type) — type: 'error' (default) | 'success' | 'info'.
 * Auto-dismisses after ~4s. Used to surface silent save failures (M2).
 * Styled by .ld-toasts / .ld-toast in styles.css (theme tokens): bottom
 * centre, above the tab bar or the task dock.
 */
window.showToast = function (message, type = 'error') {
  let container = document.getElementById('lingua-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'lingua-toast-container';
    container.className = 'ld-toasts';
    document.body.appendChild(container);
  }
  const kind = type === 'success' || type === 'info' ? type : 'error';
  const toast = document.createElement('div');
  toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');
  toast.className = 'ld-toast ld-toast--' + kind;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(function () {
    toast.classList.add('is-shown');
  });
  setTimeout(function () {
    toast.classList.remove('is-shown');
    setTimeout(function () {
      toast.remove();
    }, 250);
  }, 4000);
};

/**
 * App shell controls (templates/base.html). Documented in the redesign
 * hand-off (FOUNDATION.md).
 *
 *   LinguaShell.setTaskMode(on)        switch the one-task layout on/off at
 *                                      runtime (no tab bar, Back-pill header,
 *                                      body exactly one viewport tall)
 *   LinguaShell.isTaskMode()
 *   LinguaShell.setTaskHeader({ title, subtitle, glyph, end, backHref, backLabel })
 *                                      fill the task header; omitted keys
 *                                      keep their value, '' clears. Text only.
 *   LinguaShell.onBack(fn)             fn(event) runs when the Back pill is
 *                                      pressed; return true to say "handled"
 *                                      (navigation is then cancelled). Returns
 *                                      an unsubscribe function.
 */
(function setupShell() {
  const backHandlers = [];

  function el(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    const node = el(id);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  }

  window.LinguaShell = {
    setTaskMode: function (on) {
      on = !!on;
      document.body.classList.toggle('ld-task', on);
      document.body.classList.toggle('ld-has-tabs', !on && !!el('ldTabbar'));
      // <main> swaps its page classes (e.g. "container py-4") for the task
      // layout's, and gets them back when task mode ends.
      const main = el('main-content');
      if (!main) return;
      if (on && !main.classList.contains('ld-main--task')) {
        main.dataset.ldPageClass = main.className;
        main.className = 'ld-main ld-main--task';
      } else if (!on && main.dataset.ldPageClass !== undefined) {
        main.className = main.dataset.ldPageClass;
        delete main.dataset.ldPageClass;
      }
    },
    isTaskMode: function () {
      return document.body.classList.contains('ld-task');
    },
    setTaskHeader: function (opts) {
      const o = opts || {};
      setText('ldTaskTitle', o.title);
      setText('ldTaskSubtitle', o.subtitle);
      setText('ldTaskGlyph', o.glyph);
      setText('ldTaskEnd', o.end);
      const back = el('ldBack');
      if (back && o.backHref) back.setAttribute('href', o.backHref);
      if (back && o.backLabel) {
        const label = back.querySelector('[data-i18n]') || back.lastElementChild;
        if (label) {
          label.removeAttribute('data-i18n');
          label.textContent = o.backLabel;
        }
      }
    },
    onBack: function (fn) {
      backHandlers.push(fn);
      return function () {
        const i = backHandlers.indexOf(fn);
        if (i !== -1) backHandlers.splice(i, 1);
      };
    },
  };

  document.addEventListener('click', function (e) {
    const back = e.target.closest && e.target.closest('#ldBack');
    if (!back) return;
    for (let i = backHandlers.length - 1; i >= 0; i--) {
      let handled = false;
      try {
        handled = backHandlers[i](e) === true;
      } catch (err) {
        console.error('[shell] back handler failed', err);
      }
      if (handled) {
        e.preventDefault();
        return;
      }
    }
    // data-ld-back="history": go back when the previous page is ours.
    if (document.body.dataset.ldBack === 'history' && window.history.length > 1) {
      let sameOrigin = false;
      try {
        sameOrigin = !!document.referrer && new URL(document.referrer).origin === location.origin;
      } catch {
        sameOrigin = false;
      }
      if (sameOrigin) {
        e.preventDefault();
        window.history.back();
      }
    }
  });

  // iOS Safari keeps 100dvh when the on-screen keyboard opens, which would
  // push a task page's dock under the keyboard. While the keyboard is up,
  // size the task shell to the visual viewport instead (--ld-vvh).
  const vv = window.visualViewport;
  if (vv && typeof vv.addEventListener === 'function') {
    const sync = function () {
      const keyboard = window.innerHeight - vv.height > 120;
      if (keyboard) document.documentElement.style.setProperty('--ld-vvh', vv.height + 'px');
      else document.documentElement.style.removeProperty('--ld-vvh');
    };
    vv.addEventListener('resize', sync);
  }
})();

const _FLAGS = {
  en: '🇺🇸',
  zh: '🇨🇳',
  cn: '🇨🇳',
  ja: '🇯🇵',
  jp: '🇯🇵',
  ko: '🇰🇷',
  fr: '🇫🇷',
  es: '🇪🇸',
  English: '🇺🇸',
  Chinese: '🇨🇳',
  Japanese: '🇯🇵',
  Korean: '🇰🇷',
  French: '🇫🇷',
};

function _showLanguageIndicator(lang) {
  const indicator = document.getElementById('navLanguageIndicator');
  const flag = document.getElementById('navLanguageFlag');
  const name = document.getElementById('navLanguageName');
  if (!lang || !lang.name || !indicator || !flag || !name) return;
  flag.textContent = _FLAGS[lang.code] || _FLAGS[lang.name] || '🌐';
  name.textContent = lang.name;
  indicator.style.display = 'flex';
  document.body.classList.add('ld-has-lang');
}

/**
 * The study language in the app bar (a link to language selection). Reads the
 * legacy `selectedLanguage` JSON when present, else resolves
 * `selectedLanguageId` through the language metadata.
 */
function updateLanguageIndicator() {
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem('selectedLanguage') || 'null');
  } catch {
    saved = null;
  }
  if (saved && saved.name) {
    _showLanguageIndicator(saved);
    return;
  }
  const languageId = parseInt(localStorage.getItem('selectedLanguageId'), 10);
  if (!languageId || !window.LinguaMetadata) return;
  window.LinguaMetadata.load().then(function (meta) {
    const row = ((meta && meta.languages) || []).find(function (l) {
      return l.id === languageId;
    });
    if (row) _showLanguageIndicator({ code: row.language_code, name: row.language_name });
  });
}

/**
 * Show/hide language-specific nav items (Measure Words / Counters)
 * based on the study language chosen on the language-selection page.
 * Elements are marked up with class="lang-gate" data-lang-gate="<code>"
 * and start hidden (d-none) so there's no flash of an irrelevant tool
 * before metadata resolves the id -> language_code.
 */
function applyLanguageGating() {
  const gated = document.querySelectorAll('.lang-gate');
  if (!gated.length) return;

  const languageId = parseInt(localStorage.getItem('selectedLanguageId'), 10);
  if (!languageId) return; // no language selected yet — stay hidden

  LinguaMetadata.load().then(function (meta) {
    const lang = ((meta && meta.languages) || []).find(function (l) {
      return l.id === languageId;
    });
    const code = lang && lang.language_code;
    if (!code) return;

    gated.forEach(function (el) {
      el.classList.toggle('d-none', el.dataset.langGate !== code);
    });
  });
}

document.addEventListener('DOMContentLoaded', function () {
  updateLanguageIndicator();
  applyLanguageGating();

  // Logout: the app bar's #logout-btn and any [data-ld-logout] (the Me page).
  async function logout(e) {
    e.preventDefault();
    // Best-effort server logout so the trusted-device row is
    // revoked and the cookie cleared. We don't block redirect
    // on failure — local state still gets wiped either way.
    const token = _getStored('jwt_token');
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        /* ignore */
      }
    }
    _clearAllTokens();
    window.location.href = '/login';
  }
  document.addEventListener('click', function (e) {
    const btn = e.target.closest && e.target.closest('#logout-btn, [data-ld-logout]');
    if (btn) logout(e);
  });

  // Report submission
  const submitReportBtn = document.getElementById('submitReportBtn');
  if (submitReportBtn) {
    submitReportBtn.addEventListener('click', async function () {
      const btn = this;
      const form = document.getElementById('reportForm');
      const category = document.getElementById('reportCategory').value;
      const description = document.getElementById('reportDescription').value.trim();

      if (!category || description.length < 10) {
        form.reportValidity();
        return;
      }

      btn.disabled = true;
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1"></span>' +
        LinguaI18n.t('report.submitting');
      document.getElementById('reportError').classList.add('d-none');

      try {
        const token = _getStored('jwt_token');
        if (!token) throw new Error('Please log in');

        const res = await fetch('/api/reports/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            report_category: category,
            description: description,
            current_page: window.location.pathname,
            test_id: window.location.pathname.match(/\/test\/([^/]+)/)?.[1] || null,
            user_agent: navigator.userAgent,
            screen_resolution: `${screen.width}x${screen.height}`,
          }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Submission failed');

        document.getElementById('reportForm').classList.add('d-none');
        document.getElementById('reportFooter').classList.add('d-none');
        document.getElementById('reportSuccess').classList.remove('d-none');
        setTimeout(
          () => bootstrap.Modal.getInstance(document.getElementById('reportModal')).hide(),
          1500
        );
      } catch (e) {
        document.getElementById('reportError').textContent = e.message;
        document.getElementById('reportError').classList.remove('d-none');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>' + LinguaI18n.t('report.submit');
      }
    });
  }

  // Reset modal on close
  const reportModal = document.getElementById('reportModal');
  if (reportModal) {
    reportModal.addEventListener('hidden.bs.modal', function () {
      document.getElementById('reportForm').reset();
      document.getElementById('reportForm').classList.remove('d-none');
      document.getElementById('reportFooter').classList.remove('d-none');
      document.getElementById('reportSuccess').classList.add('d-none');
      document.getElementById('reportError').classList.add('d-none');
      const btn = document.getElementById('submitReportBtn');
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>' + LinguaI18n.t('report.submit');
    });
  }
});
