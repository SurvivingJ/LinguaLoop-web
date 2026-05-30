/**
 * Unit tests for static/js/utils.js
 *
 * All functions are accessed via window.LinguaUtils because utils.js is a
 * browser-global script (not an ES module).  The setup.js file evals it into
 * the jsdom context before these tests run.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Destructure once — window.LinguaUtils is set by setup.js
const getUtils = () => window.LinguaUtils;

// ---------------------------------------------------------------------------
// escapeHtml
// ---------------------------------------------------------------------------

describe('escapeHtml', () => {
  it('returns empty string for falsy inputs', () => {
    const { escapeHtml } = getUtils();
    expect(escapeHtml('')).toBe('');
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml(undefined)).toBe('');
    expect(escapeHtml(0)).toBe('');
  });

  it('leaves plain text unchanged', () => {
    const { escapeHtml } = getUtils();
    expect(escapeHtml('hello world')).toBe('hello world');
  });

  it('escapes < and > characters', () => {
    const { escapeHtml } = getUtils();
    expect(escapeHtml('<script>')).toBe('&lt;script&gt;');
    expect(escapeHtml('</script>')).toBe('&lt;/script&gt;');
  });

  it('escapes & character', () => {
    const { escapeHtml } = getUtils();
    expect(escapeHtml('a & b')).toBe('a &amp; b');
  });

  it('neutralises a classic XSS payload', () => {
    const { escapeHtml } = getUtils();
    const payload = '<img src=x onerror=alert(1)>';
    const escaped = escapeHtml(payload);
    expect(escaped).not.toContain('<img');
    expect(escaped).toContain('&lt;img');
  });

  it('preserves double quotes (text nodes do not need attribute-encoding)', () => {
    const { escapeHtml } = getUtils();
    // The DOM textContent→innerHTML path does not encode " in text nodes —
    // that is correct: double quotes only need escaping inside HTML attributes.
    expect(escapeHtml('"quoted"')).toBe('"quoted"');
  });
});

// ---------------------------------------------------------------------------
// getDifficultyLabel
// ---------------------------------------------------------------------------

describe('getDifficultyLabel', () => {
  it.each([
    [0, 'Beginner'],
    [1199, 'Beginner'],
    [1200, 'Elementary'],
    [1399, 'Elementary'],
    [1400, 'Intermediate'],
    [1599, 'Intermediate'],
    [1600, 'Advanced'],
    [1799, 'Advanced'],
    [1800, 'Expert'],
    [9999, 'Expert'],
  ])('ELO %i → %s', (elo, expected) => {
    expect(getUtils().getDifficultyLabel(elo)).toBe(expected);
  });
});

// ---------------------------------------------------------------------------
// getDifficultyInfo
// ---------------------------------------------------------------------------

describe('getDifficultyInfo', () => {
  it('returns an object with label, class, and color', () => {
    const info = getUtils().getDifficultyInfo(1500);
    expect(info).toMatchObject({
      label: 'Intermediate',
      class: 'badge-intermediate',
    });
    expect(typeof info.color).toBe('string');
    expect(info.color).toMatch(/^#/);
  });

  it('uses correct badge class for each tier', () => {
    const cases = [
      [600, 'badge-beginner'],
      [1300, 'badge-elementary'],
      [1500, 'badge-intermediate'],
      [1700, 'badge-advanced'],
      [2000, 'badge-expert'],
    ];
    for (const [elo, cls] of cases) {
      expect(getUtils().getDifficultyInfo(elo).class).toBe(cls);
    }
  });
});

// ---------------------------------------------------------------------------
// getLanguageFlag
// ---------------------------------------------------------------------------

describe('getLanguageFlag', () => {
  it.each([
    ['zh', '🇨🇳'],
    ['Chinese', '🇨🇳'],
    ['chinese', '🇨🇳'],
    ['ja', '🇯🇵'],
    ['Japanese', '🇯🇵'],
    ['ko', '🇰🇷'],
    ['en', '🇺🇸'],
    ['fr', '🇫🇷'],
  ])('code/name %s → flag %s', (input, flag) => {
    expect(getUtils().getLanguageFlag(input)).toBe(flag);
  });

  it('returns globe emoji for unknown language', () => {
    expect(getUtils().getLanguageFlag('klingon')).toBe('🌐');
    expect(getUtils().getLanguageFlag('')).toBe('🌐');
  });
});

// ---------------------------------------------------------------------------
// formatTime
// ---------------------------------------------------------------------------

describe('formatTime', () => {
  it.each([
    [0, '0:00'],
    [1, '0:01'],
    [59, '0:59'],
    [60, '1:00'],
    [61, '1:01'],
    [3600, '60:00'],
    [3661, '61:01'],
  ])('%i seconds → %s', (secs, expected) => {
    expect(getUtils().formatTime(secs)).toBe(expected);
  });
});

// ---------------------------------------------------------------------------
// formatDate
// ---------------------------------------------------------------------------

describe('formatDate', () => {
  it('formats a date string into a human-readable form', () => {
    const result = getUtils().formatDate('2024-01-15');
    expect(result).toMatch(/2024/);
    expect(result).toMatch(/Jan/);
  });

  it('accepts a Date object', () => {
    const d = new Date('2024-06-01');
    expect(getUtils().formatDate(d)).toMatch(/2024/);
  });
});

// ---------------------------------------------------------------------------
// getStorageItem / setStorageItem
// ---------------------------------------------------------------------------

describe('localStorage helpers', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('setStorageItem serialises and getStorageItem parses', () => {
    const { setStorageItem, getStorageItem } = getUtils();
    setStorageItem('test_key', { name: 'Alice', score: 42 });
    expect(getStorageItem('test_key')).toEqual({ name: 'Alice', score: 42 });
  });

  it('getStorageItem returns defaultValue when key is absent', () => {
    expect(getUtils().getStorageItem('missing_key', 99)).toBe(99);
  });

  it('getStorageItem returns null default when unspecified', () => {
    expect(getUtils().getStorageItem('missing_key')).toBeNull();
  });

  it('getStorageItem returns defaultValue when stored JSON is malformed', () => {
    localStorage.setItem('bad_json', '{{bad}}');
    expect(getUtils().getStorageItem('bad_json', 'fallback')).toBe('fallback');
  });

  it('round-trips arrays', () => {
    const { setStorageItem, getStorageItem } = getUtils();
    setStorageItem('arr', [1, 2, 3]);
    expect(getStorageItem('arr')).toEqual([1, 2, 3]);
  });
});

// ---------------------------------------------------------------------------
// debugLog
// ---------------------------------------------------------------------------

describe('debugLog', () => {
  it('does not call console.log when DEBUG is false (production default)', () => {
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
    getUtils().debugLog('should not appear');
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// show / hide / toggle
// ---------------------------------------------------------------------------

describe('DOM helpers', () => {
  let el;

  beforeEach(() => {
    el = document.createElement('div');
    document.body.appendChild(el);
  });

  afterEach(() => {
    el.remove();
  });

  it('hide adds d-none class', () => {
    getUtils().hide(el);
    expect(el.classList.contains('d-none')).toBe(true);
  });

  it('show removes d-none class', () => {
    el.classList.add('d-none');
    getUtils().show(el);
    expect(el.classList.contains('d-none')).toBe(false);
  });

  it('toggle(el, false) hides, toggle(el, true) shows', () => {
    getUtils().toggle(el, false);
    expect(el.classList.contains('d-none')).toBe(true);
    getUtils().toggle(el, true);
    expect(el.classList.contains('d-none')).toBe(false);
  });

  it('accepts a CSS selector string', () => {
    el.id = 'test-dom-el';
    getUtils().hide('#test-dom-el');
    expect(el.classList.contains('d-none')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// getAuthHeaders
// ---------------------------------------------------------------------------

describe('getAuthHeaders', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns empty Authorization when no token is stored', () => {
    const headers = getUtils().getAuthHeaders();
    expect(headers['Content-Type']).toBe('application/json');
    expect(headers['Authorization']).toBe('');
  });

  it('returns Bearer token when jwt_token is in localStorage', () => {
    localStorage.setItem('jwt_token', 'test.jwt.token');
    const headers = getUtils().getAuthHeaders();
    expect(headers['Authorization']).toBe('Bearer test.jwt.token');
  });
});
