/**
 * TASK-989 (ADR-047 open question 1): the prestudy page gets exercise content
 * only for the words the prime drills and loads the rest on demand.
 *
 * - drillSenseIds / isDrilled replay tests/unit/fixtures/prestudy-drill-rule.json,
 *   the fixture tests/test_exercise_content_prestudy_reader.py replays against
 *   services/prestudy.py drill_sense_ids, so client and server pick the same words.
 * - createExerciseLoader: batches of at most 20 senses, no duplicate in-flight
 *   requests, failures leave the word on the no-exercise path (no retry).
 * - The page (static/js/prestudy/prestudy.js on templates/test_prestudy.html's
 *   markup): "I don't know this" fetches the word's exercises once, the prime
 *   waits for them, and a failed fetch degrades without a crash or any request
 *   other than GET .../prestudy/exercises.
 */

import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const fixture = JSON.parse(readFileSync(join(root, 'tests/unit/fixtures/prestudy-drill-rule.json'), 'utf8'));
const template = readFileSync(join(root, 'templates/test_prestudy.html'), 'utf8');
const pageMarkup = template.split('{% block content %}')[1].split('{% endblock %}')[0];

const ok = (body) => ({ ok: true, status: 200, json: async () => body });
const flush = async (n = 5) => { for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0)); };
function deferred() {
  let resolve; let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

let L;
beforeAll(async () => {
  await import('../../static/js/prestudy/prestudy.js');
  L = window.LinguaPrestudy;
});

// ---------------------------------------------------------------------------
// The drill rule
// ---------------------------------------------------------------------------

describe('drillSenseIds (shared fixture with services/prestudy.py)', () => {
  for (const c of fixture.cases) {
    it(c.name, () => {
      const got = [...new Set(L.drillSenseIds(c.payload).map(Number))].sort((a, b) => a - b);
      expect(got).toEqual(c.drill);
    });
  }

  it('drills strictly below probably_known, and every word the learner adds', () => {
    expect(L.DRILL_MAX_P).toBe(0.75);
    expect(L.isDrilled(0.75, false)).toBe(false);
    expect(L.isDrilled(0.7499999, false)).toBe(true);
    expect(L.isDrilled(0.99, true)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// createExerciseLoader
// ---------------------------------------------------------------------------

describe('createExerciseLoader', () => {
  const EX = (id, okToShow = true) => ({ id, type: 'cloze_completion', group: 'use', okToShow });
  let warn;
  beforeEach(() => { warn = vi.spyOn(console, 'warn').mockImplementation(() => {}); });
  afterEach(() => { warn.mockRestore(); });

  function make(fetchImpl, { map = {}, has = [], batchSize } = {}) {
    const exercises = map;
    const loader = L.createExerciseLoader({
      exercises, hasExercises: new Set(has.map(String)), fetchImpl, batchSize,
      usable: (e) => e.okToShow !== false,
      url: (ids) => `/api/tests/cats/prestudy/exercises?sense_ids=${ids.join(',')}`,
    });
    return { loader, exercises };
  }
  const idsOf = (url) => url.split('sense_ids=')[1].split(',');

  it('batches at most 20 senses per request and never requests a sense twice', async () => {
    const all = Array.from({ length: 45 }, (_, i) => i + 1);
    const fetchImpl = vi.fn(async () => ok({ status: 'success', exercises: {} }));
    const { loader, exercises } = make(fetchImpl, { has: all, batchSize: 50 });   // capped at 20
    const first = loader.ensure(all);
    const again = loader.ensure(['1', 1, '45', 45]);                          // all in flight
    await Promise.all([first, again]);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    const batches = fetchImpl.mock.calls.map((c) => idsOf(c[0]));
    expect(batches.map((b) => b.length)).toEqual([20, 20, 5]);
    expect(new Set(batches.flat()).size).toBe(45);
    // a sense the server returned nothing for is loaded, with no exercises
    expect(exercises['45']).toEqual([]);
    await loader.ensure(all);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it('fetches only senses that have exercises and are not loaded yet', async () => {
    const fetchImpl = vi.fn(async () => ok({ exercises: {} }));
    const { loader } = make(fetchImpl, { map: { 1: [EX('a')] }, has: [1, 2] });
    await loader.ensure([1, 2, 3]);
    expect(fetchImpl.mock.calls.map((c) => idsOf(c[0]))).toEqual([['2']]);
    expect(loader.waiting([1, 2, 3])).toBe(false);
    await loader.ensure([1, 3]);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it('fills the map with usable exercises from either response envelope', async () => {
    const good = EX('g'); const bad = EX('b', false);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(ok({ data: { exercises: { 2: [good, bad] } } }))
      .mockResolvedValueOnce(ok({ status: 'success', sense_ids: [3], exercises: { 3: [good] } }));
    const { loader, exercises } = make(fetchImpl, { has: [2, 3] });
    await loader.ensure([2]);
    await loader.ensure([3]);
    expect(exercises).toEqual({ 2: [good], 3: [good] });
  });

  it('dedupes against a request in flight and reports it as waiting', async () => {
    const d = deferred();
    const fetchImpl = vi.fn(() => d.promise);
    const { loader, exercises } = make(fetchImpl, { has: [2] });
    const p = loader.ensure([2]);
    expect(loader.isPending(2)).toBe(true);
    expect(loader.waiting([2])).toBe(true);
    await flush();
    loader.ensure([2]);
    await flush();
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    d.resolve(ok({ exercises: { 2: [EX('x')] } }));
    await p;
    expect(loader.isPending(2)).toBe(false);
    expect(loader.waiting([2])).toBe(false);
    expect(exercises[2]).toHaveLength(1);
  });

  it.each([
    ['an HTTP error', () => Promise.resolve({ ok: false, status: 500, json: async () => ({}) })],
    ['a network error', () => Promise.reject(new Error('offline'))],
    ['a bad body', () => Promise.resolve({ ok: true, status: 200, json: async () => { throw new Error('json'); } })],
  ])('a failed request (%s) leaves the words without exercises and is not retried', async (_name, impl) => {
    const fetchImpl = vi.fn(impl);
    const { loader, exercises } = make(fetchImpl, { has: [2, 3] });
    await expect(loader.ensure([2, 3])).resolves.toBeUndefined();
    expect(loader.hasFailed(2)).toBe(true);
    expect(loader.isLoaded(2)).toBe(false);
    expect(exercises).toEqual({});
    expect(loader.waiting([2, 3])).toBe(false);
    await loader.ensure([2, 3]);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(warn).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// The page: "I don't know this" -> on-demand fetch -> the prime waits for it
// ---------------------------------------------------------------------------

const CLOZE = (id, word) => ({
  id, type: 'cloze_completion', group: 'use', level: 3,
  c: { sentence_with_blank: `__${word}`, options: [word, 'x'], correct_answer: word, explanation: '', original_sentence: `${word}。` },
});
const sense = (lemma, reading, def, freq) => ({ lemma, pos: 'noun', freq, reading, glosses: { 2: { def, ex: null } } });

function payload(over = {}) {
  return {
    status: 'success',
    test: {
      id: 't1', slug: 'cats', title: '猫', language_id: 3, transcript: '猫が犬と鳥。', audio_url: null,
      vocab_sense_ids: [11, 12, 13],
      vocab_token_map: [['猫', 11], ['が', null], ['犬', 12], ['と', null], ['鳥', 13], ['。', null]],
      furigana_payload: null, pinyin_payload: null,
    },
    questions: [],
    senses: { 11: sense('猫', 'ねこ', 'cat', 4.0), 12: sense('犬', 'いぬ', 'dog', 4.0), 13: sense('鳥', 'とり', 'bird', 4.0) },
    // 11 is drilled (p 0.1); 12 and 13 are known (not drilled)
    knowledge: { 11: { p: 0.1, status: 'unknown', n: 2 }, 12: { p: 0.9, status: 'known', n: 9 }, 13: { p: 0.95, status: 'known', n: 9 } },
    exercises: { 11: [CLOZE('e11', '猫')] },
    has_exercises: [11, 12],
    gloss_language_id: 2,
    ability_zipf: 5.0,
    ...over,
  };
}

describe('prestudy page', () => {
  let calls; let exerciseReply; let warn;

  async function boot(data) {
    calls = [];
    window.authFetch = vi.fn((url, opts) => {
      calls.push({ url, method: (opts && opts.method) || 'GET' });
      if (url === '/api/tests/cats/prestudy') return Promise.resolve(ok(data));
      if (url.endsWith('/prestudy/session')) return Promise.resolve(ok({ status: 'success', session_id: null }));
      if (url.includes('/prestudy/exercises?')) return exerciseReply(url);
      return Promise.reject(new Error('unexpected request ' + url));
    });
    vi.resetModules();
    await import('../../static/js/prestudy/prestudy.js');
    if (document.readyState === 'loading') document.dispatchEvent(new Event('DOMContentLoaded'));
    await flush();
    expect(document.getElementById('psMain').hidden).toBe(false);
  }
  const exerciseCalls = () => calls.filter((c) => c.url.includes('/prestudy/exercises?'));
  const header = () => JSON.parse(document.getElementById('psQuizMode').textContent.split('|')[1]);
  function addWord(sid) {
    document.querySelector(`.ps-tok[data-sid="${sid}"]`).click();
    document.getElementById('psPopAdd').click();
  }

  beforeEach(() => {
    warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    window.happyDOM.setURL('http://localhost/test/cats/prestudy');
    document.body.innerHTML = pageMarkup;
    window.LinguaI18n = { t: (k, p) => (p ? `${k}|${JSON.stringify(p)}` : k), init: () => Promise.resolve() };
    window.scrollTo = () => {};
  });
  afterEach(() => {
    warn.mockRestore();
    delete window.authFetch;
    delete window.LinguaI18n;
  });

  it('loads nothing more at start when the payload carries every drill word', async () => {
    exerciseReply = vi.fn();
    await boot(payload());
    expect(exerciseCalls()).toEqual([]);
    // 1 drill word with exercises: (60 + 5*8 + 2*20 + 40) / 60 = 3 minutes
    expect(document.getElementById('psChips').textContent).toContain('prestudy.minutes|{"n":3}');
  });

  it('"I don\'t know this" fetches the word once and the prime waits for it', async () => {
    const d = deferred();
    exerciseReply = vi.fn(() => d.promise);
    await boot(payload());
    addWord(12);
    await flush();
    expect(exerciseCalls().map((c) => [c.url, c.method]))
      .toEqual([['/api/tests/cats/prestudy/exercises?sense_ids=12', 'GET']]);

    // start the prime while the fetch is in flight: it waits, no second request
    document.getElementById('psNextStep').click();
    await flush();
    expect(document.getElementById('psQBody').textContent).toContain('common.loading');
    expect(document.getElementById('psNextStep').disabled).toBe(true);
    expect(exerciseCalls()).toHaveLength(1);

    d.resolve(ok({ status: 'success', sense_ids: [12], exercises: { 12: [CLOZE('e12', '犬')] } }));
    await flush();
    // 2 words x 5 word stages + 1 ladder exercise each
    expect(header()).toEqual({ words: 2, items: 12 });
    expect(exerciseCalls()).toHaveLength(1);
    expect(calls.every((c) => c.method === 'GET' || c.url.endsWith('/prestudy/session'))).toBe(true);
  });

  it('a failed fetch leaves the added word without exercises, with no crash and no other request', async () => {
    exerciseReply = vi.fn(() => Promise.resolve({ ok: false, status: 503, json: async () => ({}) }));
    await boot(payload());
    addWord(12);
    await flush();
    document.getElementById('psNextStep').click();
    await flush();
    expect(header()).toEqual({ words: 2, items: 11 });
    expect(exerciseCalls()).toHaveLength(1);
    expect(calls.map((c) => c.url).filter((u) => !u.includes('/prestudy/exercises?')))
      .toEqual(['/api/tests/cats/prestudy', '/api/tests/cats/prestudy/session']);
  });

  it('a drill word whose content the payload lacks loads at start', async () => {
    const d = deferred();
    exerciseReply = vi.fn(() => d.promise);
    await boot(payload({ exercises: {} }));
    expect(exerciseCalls().map((c) => c.url)).toEqual(['/api/tests/cats/prestudy/exercises?sense_ids=11']);
    // the estimate reads has_exercises, so it does not wait for the content (2 minutes without it)
    expect(document.getElementById('psChips').textContent).toContain('prestudy.minutes|{"n":3}');
    d.resolve(ok({ exercises: { 11: [CLOZE('e11', '猫')] } }));
    await flush();
    document.getElementById('psNextStep').click();
    await flush();
    expect(header()).toEqual({ words: 1, items: 6 });
    expect(exerciseCalls()).toHaveLength(1);
  });

  it('a payload without has_exercises (older server) never fetches', async () => {
    exerciseReply = vi.fn();
    const data = payload();
    delete data.has_exercises;
    await boot(data);
    addWord(12);
    await flush();
    document.getElementById('psNextStep').click();
    await flush();
    expect(exerciseCalls()).toEqual([]);
    expect(header()).toEqual({ words: 2, items: 11 });
  });
});
