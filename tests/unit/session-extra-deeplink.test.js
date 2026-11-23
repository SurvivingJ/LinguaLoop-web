/**
 * static/js/session/controller.js — `/session?mode=practice&extra=reviews` (TASK-1043).
 *
 * The knowledge page's "Review in Practice" links here. When practice mode has nothing required
 * left today (an empty queue, or every exercise done) and no new words are waiting, the
 * controller starts the reviews extra round at once instead of waiting for a click on the
 * extra-round panel; the parameter is consumed so a reload does not start another round. With
 * work left today, nothing changes.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const mounts = [];
const practice = {
  mount: vi.fn((container, ctx) => {
    mounts.push(ctx.item || null);
    container.innerHTML = '<p>practice</p>';
    return { destroy() {} };
  }),
  prefetch: vi.fn(() => null),
  describePrefetch: vi.fn(() => ''),
};
vi.mock('../../static/js/session/players/practice.js', () => practice);

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
    <div id="sessionStage"></div>
    <div id="sessionSummary" class="d-none">
      <div id="sessionSummaryBody"></div>
      <div id="sessionResultsWrap"><ul id="sessionResults"></ul></div>
      <div id="sessionNewWordsPrompt" class="d-none">
        <button id="sessionNewWordsStart"></button><button id="sessionNewWordsLater"></button>
      </div>
      <div id="sessionExtraPanel" class="d-none">
        <input type="checkbox" id="sessionExtraReviews" />
        <select id="sessionExtraNewWords"><option value="0">0</option><option value="5">5</option></select>
        <p id="sessionExtraWarning" class="d-none"></p>
        <button id="sessionExtraStart"></button><button id="sessionExtraDone"></button>
      </div>
      <div id="sessionTailPrompt" class="d-none">
        <p id="sessionTailMessage"></p><p id="sessionTailGovernor" class="d-none"></p>
        <button id="sessionTailKeepGoing"></button><button id="sessionTailDone"></button>
      </div>
    </div>`;
}

const $ = (id) => document.getElementById(id);
const settle = async (n = 8) => {
  for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0));
};

const DONE = { kind: 'practice', id: 'maint_0', mode: 'maintenance', is_completed: true };
const OPEN = { kind: 'practice', id: 'maint_1', mode: 'maintenance', is_completed: false };
const NEW_WORDS = { kind: 'practice', id: 'acq_0', mode: 'acquisition', is_completed: false };

async function boot(url, queue) {
  vi.resetModules();
  buildDom();
  window.history.replaceState({}, '', url);
  localStorage.setItem('selectedLanguageId', '2');
  window.authFetch = vi.fn(async () => ({
    ok: true,
    json: async () => ({
      data: { queue: queue.map((q) => ({ ...q })), next_index: 0, tail: null, tail_queue: [] },
    }),
  }));
  const realAdd = document.addEventListener.bind(document);
  let init = null;
  const spy = vi.spyOn(document, 'addEventListener').mockImplementation((type, fn, opts) => {
    if (type === 'DOMContentLoaded') init = fn;
    else realAdd(type, fn, opts);
  });
  const mod = await import('../../static/js/session/controller.js');
  spy.mockRestore();
  init();
  await settle();
  return mod;
}

const extraMounts = () => mounts.filter((item) => item && item.is_extra);

beforeEach(() => {
  mounts.length = 0;
  practice.mount.mockClear();
  window.LinguaI18n = undefined;
  window.LinguaMetadata = undefined;
  window.showToast = vi.fn();
  window.scrollTo = vi.fn();
});

afterEach(() => {
  delete window.authFetch;
  delete window.showToast;
  document.body.innerHTML = '';
  window.history.replaceState({}, '', '/');
  vi.restoreAllMocks();
});

describe('practice deep link extra=reviews', () => {
  it('starts a reviews round at once when the practice queue is empty', async () => {
    await boot('/session?mode=practice&extra=reviews', []);
    expect(extraMounts()).toHaveLength(1);
    expect(extraMounts()[0].extra).toMatchObject({ reviews: true, newWords: 0 });
    expect(extraMounts()[0].mode).toBe('maintenance');
    expect($('sessionExtraPanel').classList.contains('d-none')).toBe(true);
  });

  it("starts it when today's exercises are all done", async () => {
    await boot('/session?mode=practice&extra=reviews', [DONE]);
    expect(extraMounts()).toHaveLength(1);
  });

  it('consumes the parameter so a reload does not start another round', async () => {
    await boot('/session?mode=practice&extra=reviews', []);
    expect(window.location.search).toBe('?mode=practice');
  });

  it('changes nothing while exercises are left today', async () => {
    await boot('/session?mode=practice&extra=reviews', [OPEN]);
    expect(extraMounts()).toHaveLength(0);
    expect($('sessionStart').classList.contains('d-none')).toBe(false);
  });

  it("lets today's new words come first", async () => {
    await boot('/session?mode=practice&extra=reviews', [DONE, NEW_WORDS]);
    expect(extraMounts()).toHaveLength(0);
  });

  it('without the parameter the empty queue shows the panel, as before', async () => {
    await boot('/session?mode=practice', []);
    expect(extraMounts()).toHaveLength(0);
    expect($('sessionExtraPanel').classList.contains('d-none')).toBe(false);
  });

  it('is ignored outside practice mode', async () => {
    await boot('/session?extra=reviews', []);
    expect(extraMounts()).toHaveLength(0);
    expect(window.location.search).toBe('?extra=reviews');
  });
});

describe('takeExtraDeepLink', () => {
  it('reads and removes only extra=reviews', async () => {
    const mod = await boot('/session?mode=practice', [OPEN]);
    const hist = { state: null, replaceState: vi.fn() };
    const loc = { pathname: '/session', search: '?mode=practice&extra=reviews', hash: '' };
    expect(mod.takeExtraDeepLink(loc, hist)).toBe(true);
    expect(hist.replaceState).toHaveBeenCalledWith(null, '', '/session?mode=practice');
    expect(
      mod.takeExtraDeepLink({ pathname: '/session', search: '?extra=new', hash: '' }, hist)
    ).toBe(false);
  });
});
