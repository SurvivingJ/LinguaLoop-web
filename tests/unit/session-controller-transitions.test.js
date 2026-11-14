/**
 * static/js/session/controller.js — item transitions: the next item mounts at
 * once while the completion is saved in the background, the item after the
 * current one is prefetched, a save that fails is shown (not lost), and the
 * tail check waits for outstanding saves.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const mounts = [];
function fakePlayer(name) {
  return {
    mount: vi.fn((container, ctx) => {
      mounts.push({ name, ctx });
      container.innerHTML = `<p>${name}</p>`;
      return { destroy() {} };
    }),
    prefetch: vi.fn((item) => Promise.resolve({ ok: true, data: { for: item.id } })),
  };
}
const flash = fakePlayer('flashcards');
const dt = fakePlayer('dual_translation');
vi.mock('../../static/js/session/players/flashcards.js', () => flash);
vi.mock('../../static/js/session/players/dual_translation.js', () => dt);

function buildDom() {
  document.body.innerHTML = `
    <div id="sessionLoading"></div>
    <div id="sessionError" class="d-none"><span id="sessionErrorMsg"></span><button id="sessionErrorRetry"></button></div>
    <div id="sessionStart" class="d-none">
      <p id="sessionStartSummary"></p><p id="sessionStartCount" class="d-none"></p>
      <button id="sessionStartBtn"><span id="sessionStartBtnLabel"></span></button>
    </div>
    <div id="sessionProgress" class="d-none">
      <span id="sessionProgressCount"></span><span id="sessionProgressFill"></span>
      <div id="sessionDots"></div>
    </div>
    <div id="sessionSaveStatus" class="d-none"><button id="sessionSaveRetry"></button></div>
    <div id="sessionStage"></div>
    <div id="sessionSummary" class="d-none">
      <div id="sessionSummaryBody"></div>
      <div id="sessionTailPrompt" class="d-none">
        <p id="sessionTailMessage"></p><p id="sessionTailGovernor" class="d-none"></p>
        <button id="sessionTailKeepGoing"></button><button id="sessionTailDone"></button>
      </div>
    </div>`;
}

const $ = (id) => document.getElementById(id);
const flush = () => new Promise((r) => setTimeout(r, 0));
const settle = async (n = 5) => {
  for (let i = 0; i < n; i++) await flush();
};

const QUEUE = [
  { kind: 'flashcards', id: 'fc_0', cards: 3 },
  { kind: 'dual_translation', id: 'dt_0' },
  { kind: 'flashcards', id: 'fc_1', cards: 3 },
];

let calls;
let completeImpl;

async function boot(queue = QUEUE) {
  vi.resetModules();
  buildDom();
  localStorage.setItem('selectedLanguageId', '2');
  calls = [];
  window.authFetch = vi.fn(async (url, opts) => {
    calls.push({ url, opts });
    if (url.startsWith('/api/study-session/complete-block')) return completeImpl(url, opts);
    return {
      ok: true,
      json: async () => ({ data: { queue: queue.map((q) => ({ ...q })), next_index: 0 } }),
    };
  });
  // Each import registers its own DOMContentLoaded listener; run only this
  // instance's, so controllers from earlier tests stay asleep.
  const realAdd = document.addEventListener.bind(document);
  let init = null;
  const spy = vi.spyOn(document, 'addEventListener').mockImplementation((type, fn, opts) => {
    if (type === 'DOMContentLoaded') init = fn;
    else realAdd(type, fn, opts);
  });
  await import('../../static/js/session/controller.js');
  spy.mockRestore();
  init();
  await settle();
}

const posts = () => calls.filter((c) => c.opts && c.opts.method === 'POST');
const sessionGets = () => calls.filter((c) => c.url.startsWith('/api/study-session?'));

beforeEach(() => {
  mounts.length = 0;
  [flash, dt].forEach((p) => {
    p.mount.mockClear();
    p.prefetch.mockClear();
  });
  completeImpl = async () => ({ ok: true });
  window.LinguaI18n = undefined;
  window.LinguaMetadata = undefined;
  window.showToast = vi.fn();
  window.scrollTo = vi.fn();
});

afterEach(() => {
  delete window.authFetch;
  delete window.showToast;
  delete window.__ldSessionEarly;
  document.body.innerHTML = '';
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('item transitions', () => {
  it('mounts the next item without waiting for the completion POST', async () => {
    let release;
    completeImpl = () => new Promise((r) => (release = () => r({ ok: true })));
    await boot();
    $('sessionStartBtn').click();
    await settle();
    expect(mounts.map((m) => m.name)).toEqual(['flashcards']);

    mounts[0].ctx.onComplete({});
    await settle();
    // The save is still in flight, yet the next player is already on stage.
    expect(posts()).toHaveLength(1);
    expect(JSON.parse(posts()[0].opts.body)).toEqual({ block_id: 'fc_0', language_id: 2 });
    expect(posts()[0].opts.keepalive).toBe(true);
    expect(mounts.map((m) => m.name)).toEqual(['flashcards', 'dual_translation']);
    expect($('sessionProgressCount').textContent).toBe('1/3');
    release();
    await settle();
    expect($('sessionSaveStatus').classList.contains('d-none')).toBe(true);
  });

  it('a second onComplete for the same item is ignored', async () => {
    await boot();
    $('sessionStartBtn').click();
    await settle();
    const first = mounts[0].ctx;
    first.onComplete({});
    first.onComplete({});
    first.onSkip();
    await settle();
    expect(posts()).toHaveLength(1);
    expect(mounts.map((m) => m.name)).toEqual(['flashcards', 'dual_translation']);
  });

  it('prefetches the first item on the start card and the next one during play', async () => {
    await boot();
    expect(flash.prefetch).toHaveBeenCalledTimes(1);
    expect(flash.prefetch.mock.calls[0][0].id).toBe('fc_0');
    expect(flash.prefetch.mock.calls[0][1]).toEqual({ languageId: 2, current: null });
    expect(dt.prefetch).not.toHaveBeenCalled();

    $('sessionStartBtn').click();
    await settle();
    expect(dt.prefetch).toHaveBeenCalledTimes(1);
    expect(dt.prefetch.mock.calls[0][0].id).toBe('dt_0');
    expect(dt.prefetch.mock.calls[0][1].current.id).toBe('fc_0');
    // The mounted player was handed the item carrying its prefetched payload.
    expect(await mounts[0].ctx.item.prefetch).toEqual({ ok: true, data: { for: 'fc_0' } });

    mounts[0].ctx.onComplete({});
    await settle();
    expect(flash.prefetch).toHaveBeenCalledTimes(2);
    expect(flash.prefetch.mock.calls[1][0].id).toBe('fc_1');
    expect(flash.prefetch.mock.calls[1][1].current.id).toBe('dt_0');
  });

  it('retries a failed save, then shows the banner; Retry saves it', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    let online = false;
    completeImpl = async () => ({ ok: online });
    await boot();
    $('sessionStartBtn').click();
    await settle();
    vi.useFakeTimers();
    mounts[0].ctx.onComplete({});
    await vi.advanceTimersByTimeAsync(10);
    // Already on the next item while the save is being retried.
    expect(mounts.map((m) => m.name)).toEqual(['flashcards', 'dual_translation']);
    expect($('sessionSaveStatus').classList.contains('d-none')).toBe(true);
    await vi.advanceTimersByTimeAsync(5000);
    expect(posts()).toHaveLength(3);
    expect($('sessionSaveStatus').classList.contains('d-none')).toBe(false);
    // The persistent banner replaces the transient toast.
    expect(window.showToast).not.toHaveBeenCalled();

    online = true;
    $('sessionSaveRetry').click();
    await vi.advanceTimersByTimeAsync(10);
    expect(posts()).toHaveLength(4);
    expect($('sessionSaveStatus').classList.contains('d-none')).toBe(true);
  });

  it('the tail check waits for outstanding saves', async () => {
    let release;
    completeImpl = () => new Promise((r) => (release = () => r({ ok: true })));
    await boot([{ kind: 'flashcards', id: 'fc_0', cards: 3 }]);
    $('sessionStartBtn').click();
    await settle();
    expect(sessionGets()).toHaveLength(1);
    mounts[0].ctx.onComplete({});
    await settle();
    // Summary is up, but the server is not asked about the tail yet.
    expect($('sessionSummary').classList.contains('d-none')).toBe(false);
    expect(sessionGets()).toHaveLength(1);
    release();
    await settle();
    expect(sessionGets()).toHaveLength(2);
  });
});

describe('early session request', () => {
  it('uses the response the page already asked for', async () => {
    const early = {
      url: '/api/study-session?language_id=2',
      promise: Promise.resolve({
        ok: true,
        json: async () => ({ data: { queue: [{ kind: 'flashcards', id: 'early_fc' }], next_index: 0 } }),
      }),
    };
    window.__ldSessionEarly = early;
    await boot();
    expect(sessionGets()).toHaveLength(0);
    expect(window.__ldSessionEarly).toBeNull();
    $('sessionStartBtn').click();
    await settle();
    expect(mounts[0].ctx.item.id).toBe('early_fc');
  });

  it('asks again through authFetch when the early request was refused', async () => {
    window.__ldSessionEarly = {
      url: '/api/study-session?language_id=2',
      promise: Promise.resolve({ ok: false, status: 401 }),
    };
    await boot();
    expect(sessionGets()).toHaveLength(1);
    expect($('sessionStart').classList.contains('d-none')).toBe(false);
  });

  it('ignores an early request made for another URL', async () => {
    window.__ldSessionEarly = {
      url: '/api/study-session?language_id=9',
      promise: Promise.resolve({ ok: true, json: async () => ({ data: { queue: [] } }) }),
    };
    await boot();
    expect(sessionGets()).toHaveLength(1);
  });
});
