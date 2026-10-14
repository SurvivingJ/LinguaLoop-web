/**
 * static/js/session/controller.js — the optional tail is also offered when the
 * REQUIRED queue is empty (e.g. a weekday-weight-0 day with reviews due), not
 * only from the end-of-session summary.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const TAIL = {
  tail: {
    reviews_left_items: 6,
    reviews_left_minutes: 2,
    new_words_left: 0,
    new_words_left_minutes: 0,
  },
  tail_queue: [{ kind: 'practice', id: 'tail_maint_0', mode: 'maintenance', minutes: 2 }],
  governor: null,
};

function buildDom() {
  document.body.innerHTML = `
    <div id="sessionLoading"></div>
    <div id="sessionError" class="d-none"><span id="sessionErrorMsg"></span><button id="sessionErrorRetry"></button></div>
    <div id="sessionStart" class="d-none">
      <p id="sessionStartSummary"></p>
      <button id="sessionStartBtn"><span id="sessionStartBtnLabel"></span></button>
    </div>
    <div id="sessionProgress" class="d-none"></div>
    <div id="sessionStage"></div>
    <div id="sessionSummary" class="d-none">
      <div id="sessionSummaryBody"></div>
      <div id="sessionTailPrompt" class="d-none">
        <p id="sessionTailMessage"></p><p id="sessionTailGovernor" class="d-none"></p>
        <button id="sessionTailKeepGoing"></button><button id="sessionTailDone"></button>
      </div>
    </div>`;
}

const flush = () => new Promise((r) => setTimeout(r, 0));

async function boot(responses) {
  vi.resetModules();
  buildDom();
  localStorage.setItem('selectedLanguageId', '2');
  const calls = [];
  window.authFetch = vi.fn(async (url) => {
    calls.push(url);
    const body = responses.shift();
    return { ok: true, json: async () => ({ data: body }) };
  });
  await import('../../static/js/session/controller.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
  for (let i = 0; i < 5; i++) await flush();
  return calls;
}

beforeEach(() => {
  window.LinguaI18n = undefined;
  window.LinguaMetadata = undefined;
});

afterEach(() => {
  delete window.authFetch;
  document.body.innerHTML = '';
});

describe('empty required queue', () => {
  it('offers the optional tail when reviews are left', async () => {
    const calls = await boot([{ queue: [], next_index: 0 }, { queue: [], ...TAIL }]);
    expect(calls).toHaveLength(2); // initial load + the tail check
    expect($('sessionTailPrompt').classList.contains('d-none')).toBe(false);
    expect($('sessionSummary').classList.contains('d-none')).toBe(false);
    expect($('sessionStart').classList.contains('d-none')).toBe(true);
    expect($('sessionSummaryBody').textContent).toContain('No session items for today');
  });

  it('keeps the plain empty state when nothing optional is left', async () => {
    await boot([
      { queue: [], next_index: 0 },
      { queue: [], tail: null, tail_queue: [], governor: null },
    ]);
    expect($('sessionTailPrompt').classList.contains('d-none')).toBe(true);
    expect($('sessionSummary').classList.contains('d-none')).toBe(true);
    expect($('sessionStart').classList.contains('d-none')).toBe(false);
    expect($('sessionStartSummary').textContent).toContain('No session items for today');
  });

  it('"Done for today" hides the prompt', async () => {
    await boot([{ queue: [], next_index: 0 }, { queue: [], ...TAIL }]);
    $('sessionTailDone').click();
    expect($('sessionTailPrompt').classList.contains('d-none')).toBe(true);
  });
});

function $(id) {
  return document.getElementById(id);
}
