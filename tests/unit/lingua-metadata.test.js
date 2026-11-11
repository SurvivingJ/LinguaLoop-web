/**
 * static/js/utils.js — LinguaMetadata.load() is pages' "ready to render" gate.
 * The metadata is embedded in the page (latency 2026-11), so load() must also
 * wait for the UI translations; otherwise a page renders raw i18n keys
 * ("test.level") — the regression the 2026-11-11 walkthrough caught on the
 * preview -> test hand-off.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const META = { languages: [{ id: 3, language_code: 'ja' }], test_types: [], status: 'success' };

function reset() {
  window.LinguaMetadata._cache = null;
  window.LinguaMetadata._promise = null;
}

describe('LinguaMetadata.load', () => {
  beforeEach(() => {
    reset();
    window.LINGUA_METADATA = META;
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    delete window.LINGUA_METADATA;
    delete window.LinguaI18n;
    reset();
  });

  it('uses the embedded metadata synchronously (no fetch)', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    window.LinguaMetadata.load();
    expect(window.LinguaMetadata._cache).toBe(META);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it('does not resolve before translations are loaded', async () => {
    let finishI18n;
    window.LinguaI18n = { init: () => new Promise((r) => { finishI18n = r; }) };
    let resolved = false;
    window.LinguaMetadata.load().then(() => { resolved = true; });
    await vi.advanceTimersByTimeAsync(100);
    expect(resolved).toBe(false);
    finishI18n();
    await vi.advanceTimersByTimeAsync(0);
    expect(resolved).toBe(true);
  });

  it('never waits more than 4 s for translations', async () => {
    window.LinguaI18n = { init: () => new Promise(() => {}) };
    let value = null;
    window.LinguaMetadata.load().then((m) => { value = m; });
    await vi.advanceTimersByTimeAsync(3900);
    expect(value).toBeNull();
    await vi.advanceTimersByTimeAsync(200);
    expect(value).toBe(META);
  });

  it('a translation failure does not block the page', async () => {
    window.LinguaI18n = { init: () => Promise.reject(new Error('offline')) };
    await expect(window.LinguaMetadata.load()).resolves.toBe(META);
  });
});
