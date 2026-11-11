/**
 * LinguaDojo Shared Utilities
 * Common functions used across templates - import to avoid duplication.
 */

// =============================================================================
// CONSTANTS
// =============================================================================

// eslint-disable-next-line no-redeclare -- this file defines the window.LINGUADOJO global that consumers read
const LINGUADOJO = window.LINGUADOJO || {};

// Difficulty = the age tiers tests are written for (ADR-003-age-tiers,
// dim_complexity_tiers). A tier's band runs halfway to its neighbours'
// starting ratings (initial_elo 875 / 1175 / 1400 / 1550 / 1700 / 1925), so a
// fresh test of tier N reads as tier N. `label` is the English name and
// `i18n` its translation key; `class` is the badge style.
const ELO_RANGES = {
  T1: { min: 0, max: 1024, label: 'Toddler (4–5)', i18n: 'difficulty.tier1', class: 'badge-tier1' },
  T2: { min: 1025, max: 1287, label: 'Primary school (8–9)', i18n: 'difficulty.tier2', class: 'badge-tier2' },
  T3: { min: 1288, max: 1474, label: 'Young teen (13–14)', i18n: 'difficulty.tier3', class: 'badge-tier3' },
  T4: { min: 1475, max: 1624, label: 'High school (16–17)', i18n: 'difficulty.tier4', class: 'badge-tier4' },
  T5: { min: 1625, max: 1812, label: 'University (19–21)', i18n: 'difficulty.tier5', class: 'badge-tier5' },
  T6: { min: 1813, max: 9999, label: 'Professional (30+)', i18n: 'difficulty.tier6', class: 'badge-tier6' },
};

// Language flag mapping
const LANGUAGE_FLAGS = {
  en: '🇺🇸',
  english: '🇺🇸',
  English: '🇺🇸',
  zh: '🇨🇳',
  chinese: '🇨🇳',
  Chinese: '🇨🇳',
  ja: '🇯🇵',
  japanese: '🇯🇵',
  Japanese: '🇯🇵',
  ko: '🇰🇷',
  korean: '🇰🇷',
  Korean: '🇰🇷',
  fr: '🇫🇷',
  french: '🇫🇷',
  French: '🇫🇷',
};

// Debug mode - set to false in production
const DEBUG = false;

// =============================================================================
// SECURITY
// =============================================================================

/**
 * Escape HTML to prevent XSS attacks.
 *
 * Escapes quotes as well as angle brackets, so the result is safe in BOTH
 * text and quoted-attribute contexts. The previous implementation assigned to
 * `div.textContent` and read back `div.innerHTML`, which does not escape `"`
 * or `'` — safe in a text node, but an attribute-injection hole the moment the
 * result was interpolated into `value="..."`. Quotes render identically in a
 * text node either way, so the stricter version costs nothing.
 *
 * The falsy-input behaviour (`0` and `false` collapse to '') is preserved
 * deliberately — call sites across the app rely on it to blank out empty
 * values, so changing it here is a separate decision from the escaping fix.
 *
 * @param {string} text - Raw text to escape
 * @returns {string} HTML-safe text, usable in text and attribute contexts
 */
const HTML_ESCAPES = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

function escapeHtml(text) {
  if (!text) return '';
  return String(text).replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
}

// =============================================================================
// DIFFICULTY / ELO HELPERS
// =============================================================================

/**
 * The difficulty tier (an ELO_RANGES key, 'T1'..'T6') for an ELO rating.
 * ELO_RANGES is the one difficulty scale: test cards, the Browse filter, the
 * preview page, the test page and the session player all use it.
 * @param {number} elo - ELO rating
 * @returns {string} e.g. 'T2'
 */
function getDifficultyBand(elo) {
  const r = Number(elo);
  for (const [key, band] of Object.entries(ELO_RANGES)) {
    if (r < band.max + 1) return key;
  }
  return 'T6';
}

/**
 * English tier name for an ELO rating, e.g. "Primary school (8–9)".
 * @param {number} elo - ELO rating
 * @returns {string}
 */
function getDifficultyLabel(elo) {
  return ELO_RANGES[getDifficultyBand(elo)].label;
}

/**
 * The tier name shown to the learner, in the UI language.
 * @param {number} elo - ELO rating
 * @returns {string}
 */
function getDifficultyText(elo) {
  const band = ELO_RANGES[getDifficultyBand(elo)];
  const t = window.LinguaI18n && typeof window.LinguaI18n.t === 'function' ? window.LinguaI18n.t(band.i18n) : null;
  return t && t !== band.i18n ? t : band.label;
}

/**
 * Difficulty text for a test in one mode, from the test payload's
 * skill_ratings ({reading: {elo_rating}, ...}); '' when unknown.
 * @param {Object} skillRatings
 * @param {string} mode - 'reading' | 'listening' | 'dictation' | ...
 * @returns {string}
 */
function getTestDifficultyText(skillRatings, mode) {
  const r = skillRatings && skillRatings[mode] && skillRatings[mode].elo_rating;
  return r == null ? '' : getDifficultyText(r);
}

/**
 * Full difficulty info for an ELO rating.
 * @param {number} elo - ELO rating
 * @returns {Object} {band, label (UI language), class, color}
 */
function getDifficultyInfo(elo) {
  const band = getDifficultyBand(elo);
  return {
    band,
    label: getDifficultyText(elo),
    class: ELO_RANGES[band].class,
    color: getDifficultyColor(band),
  };
}

/**
 * Colour for a difficulty tier.
 * @param {string} band - 'T1'..'T6'
 * @returns {string} CSS color
 */
function getDifficultyColor(band) {
  const colors = {
    T1: '#2e7d4f',
    T2: '#3b6ea8',
    T3: '#0e7569',
    T4: '#c28f2c',
    T5: '#e8833a',
    T6: '#c24a3f',
  };
  return colors[band] || '#6b7280';
}

// =============================================================================
// LANGUAGE HELPERS
// =============================================================================

/**
 * Get flag emoji for language
 * @param {string} langCode - Language code or name
 * @returns {string} Flag emoji or default globe
 */
function getLanguageFlag(langCode) {
  return LANGUAGE_FLAGS[langCode] || '🌐';
}

// =============================================================================
// DOM HELPERS
// =============================================================================

/**
 * Show an element by removing d-none class
 * @param {HTMLElement|string} el - Element or selector
 */
function show(el) {
  const element = typeof el === 'string' ? document.querySelector(el) : el;
  element?.classList.remove('d-none');
}

/**
 * Hide an element by adding d-none class
 * @param {HTMLElement|string} el - Element or selector
 */
function hide(el) {
  const element = typeof el === 'string' ? document.querySelector(el) : el;
  element?.classList.add('d-none');
}

/**
 * Toggle element visibility
 * @param {HTMLElement|string} el - Element or selector
 * @param {boolean} visible - Whether to show (true) or hide (false)
 */
function toggle(el, visible) {
  visible ? show(el) : hide(el);
}

// =============================================================================
// API HELPERS
// =============================================================================

/**
 * Get auth headers for API requests
 * @returns {Object} Headers object with Authorization
 */
function getAuthHeaders() {
  const token = localStorage.getItem('jwt_token') || LINGUADOJO.jwt_token;
  return {
    'Content-Type': 'application/json',
    Authorization: token ? `Bearer ${token}` : '',
  };
}

/**
 * Make authenticated API request
 * @param {string} url - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
async function apiRequest(url, options = {}) {
  if (options.body && typeof options.body === 'object') {
    options.body = JSON.stringify(options.body);
  }

  const response = await window.authFetch(url, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || data.message || 'Request failed');
  }

  return data;
}

/**
 * API GET request
 * @param {string} url - API endpoint
 * @returns {Promise<Object>} Response data
 */
function apiGet(url) {
  return apiRequest(url, { method: 'GET' });
}

/**
 * API POST request
 * @param {string} url - API endpoint
 * @param {Object} body - Request body
 * @returns {Promise<Object>} Response data
 */
function apiPost(url, body) {
  return apiRequest(url, { method: 'POST', body });
}

// =============================================================================
// STORAGE HELPERS
// =============================================================================

/**
 * Get item from localStorage with JSON parsing
 * @param {string} key - Storage key
 * @param {*} defaultValue - Default if not found
 * @returns {*} Parsed value or default
 */
function getStorageItem(key, defaultValue = null) {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (e) {
    return defaultValue;
  }
}

/**
 * Set item in localStorage with JSON stringification
 * @param {string} key - Storage key
 * @param {*} value - Value to store
 */
function setStorageItem(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

// =============================================================================
// LOGGING (conditional)
// =============================================================================

/**
 * Debug log - only outputs if DEBUG is true
 * @param  {...any} args - Arguments to log
 */
function debugLog(...args) {
  if (DEBUG) {
    console.log(...args);
  }
}

// =============================================================================
// DATE/TIME HELPERS
// =============================================================================

/**
 * Format seconds to MM:SS
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted time string
 */
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format date to readable string
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatDate(date) {
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// =============================================================================
// LANGUAGE METADATA (native names from dim_languages)
// =============================================================================

/**
 * Cached language metadata from /api/metadata.
 * Provides native_name lookup for language display.
 */
// eslint-disable-next-line no-redeclare -- this file defines the window.LinguaMetadata global that consumers read
const LinguaMetadata = {
  _cache: null,
  _promise: null,

  /**
   * Load metadata from API (cached, single fetch).
   * @returns {Promise<Object>} Metadata response
   */
  load() {
    if (this._cache) return Promise.resolve(this._cache);
    if (this._promise) return this._promise;
    this._promise = fetch('/api/metadata')
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        LinguaMetadata._cache = data;
        return data;
      })
      .catch(function (err) {
        console.error('[LinguaMetadata] Failed to load:', err);
        LinguaMetadata._cache = { languages: [], test_types: [] };
        return LinguaMetadata._cache;
      });
    return this._promise;
  },

  /**
   * Get native name for a language (by English name or code).
   * @param {string} langNameOrCode - e.g. "chinese", "zh", "Chinese"
   * @returns {string} Native name or original input as fallback
   */
  getNativeName(langNameOrCode) {
    if (!this._cache || !langNameOrCode) return langNameOrCode || '';
    const lower = langNameOrCode.toLowerCase();
    const lang = this._cache.languages.find(function (l) {
      return (
        (l.language_name || '').toLowerCase() === lower ||
        (l.language_code || '').toLowerCase() === lower
      );
    });
    return lang && lang.native_name ? lang.native_name : langNameOrCode;
  },

  /**
   * Get native name by language ID.
   * @param {number} langId - Language ID
   * @returns {string} Native name or fallback
   */
  getNativeNameById(langId) {
    if (!this._cache) return '';
    const lang = this._cache.languages.find(function (l) {
      return l.id === langId;
    });
    return lang && lang.native_name ? lang.native_name : '';
  },
};

window.LinguaMetadata = LinguaMetadata;

// =============================================================================
// EXPORTS (for module usage)
// =============================================================================

// Make utilities globally available
window.LinguaUtils = {
  // Constants
  ELO_RANGES,
  LANGUAGE_FLAGS,
  DEBUG,

  // Security
  escapeHtml,

  // Difficulty
  getDifficultyBand,
  getDifficultyLabel,
  getDifficultyText,
  getTestDifficultyText,
  getDifficultyInfo,
  getDifficultyColor,

  // Language
  getLanguageFlag,

  // DOM
  show,
  hide,
  toggle,

  // API
  getAuthHeaders,
  apiRequest,
  apiGet,
  apiPost,

  // Storage
  getStorageItem,
  setStorageItem,

  // Logging
  debugLog,

  // Date/Time
  formatTime,
  formatDate,

  // Language Metadata
  LinguaMetadata,
};
