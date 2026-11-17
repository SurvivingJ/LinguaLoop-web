/**
 * static/js/session/controller.js — one-tap return to the session (TASK-993).
 *
 * Pages that leave a running session send the learner back with a one-shot
 * marker: `/session?resume=<slug>` (prestudy "Take the test") opens that test at
 * once when it is the next item, `/session?resume_after=<slug>` (the follow-up's
 * "Back to today's session") opens the item after that finished test. The
 * marker is removed from the URL before anything else, and any mismatch with
 * the server's queue falls back to the Today card.
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
    prefetch: vi.fn(() => Promise.resolve({ ok: true, data: {} })),
  };
}
const rl = fakePlayer('reading_listening');
const flash = fakePlayer('flashcards');
const pre = fakePlayer('prestudy');
vi.mock('../../static/js/session/players/reading_listening.js', () => rl);
vi.mock('../../static/js/session/players/flashcards.js', () => flash);
vi.mock('../../static/js/session/players/prestudy.js', () => pre);

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
const settle = async (n = 6) => {
  for (let i = 0; i < n; i++) await flush();
};

// A prestudy block for test "alpha", the test itself, then a flashcards block.
const QUEUE = [
  { kind: 'flashcards', id: 'fc_0', cards: 3, is_completed: true },
  { kind: 'prestudy', id: 'prestudy_t1', test_id: 't1', slug: 'alpha', is_completed: true },
  { kind: 'test', id: 't1', slug: 'alpha', test_type: 'reading', is_completed: false },
  { kind: 'flashcards', id: 'fc_1', cards: 3, is_completed: false },
];

let mod;
async function boot(url, queue = QUEUE, nextIndex = 2) {
  vi.resetModules();
  buildDom();
  window.history.replaceState(null, '', url);
  localStorage.setItem('selectedLanguageId', '1');
  window.authFetch = vi.fn(async () => ({
    ok: true,
    json: async () => ({
      data: { queue: queue.map((q) => ({ ...q })), next_index: nextIndex },
    }),
  }));
  const realAdd = document.addEventListener.bind(document);
  let init = null;
  const spy = vi.spyOn(document, 'addEventListener').mockImplementation((type, fn, opts) => {
    if (type === 'DOMContentLoaded') init = fn;
    else realAdd(type, fn, opts);
  });
  mod = await import('../../static/js/session/controller.js');
  spy.mockRestore();
  init();
  await settle();
}

const startShown = () => !$('sessionStart').classList.contains('d-none');

beforeEach(() => {
  mounts.length = 0;
  [rl, flash, pre].forEach((p) => p.mount.mockClear());
  window.LinguaI18n = undefined;
  window.LinguaMetadata = undefined;
  window.showToast = vi.fn();
  window.scrollTo = vi.fn();
});

afterEach(() => {
  delete window.authFetch;
  delete window.__ldSessionEarly;
  document.body.innerHTML = '';
  window.history.replaceState(null, '', '/');
  vi.restoreAllMocks();
});

describe('resume=<slug> (prestudy "Take the test")', () => {
  it('opens the test straight away, without the Today card', async () => {
    await boot('/session?resume=alpha');
    expect(mounts.map((m) => m.name)).toEqual(['reading_listening']);
    expect(mounts[0].ctx.item.slug).toBe('alpha');
    expect(startShown()).toBe(false);
    expect($('sessionLoading').classList.contains('d-none')).toBe(true);
    expect($('sessionProgress').classList.contains('d-none')).toBe(false);
  });

  it('removes the marker from the URL and keeps other parameters', async () => {
    await boot('/session?resume=alpha&foo=1#x');
    expect(window.location.pathname).toBe('/session');
    expect(window.location.search).toBe('?foo=1');
    expect(window.location.hash).toBe('#x');
  });

  it('a reload after that shows the Today card', async () => {
    await boot('/session?resume=alpha');
    // the URL the reload would use
    await boot(window.location.pathname + window.location.search);
    expect(mounts.map((m) => m.name)).toEqual(['reading_listening']);
    expect(startShown()).toBe(true);
  });

  it('without a marker the Today card shows as before', async () => {
    await boot('/session');
    expect(mounts).toHaveLength(0);
    expect(startShown()).toBe(true);
    $('sessionStartBtn').click();
    await settle();
    expect(mounts.map((m) => m.name)).toEqual(['reading_listening']);
  });

  it('falls back to the Today card when another item is next', async () => {
    // the block did not save: the prestudy item is still the next one
    const q = QUEUE.map((x) => (x.kind === 'prestudy' ? { ...x, is_completed: false } : x));
    await boot('/session?resume=alpha', q, 1);
    expect(mounts).toHaveLength(0);
    expect(startShown()).toBe(true);
    expect(window.location.search).toBe('');
  });

  it('falls back when the test was finished elsewhere or left the queue', async () => {
    const done = QUEUE.map((x) => (x.id === 't1' ? { ...x, is_completed: true } : x));
    await boot('/session?resume=alpha', done, 3);
    expect(mounts).toHaveLength(0);
    expect(startShown()).toBe(true);

    await boot('/session?resume=gone');
    expect(mounts).toHaveLength(0);
    expect(startShown()).toBe(true);
  });

  it('a prestudy block with the same slug is not the test', async () => {
    const q = QUEUE.map((x) => (x.kind === 'prestudy' ? { ...x, is_completed: false } : x));
    await boot('/session?resume=alpha', q, 0);
    expect(mounts).toHaveLength(0);
  });

  it('shows the summary, not a player, when nothing is left', async () => {
    const all = QUEUE.map((x) => ({ ...x, is_completed: true }));
    await boot('/session?resume=alpha', all, 4);
    expect(mounts).toHaveLength(0);
    expect($('sessionSummary').classList.contains('d-none')).toBe(false);
  });

  it('is ignored in practice mode (marker still consumed)', async () => {
    await boot('/session?mode=practice&resume=alpha');
    expect(mounts.filter((m) => m.name === 'reading_listening')).toHaveLength(0);
    expect(window.location.search).toBe('?mode=practice');
  });
});

describe('resume_after=<slug> (follow-up "Back to today\'s session")', () => {
  const after = QUEUE.map((x) => (x.id === 't1' ? { ...x, is_completed: true } : x));

  it('opens the item after the finished test', async () => {
    await boot('/session?resume_after=alpha', after, 3);
    expect(mounts.map((m) => m.name)).toEqual(['flashcards']);
    expect(mounts[0].ctx.item.id).toBe('fc_1');
    expect(startShown()).toBe(false);
    expect(window.location.search).toBe('');
  });

  it('falls back when the test is not finished (its save failed)', async () => {
    await boot('/session?resume_after=alpha', QUEUE, 2);
    expect(mounts).toHaveLength(0);
    expect(startShown()).toBe(true);
  });
});

describe('resumeIndex', () => {
  it('matches only the item Resume would open', async () => {
    await boot('/session');
    const { resumeIndex } = mod;
    expect(resumeIndex(null, QUEUE, 2)).toBe(-1);
    expect(resumeIndex({ slug: 'alpha', after: false }, QUEUE, 2)).toBe(2);
    expect(resumeIndex({ slug: 'alpha', after: false }, QUEUE, 0)).toBe(2);
    expect(resumeIndex({ slug: 'alpha', after: true }, QUEUE, 2)).toBe(-1);
    expect(resumeIndex({ slug: '', after: false }, QUEUE, 2)).toBe(-1);
  });
});
