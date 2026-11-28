// Idiom trainer engine: the ladder of one idiom, the round plan, the question
// builder and the progress store (static/js/idioms/*).
import { describe, it, expect } from 'vitest';
import * as L from '../../static/js/idioms/ladder.js';
import { build, distractors } from '../../static/js/idioms/questions.js';
import { createStore, idOf, toServerState, topicOf } from '../../static/js/idioms/store.js';

const DAY = 86400000;
const seeded = (seed) => () => {
  seed = (seed * 1664525 + 1013904223) % 4294967296;
  return seed / 4294967296;
};

const TAGS = ['effort', 'failure', 'joy', 'anger', 'speech', 'luck', 'caution', 'haste'];
const card = (n, over = {}) => ({
  id: `cy${String(n).padStart(3, '0')}`,
  t: `成语${n}甲乙`,
  r: 'chéng yǔ',
  mean: `meaning number ${n}`,
  lvl: 1,
  tag: TAGS[n % TAGS.length],
  set: 'chengyu',
  lit: `literal ${n}`,
  story: null,
  use: { reg: 'neutral', tone: 'neutral', how: 'as a predicate' },
  near: [],
  parts: [`成语${n}`, `甲乙${n}`],
  cue: `a situation that calls for idiom ${n}`,
  ctx: [0, 1, 2, 3, 4, 5].map((i) => ({
    s: `情况${i}里他{成语${n}甲乙}了。`,
    en: `context ${i} of ${n}`,
  })),
  bad: [0, 1].map((i) => ({
    s: `错误${i}的{成语${n}甲乙}。`,
    en: `meant ${i}`,
    why: `wrong because ${i}`,
  })),
  ...over,
});
const POOL = Array.from({ length: 24 }, (_, n) => card(n + 1));

describe('idiom ladder', () => {
  it('two right answers in a row move an idiom up one step', () => {
    let s = L.newState();
    let r = L.record(s, true, 1000);
    expect(r.event).toBeNull();
    expect(r.state).toMatchObject({ l: 1, k: 1, n: 1, c: 1 });
    r = L.record(r.state, true, 2000);
    expect(r.event).toBe('up');
    expect(r.state).toMatchObject({ l: 2, k: 0, hi: 2 });
    // a wrong answer resets the run and keeps the step
    r = L.record(r.state, true, 3000);
    r = L.record(r.state, false, 4000);
    expect(r.state).toMatchObject({ l: 2, k: 0, n: 4, c: 3 });
    expect(r.event).toBeNull();
  });

  it('ten right answers master an idiom and schedule the first review a day later', () => {
    let s = L.newState();
    let event = null;
    for (let i = 0; i < 10; i++) ({ state: s, event } = L.record(s, true, 1000 + i));
    expect(event).toBe('mastered');
    expect(s.l).toBe(L.MASTERED);
    expect(s.due).toBe(1009 + DAY);
    expect(L.isMastered(s)).toBe(true);
    expect(L.isDue(s, 1009 + DAY)).toBe(true);
    expect(L.isDue(s, 1009 + DAY - 1)).toBe(false);
  });

  it('reviews stretch out, and a failed review goes back to step 4', () => {
    let s = { ...L.newState(), l: L.MASTERED, iv: 0, due: 0, n: 10, c: 10, hi: 6 };
    const gaps = [];
    for (let i = 0; i < 8; i++) {
      const r = L.record(s, true, 0);
      expect(r.event).toBe('kept');
      gaps.push(r.state.due / DAY);
      s = r.state;
    }
    expect(gaps).toEqual([3, 7, 14, 30, 60, 120, 120, 120]);
    const fail = L.record(s, false, 5);
    expect(fail.event).toBe('down');
    expect(fail.state).toMatchObject({ l: 4, k: 0, iv: 0, due: null, hi: 6 });
  });

  it('each step has its own kind of question', () => {
    expect([1, 2, 3, 4, 5, 6].map(L.modeFor)).toEqual([
      'meet',
      'recognise',
      'complete',
      'judge',
      'recall',
      'review',
    ]);
  });

  it('plans a round: reviews, idioms in progress, then new ones; each learned idiom twice, never back to back', () => {
    const states = {
      cy001: { ...L.newState(), l: L.MASTERED, due: 10, n: 12, last: 5 }, // due
      cy002: { ...L.newState(), l: L.MASTERED, due: 10 ** 15, n: 12, last: 5 }, // not due
      cy003: { ...L.newState(), l: 3, n: 5, last: 20 },
      cy004: { ...L.newState(), l: 2, n: 3, last: 10 },
    };
    const q = L.planRound(POOL, states, { now: 100, size: 12, active: 5 });
    expect(q).toContain('cy001');
    expect(q).not.toContain('cy002');
    expect(q.filter((id) => id === 'cy001')).toHaveLength(1);
    // oldest in progress first, then new idioms in list order
    expect(q.slice(0, 5)).toEqual(['cy004', 'cy003', 'cy005', 'cy006', 'cy007']);
    for (const id of ['cy003', 'cy004', 'cy005', 'cy006', 'cy007'])
      expect(q.filter((x) => x === id)).toHaveLength(2);
    for (let i = 1; i < q.length; i++) expect(q[i]).not.toBe(q[i - 1]);
    expect(q).toHaveLength(11);
  });

  it('a round respects the chosen sets and a new learner starts at the top of the list', () => {
    const mixed = [...POOL.slice(0, 3), { ...card(90), set: 'suyu' }];
    expect(L.planRound(mixed, {}, { now: 1, sets: ['suyu'] })).toEqual(['cy090', 'cy090']);
    expect(L.planRound(POOL, {}, { now: 1 }).slice(0, 5)).toEqual([
      'cy001',
      'cy002',
      'cy003',
      'cy004',
      'cy005',
    ]);
    expect(L.planRound([], {}, { now: 1 })).toEqual([]);
  });

  it('summary and merge', () => {
    const states = {
      cy001: { ...L.newState(), l: 6, due: 0, n: 9 },
      cy002: { ...L.newState(), l: 2, n: 2 },
    };
    expect(L.summary(POOL, states, 5)).toEqual({ learning: 1, mastered: 1, due: 1, fresh: 22 });
    const merged = L.mergeStates(
      { a: { n: 3, last: 1 }, b: { n: 2, last: 9 } },
      { a: { n: 5, last: 0 }, b: { n: 2, last: 3 }, c: { n: 1 } }
    );
    expect(merged).toEqual({ a: { n: 5, last: 0 }, b: { n: 2, last: 9 }, c: { n: 1 } });
  });
});

describe('idiom questions', () => {
  const c = POOL[4];

  it('meet: the idiom is shown in context and its meaning is chosen among other meanings', () => {
    const q = build(c, 'meet', POOL, seeded(3));
    expect(q.prompt.blank).toBe(false);
    expect(q.prompt.sentence).toContain(`{${c.t}}`);
    expect(q.options).toHaveLength(4);
    expect(q.options[q.answer]).toBe(c.mean);
    expect(new Set(q.options).size).toBe(4);
    expect([0, 1]).toContain(q.ctx);
  });

  it('recognise: a later context with the idiom hidden; four idioms', () => {
    const q = build(c, 'recognise', POOL, seeded(4));
    expect(q.prompt.blank).toBe(true);
    expect(q.prompt.en).toMatch(/^context/);
    expect(q.options[q.answer]).toBe(c.t);
    expect(q.options).toHaveLength(4);
    expect(q.ctx).toBeGreaterThanOrEqual(1);
  });

  it('never offers an idiom of the same theme or a listed look-alike', () => {
    const near = POOL[5];
    const withNear = { ...c, near: [{ t: near.t, diff: 'x' }] };
    for (let seed = 1; seed < 60; seed++) {
      const got = distractors(withNear, POOL, 5, seeded(seed));
      expect(got).toHaveLength(5);
      for (const o of got) {
        expect(o.tag).not.toBe(c.tag);
        expect(o.t).not.toBe(near.t);
        expect(o.id).not.toBe(c.id);
      }
    }
  });

  it('a small pool still gives enough options', () => {
    const tiny = POOL.slice(0, 5).map((x) => ({ ...x, tag: 'effort' }));
    expect(distractors(tiny[0], tiny, 3, seeded(1))).toHaveLength(3);
  });

  it('shows a context the idiom was not just seen in', () => {
    const rng = seeded(9);
    for (let i = 0; i < 30; i++) expect(build(c, 'recognise', POOL, rng, [1, 2, 3, 4]).ctx).toBe(5);
    expect([1, 2, 3, 4, 5]).toContain(build(c, 'recognise', POOL, rng, [1, 2, 3, 4, 5]).ctx);
  });

  it('complete: the meaning and the first half; the second half is chosen', () => {
    const q = build(c, 'complete', POOL, seeded(5));
    expect(q.prompt).toEqual({ text: c.mean, stem: c.parts[0] });
    expect(q.options[q.answer]).toBe(c.parts[1]);
    expect(q.options).toHaveLength(4);
  });

  it('judge: a good context is right, a misuse is wrong and explains why', () => {
    const seen = { right: 0, wrong: 0 };
    const rng = seeded(6);
    for (let i = 0; i < 80; i++) {
      const q = build(c, 'judge', POOL, rng);
      expect(q.options).toEqual(['right', 'wrong']);
      if (q.answer === 0) {
        seen.right += 1;
        expect(c.ctx.map((x) => x.s)).toContain(q.prompt.sentence);
        expect(q.after.why).toBeUndefined();
      } else {
        seen.wrong += 1;
        expect(c.bad.map((x) => x.s)).toContain(q.prompt.sentence);
        expect(q.after.why).toMatch(/^wrong because/);
      }
    }
    expect(seen.right).toBeGreaterThan(20);
    expect(seen.wrong).toBeGreaterThan(20);
  });

  it('recall and review', () => {
    const recall = build(c, 'recall', POOL, seeded(7));
    expect(recall.prompt).toEqual({ text: c.cue });
    expect(recall.options).toHaveLength(6);
    expect(recall.options[recall.answer]).toBe(c.t);
    const review = build(c, 'review', POOL, seeded(8));
    expect(review.prompt.blank).toBe(true);
    expect(review.options[review.answer]).toBe(c.t);
  });
});

describe('idiom progress store', () => {
  const memory = () => {
    const data = {};
    return {
      getItem: (k) => (k in data ? data[k] : null),
      setItem: (k, v) => (data[k] = String(v)),
      data,
    };
  };
  const api = (server = { status: 200, states: {} }) => {
    const calls = [];
    const fetcher = async (url, opts) => {
      calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
      const ok = server.status >= 200 && server.status < 300;
      return { ok, status: server.status, json: async () => ({ states: server.states }) };
    };
    return { calls, fetcher };
  };

  it('an idiom is the tracking topic idiom-<id>', () => {
    expect(topicOf('cy001')).toBe('idiom-cy001');
    expect(idOf('idiom-ky120')).toBe('ky120');
    expect(idOf('wa-topic')).toBeNull();
    expect(
      toServerState({ ...L.newState(), l: 4, k: 1, n: 7, c: 6, last: 1700000000999, hi: 6 })
    ).toEqual({
      u: 6,
      l: 1700000000,
      s: { l: 4, k: 1, n: 7, c: 6, due: null, iv: 0, last: 1700000000999 },
    });
  });

  it('keeps each language apart and sends one request per finished round', async () => {
    const storage = memory();
    const { calls, fetcher } = api();
    const zh = createStore({
      lang: 'zh',
      languageId: 1,
      storage,
      fetcher,
      now: () => 1700000100000,
    });
    let s = L.record(L.newState(), true, 1700000000000).state;
    zh.answer('cy001', s, { correct: true, ms: 2100 });
    s = L.record(s, true, 1700000001000).state;
    zh.answer('cy001', s, { correct: true, ms: 99999 });
    expect(calls).toHaveLength(0);
    await zh.endRound();
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('/api/grammar-drill/round');
    expect(calls[0].body).toMatchObject({ language_id: 1, mode: 'round', played_at: 1700000100 });
    expect(calls[0].body.topics).toEqual([
      {
        topic: 'idiom-cy001',
        answers: 2,
        correct: 2,
        timed: 2,
        ms_sum: 32100,
        stage: 2,
        instant: false,
        sub_misses: {},
        state: toServerState(s),
      },
    ]);
    expect(Object.keys(storage.data)).toContain('ld_idioms_zh_v1');
    const ja = createStore({ lang: 'ja', languageId: 3, storage, fetcher });
    expect(ja.state('cy001')).toBeUndefined();
    expect(createStore({ lang: 'zh', languageId: 1, storage, fetcher }).state('cy001').l).toBe(2);
  });

  it('queues while tracking is unavailable and merges the account on pull', async () => {
    const storage = memory();
    const down = api({ status: 503, states: {} });
    const a = createStore({ lang: 'ja', languageId: 3, storage, fetcher: down.fetcher });
    a.answer('ky001', { ...L.newState(), n: 1, c: 1, k: 1, last: 5 }, { correct: true, ms: 10 });
    await a.endRound();
    expect(a.queued).toBe(1);
    const remote = toServerState({ ...L.newState(), l: 5, n: 30, c: 28, last: 9000, hi: 5 });
    const up = api({
      status: 200,
      states: { 'idiom-ky001': remote, 'wa-topic': { u: 3, l: 1, s: { l: 3 } } },
    });
    const b = createStore({ lang: 'ja', languageId: 3, storage, fetcher: up.fetcher });
    b.answer('ky002', { ...L.newState(), n: 2, c: 2, l: 2, last: 7 }, { correct: true, ms: 10 });
    await b.pull();
    await b.endRound();
    expect(b.state('ky001')).toMatchObject({ l: 5, n: 30, hi: 5 }); // the account had more answers
    expect(b.state('wa-topic')).toBeUndefined(); // other drills' topics are not idioms
    const modes = up.calls.filter((c) => c.body).map((c) => c.body.mode);
    expect(modes).toContain('sync');
    const sync = up.calls.find((c) => c.body && c.body.mode === 'sync');
    expect(sync.body.topics.map((t) => t.topic)).toEqual(['idiom-ky002']);
    expect(b.queued).toBe(0);
  });
});
