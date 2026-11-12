/** static/js/native-language-prompt.js: asks once, skip uses the browser language. */
import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';

beforeAll(async () => {
  await import('../../static/js/native-language-prompt.js');
});

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe('browserLanguageId', () => {
  const f = () => window.LinguaNativePrompt.browserLanguageId;
  it('takes the first supported browser language', () => {
    expect(f()(['fr-FR', 'ja-JP', 'en-US'])).toBe(3);
    expect(f()(['zh-CN'])).toBe(1);
    expect(f()(['en-GB'])).toBe(2);
  });
  it('falls back to English', () => {
    expect(f()(['fr-FR', 'de'])).toBe(2);
    expect(f()([])).toBe(2);
  });
});

describe('maybePrompt', () => {
  it('does nothing without a session', async () => {
    window.authFetch = vi.fn();
    expect(await window.LinguaNativePrompt.maybePrompt()).toBe(false);
    expect(window.authFetch).not.toHaveBeenCalled();
  });

  it('does not ask a learner who already has a native language, and remembers', async () => {
    localStorage.setItem('jwt_token', 't');
    window.authFetch = vi.fn(async () => ({ ok: true, json: async () => ({ data: { native_language_id: 2 } }) }));
    expect(await window.LinguaNativePrompt.maybePrompt()).toBe(false);
    expect(await window.LinguaNativePrompt.maybePrompt()).toBe(false);
    expect(window.authFetch).toHaveBeenCalledTimes(1);
  });

  it('asks when none is set', async () => {
    localStorage.setItem('jwt_token', 't');
    window.authFetch = vi.fn(async () => ({ ok: true, json: async () => ({ native_language_id: null }) }));
    expect(await window.LinguaNativePrompt.maybePrompt()).toBe(true);
  });
});
