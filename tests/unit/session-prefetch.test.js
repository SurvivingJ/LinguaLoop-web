/**
 * The per-player `prefetch` hook (static/js/session/player_registry.js,
 * prefetch.js) and the hooks of the players that define one.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const flashMount = vi.fn(() => ({ destroy() {} }));
const flashPrefetch = vi.fn();
vi.mock('../../static/js/session/players/flashcards.js', () => ({
  mount: flashMount,
  prefetch: flashPrefetch,
}));
vi.mock('../../static/js/session/players/prestudy.js', () => ({
  mount: vi.fn(() => ({ destroy() {} })),
  prefetch: undefined,
}));

const { prefetchItem } = await import('../../static/js/session/player_registry.js');
const { prefetchJson, takePrefetch, warmAudio, adoptAudio } = await import(
  '../../static/js/session/prefetch.js'
);
const practice = await import('../../static/js/session/players/practice.js');
const speedRound = await import('../../static/js/session/players/speed_round.js');
const dictation = await import('../../static/js/session/players/dictation.js');
const readingListening = await import('../../static/js/session/players/reading_listening.js');

const flush = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  flashPrefetch.mockReset();
  flashMount.mockClear();
});

afterEach(() => {
  delete window.authFetch;
  vi.restoreAllMocks();
});

describe('prefetchItem', () => {
  it("calls the player's hook with the item and context, and stores the result", async () => {
    const pending = Promise.resolve({ ok: true, data: {} });
    flashPrefetch.mockReturnValue(pending);
    const item = { kind: 'flashcards', id: 'fc_0' };
    const current = { kind: 'test', test_type: 'reading' };
    const mod = await prefetchItem(item, { languageId: 2, current });
    expect(flashPrefetch).toHaveBeenCalledWith(item, { languageId: 2, current });
    expect(item.prefetch).toBe(pending);
    expect(mod.mount).toBe(flashMount);
    expect(flashMount).not.toHaveBeenCalled();
  });

  it('asks at most once per item', async () => {
    flashPrefetch.mockReturnValue(Promise.resolve({ ok: true }));
    const item = { kind: 'flashcards', id: 'fc_0' };
    await prefetchItem(item, { languageId: 2 });
    delete item.prefetch; // the player took it
    await prefetchItem(item, { languageId: 2 });
    expect(flashPrefetch).toHaveBeenCalledTimes(1);
    expect('prefetch' in item).toBe(false);
  });

  it('stores nothing when the hook declines', async () => {
    flashPrefetch.mockReturnValue(null);
    const item = { kind: 'flashcards', id: 'fc_0' };
    await prefetchItem(item, {});
    expect('prefetch' in item).toBe(false);
  });

  it('survives a hook that throws', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    flashPrefetch.mockImplementation(() => {
      throw new Error('boom');
    });
    const item = { kind: 'flashcards', id: 'fc_0' };
    await expect(prefetchItem(item, {})).resolves.toBeTruthy();
    expect('prefetch' in item).toBe(false);
  });

  it('skips completed items, unknown kinds and players without a hook', async () => {
    expect(await prefetchItem({ kind: 'flashcards', is_completed: true }, {})).toBeNull();
    expect(flashPrefetch).not.toHaveBeenCalled();
    expect(await prefetchItem({ kind: 'test', test_type: 'not_a_real_type' }, {})).toBeNull();
    const item = { kind: 'prestudy', id: 'p' };
    await prefetchItem(item, {});
    expect('prefetch' in item).toBe(false);
  });
});

describe('prefetch helpers', () => {
  it('prefetchJson resolves { ok, data } and never rejects', async () => {
    window.authFetch = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ a: 1 }) }));
    expect(await prefetchJson('/x')).toEqual({ ok: true, status: 200, data: { a: 1 } });
    window.authFetch = vi.fn(async () => ({ ok: false, status: 500 }));
    expect((await prefetchJson('/x')).ok).toBe(false);
    window.authFetch = vi.fn(async () => {
      throw new Error('offline');
    });
    expect((await prefetchJson('/x')).ok).toBe(false);
  });

  it('takePrefetch hands the result over once, and null when unusable', async () => {
    const item = { prefetch: Promise.resolve({ ok: true, data: 1 }) };
    expect(await takePrefetch(item)).toEqual({ ok: true, data: 1 });
    expect('prefetch' in item).toBe(false);
    expect(await takePrefetch(item)).toBeNull();
    expect(await takePrefetch({ prefetch: Promise.resolve({ ok: false }) })).toBeNull();
    expect(await takePrefetch({ prefetch: Promise.reject(new Error('x')) })).toBeNull();
    expect(await takePrefetch(null)).toBeNull();
  });

  it('adoptAudio swaps in the warmed element only when it holds the same file', () => {
    const host = document.createElement('div');
    host.innerHTML = '<audio id="audioElement" preload="auto"></audio>';
    const warmed = warmAudio('https://audio.example/a.mp3');
    expect(warmed.preload).toBe('auto');
    const used = adoptAudio(host.firstChild, warmed, 'https://audio.example/a.mp3');
    expect(used).toBe(warmed);
    expect(host.querySelector('#audioElement')).toBe(warmed);

    host.innerHTML = '<audio id="audioElement"></audio>';
    const own = host.firstChild;
    expect(adoptAudio(own, warmed, 'https://audio.example/other.mp3')).toBe(own);
    expect(own.getAttribute('src')).toBe('https://audio.example/other.mp3');
    expect(adoptAudio(own, null, 'https://audio.example/b.mp3')).toBe(own);
  });
});

describe('player hooks', () => {
  beforeEach(() => {
    window.authFetch = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) }));
  });

  it('practice: loads the round, but not while attempts are still being recorded', async () => {
    const item = { kind: 'practice', id: 'maint_1', mode: 'maintenance', minutes: 5 };
    expect(practice.prefetch(item, { languageId: 2, current: { kind: 'practice' } })).toBeNull();
    expect(practice.prefetch(item, { languageId: 2, current: { kind: 'speed_round' } })).toBeNull();
    expect(practice.prefetch({ ...item, is_extra: true }, { languageId: 2 })).toBeNull();
    expect(window.authFetch).not.toHaveBeenCalled();

    const res = await practice.prefetch(item, {
      languageId: 2,
      current: { kind: 'test', test_type: 'reading' },
    });
    expect(res.ok).toBe(true);
    expect(window.authFetch).toHaveBeenCalledWith(
      '/api/practice/session?mode=maintenance&minutes=5&language_id=2'
    );
  });

  it('practice: describePrefetch gives the start-card line', () => {
    const t = (key, params, fallback) => fallback;
    const res = { ok: true, data: { items: [{ expected_seconds: 60 }, { expected_seconds: 60 }] } };
    expect(practice.describePrefetch(res, { moreRounds: 0, t })).toBe('2 exercises · about 2 min');
    expect(practice.describePrefetch({ ok: false, data: {} }, { moreRounds: 0, t })).toBe('');
  });

  it('speed round: same rule as practice', async () => {
    const item = { kind: 'speed_round', size: 12 };
    expect(speedRound.prefetch(item, { languageId: 2, current: { kind: 'practice' } })).toBeNull();
    await speedRound.prefetch(item, { languageId: 2, current: { kind: 'flashcards' } });
    expect(window.authFetch).toHaveBeenCalledWith('/api/practice/speed-round?language_id=2&size=12');
  });

  it('dictation: loads the test and warms its audio', async () => {
    window.authFetch = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ test_data: { audio_url: 'https://audio.example/d.mp3' } }),
    }));
    const res = await dictation.prefetch({ kind: 'test', test_type: 'dictation', slug: 'd1' });
    expect(window.authFetch).toHaveBeenCalledWith('/api/tests/test/d1?mode=dictation');
    expect(res.audio.getAttribute('src')).toBe('https://audio.example/d.mp3');
    expect(res.audio.preload).toBe('auto');
  });

  it('listening: loads the test, its sentences and its audio; reading has no audio', async () => {
    const calls = [];
    window.authFetch = vi.fn(async (url) => {
      calls.push(url);
      if (url.endsWith('/sentences')) {
        return { ok: true, status: 200, json: async () => ({ sentences: [] }) };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          test_data: { id: 't', transcript: '你好。', audio_url: 'https://audio.example/l.mp3' },
          questions_data: [],
        }),
      };
    });
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const res = await readingListening.prefetch({ kind: 'test', test_type: 'listening', slug: 'l1' });
    expect(calls).toEqual(['/api/tests/test/l1', '/api/tests/l1/sentences']);
    expect(res.ok).toBe(true);
    expect('sentences' in res).toBe(true);
    expect(res.audio.getAttribute('src')).toBe('https://audio.example/l.mp3');

    const reading = await readingListening.prefetch({ kind: 'test', test_type: 'reading', slug: 'r1' });
    expect(reading.audio).toBeUndefined();
  });

  it('dictation player uses the prefetched payload and audio instead of loading again', async () => {
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {});
    window.authFetch = vi.fn();
    const audio = warmAudio('https://audio.example/d.mp3');
    const item = {
      slug: 'd1',
      prefetch: Promise.resolve({
        ok: true,
        data: { test_data: { title: 'Pre', audio_url: 'https://audio.example/d.mp3', language: 'zh' } },
        audio,
      }),
    };
    const c = document.createElement('div');
    document.body.appendChild(c);
    const handle = dictation.mount(c, { item, languageId: 1, onComplete: vi.fn() });
    await flush();
    await flush();
    expect(window.authFetch).not.toHaveBeenCalled();
    expect(c.querySelector('#testTitle').textContent).toBe('Pre');
    expect(c.querySelector('#audioElement')).toBe(audio);
    expect(c.querySelector('#mainUi').style.display).toBe('block');
    handle.destroy();
    c.remove();
  });
});
