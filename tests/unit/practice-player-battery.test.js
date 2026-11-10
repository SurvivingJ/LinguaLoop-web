/**
 * Ladder checkpoints in static/js/session/players/practice.js: a gate marker
 * in the practice queue opens its battery (POST /api/vocab-dojo/gate), each
 * battery item is posted with exercise_context 'gate' and never re-queued, and
 * the last answer submits the battery (POST /api/vocab-dojo/gate/result).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/practice.js';

let realER;
let initOpts;
let fetchMock;

const flush = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  realER = window.ExRenderers;
  initOpts = null;
  window.ExRenderers = {
    init: (o) => { initOpts = o; },
    dispatch: vi.fn((type, ex, c, w) => {
      // the real renderers inject a feedback slot
      initOpts.cardEl.innerHTML = `${w}<div id="exerciseFeedback"></div><button id="nextBtn"></button>`;
    }),
    escHtml: (s) => String(s),
    shuffleArr: (a) => a.slice(),
  };
  fetchMock = vi.fn(async (url, opts) => {
    const u = String(url);
    if (u.startsWith('/api/practice/session')) {
      return { ok: true, json: async () => ({ items: [{ is_gate_marker: true, gate_name: 'gate_a', sense_id: 9, mode: 'acquisition' }] }) };
    }
    if (u === '/api/vocab-dojo/gate') {
      return { ok: true, json: async () => ({ data: {
        battery_token: 'tok', exercises: [
          { exercise_id: 'g1', exercise_type: 'cloze_completion', content: {} },
          { exercise_id: 'g2', exercise_type: 'cloze_completion', content: {} },
        ] } }) };
    }
    if (u === '/api/practice/attempt') {
      return { ok: true, json: async () => ({ requeue: !JSON.parse(opts.body).is_correct }) };
    }
    if (u === '/api/vocab-dojo/gate/result') {
      return { ok: true, json: async () => ({ data: { passed: true, correct: 1, battery_size: 2 } }) };
    }
    return { ok: true, json: async () => ({}) };
  });
  window.authFetch = fetchMock;
});

afterEach(() => {
  window.ExRenderers = realER;
  delete window.authFetch;
});

describe('practice player ladder checkpoints', () => {
  it('runs a gate battery in place of its marker and submits it', async () => {
    const container = document.createElement('div');
    mount(container, { item: { mode: 'acquisition', minutes: 10 }, languageId: 3 });
    for (let i = 0; i < 5; i++) await flush();
    expect(window.ExRenderers.dispatch).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain('Checkpoint · 1 of 2');

    initOpts.showFeedback(false, '');
    await initOpts.submitAttempt(false, {});
    initOpts.nextExercise();
    await flush();
    initOpts.showFeedback(true, '');
    await initOpts.submitAttempt(true, {});
    await flush();

    const attempts = fetchMock.mock.calls.filter((c) => c[0] === '/api/practice/attempt').map((c) => JSON.parse(c[1].body));
    expect(attempts.map((a) => [a.exercise_id, a.exercise_context])).toEqual([['g1', 'gate'], ['g2', 'gate']]);
    const result = fetchMock.mock.calls.find((c) => c[0] === '/api/vocab-dojo/gate/result');
    expect(JSON.parse(result[1].body)).toMatchObject({
      sense_id: 9, gate_name: 'gate_a', battery_token: 'tok',
      results: [{ exercise_id: 'g1', is_correct: false }, { exercise_id: 'g2', is_correct: true }],
    });
    expect(container.textContent).toContain('Checkpoint passed (1/2)');
    // the wrong battery answer was not re-queued
    initOpts.nextExercise();
    await flush();
    expect(window.ExRenderers.dispatch).toHaveBeenCalledTimes(2);
  });
});
