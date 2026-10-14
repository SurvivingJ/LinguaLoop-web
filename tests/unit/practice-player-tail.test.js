/**
 * Unit tests for the tail flag in static/js/session/players/practice.js:
 * the optional "Keep going?" round requests /api/practice/session with tail=1
 * and echoes is_tail on every attempt POST (session-budget-settings).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/practice.js';

const EX = {
  exercise_id: 'ex-1',
  exercise_type: 'mc',
  expected_seconds: 12,
  content: {},
};

let realER;
let initOpts;
let fetchMock;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

beforeEach(() => {
  realER = window.ExRenderers;
  initOpts = null;
  window.ExRenderers = {
    init: (o) => {
      initOpts = o;
    },
    dispatch: vi.fn(),
    escHtml: (s) => String(s),
    shuffleArr: (a) => a.slice(),
  };
  fetchMock = vi.fn(async (url) => {
    if (String(url).startsWith('/api/practice/session')) {
      return { ok: true, json: async () => ({ items: [EX] }) };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  });
  window.authFetch = fetchMock;
});

afterEach(() => {
  window.ExRenderers = realER;
  delete window.authFetch;
});

async function run(item) {
  const container = document.createElement('div');
  mount(container, { item, languageId: 7 });
  await flush();
  initOpts.submitAttempt(true, { picked: 0 });
  await flush();
  const attemptCall = fetchMock.mock.calls.find((c) => c[0] === '/api/practice/attempt');
  return {
    sessionUrl: fetchMock.mock.calls[0][0],
    body: JSON.parse(attemptCall[1].body),
  };
}

describe('practice player tail flag', () => {
  it('adds tail=1 to the session URL and is_tail to the attempt for tail items', async () => {
    const { sessionUrl, body } = await run({ mode: 'maintenance', minutes: 6, is_tail: true });
    expect(sessionUrl).toContain('&tail=1');
    expect(sessionUrl).toContain('mode=maintenance');
    expect(body.is_tail).toBe(true);
    expect(body.session_mode).toBe('maintenance');
  });

  it('leaves the URL and attempt untouched for main-session items', async () => {
    const { sessionUrl, body } = await run({ mode: 'acquisition', minutes: 10 });
    expect(sessionUrl).not.toContain('tail');
    expect('is_tail' in body).toBe(false);
  });
});
