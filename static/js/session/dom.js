// static/js/session/dom.js
// Small helpers shared by the session controller and its players.

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** Escape a value for interpolation into innerHTML or an attribute. */
export function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
}

const fill = (s, params) =>
  params ? String(s).replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m)) : s;

/**
 * Translate `key`. When the bundle has no entry (LinguaI18n.t echoes the key)
 * or i18n is not loaded, the English `fallback` is used with `{name}` params
 * filled in.
 */
export function T(key, params, fallback) {
  const i18n = window.LinguaI18n;
  if (i18n && typeof i18n.t === 'function') {
    const v = i18n.t(key, params);
    if (v && v !== key) return v;
  }
  return fill(fallback || key, params);
}

/** Translate freshly injected data-i18n markup under `root`. */
export function applyI18n(root) {
  const i18n = window.LinguaI18n;
  if (i18n && typeof i18n.applyToDOM === 'function') i18n.applyToDOM(root);
}

/** A language's own name ("日本語"), or its upper-cased code. */
export function nativeName(code) {
  const meta = window.LinguaMetadata;
  return (
    (meta && meta.getNativeName && meta.getNativeName(code)) ||
    (code ? String(code).toUpperCase() : '')
  );
}

/** Shuffled copy (Fisher-Yates). */
export function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** 75 -> "1:15". */
export function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/** 75 -> "01:15" (elapsed-time clocks). */
export function formatClock(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/** Monotonic milliseconds where available. */
export function nowMs() {
  return window.performance && performance.now ? performance.now() : Date.now();
}

/** Toggle a player's #loadingOverlay. */
export function showLoading(container, show) {
  const el = container.querySelector('#loadingOverlay');
  if (el) el.style.display = show ? 'flex' : 'none';
}

/**
 * Show a player's #errorState / #errorMessage and hide the listed sections
 * (ids inside `container`).
 */
export function showError(container, msg, hideIds) {
  const err = container.querySelector('#errorState');
  if (err) {
    err.style.display = 'block';
    const text = container.querySelector('#errorMessage');
    if (text) text.textContent = msg;
  }
  (hideIds || []).forEach((id) => {
    const el = container.querySelector('#' + id);
    if (el) el.style.display = 'none';
  });
}

/** Toast shown when a save could not be persisted. */
export function toastSaveFailed() {
  if (typeof window.showToast === 'function') {
    window.showToast(
      T('session.save_failed', null, 'Couldn’t save your progress — check your connection.')
    );
  }
}
