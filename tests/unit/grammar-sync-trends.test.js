/**
 * Grammar-drill progress tracking (ADR-066):
 *   store.js    syncState / mergeRemote (the state the server keeps)
 *   sync.js     the round tally, the unsent-round queue, pull and merge
 *   trends.js   shaping the daily summaries for the progress views
 */
import { describe, it, expect } from 'vitest';
import { createStore, decodeResults, encodeResults } from '../../static/js/grammar/store.js';
import { MAX_QUEUE, QUEUE_KEY, createSync, createTally } from '../../static/js/grammar/sync.js';
import {
  addDays,
  applyRound,
  dayDiff,
  hubSummary,
  linePoints,
  needsWork,
  topicSeries,
  trendOf,
} from '../../static/js/grammar/trends.js';
import { memoryStorage } from './fixtures/grammar.js';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** A server stand-in: answers from `plan` (a function or a fixed result). */
function server(plan = {}) {
  const calls = [];
  const request = async (method, url, body) => {
    calls.push({ method, url, body: body ? JSON.parse(JSON.stringify(body)) : null });
    const p = method === 'POST' ? plan.post : plan.get;
    const res = typeof p === 'function' ? p(body, calls) : p;
    return res || { ok: true, status: 200, data: { status: 'success', recorded: 1 } };
  };
  return { calls, request, posts: () => calls.filter((c) => c.method === 'POST') };
}

function practise(store, slug, n, { ok = true, stage = 1, ms = 1200 } = {}) {
  for (let i = 0; i < n; i++) store.record(slug, { id: `${slug}-01-${i}`, stage, ok, ms });
}

const row = (topic, day, answers, correct, extra = {}) => ({
  topic,
  day,
  answers,
  correct,
  timed: correct,
  ms_sum: correct * 2000,
  stage: 1,
  instant: false,
  sub_misses: {},
  ...extra,
});

describe('store: the state the server keeps', () => {
  it('encodes results as signed ms and reads them back', () => {
    expect(encodeResults([1200, -800, 950])).toBe('1200,-800,950');
    expect(decodeResults('1200,-800,950')).toEqual([1200, -800, 950]);
    expect(encodeResults([])).toBe('');
    expect(decodeResults('')).toEqual([]);
    expect(decodeResults('12;drop')).toEqual([]);
    expect(decodeResults(null)).toEqual([]);
    expect(encodeResults(Array.from({ length: 40 }, (_, k) => k + 1)).split(',')).toHaveLength(30);
  });

  it('syncState is null until something is recorded, then compact and without item boxes', () => {
    const store = createStore(memoryStorage(), 'k', () => 5000);
    expect(store.syncState('le')).toBeNull();
    practise(store, 'le', 2);
    store.record('le', { id: 'le-01-9', stage: 1, ok: false, ms: 700 });
    expect(store.syncState('le')).toEqual({
      u: 1,
      r: ['1200,1200,-700', '', '', ''],
      q: 3,
      e: [0, 0, 0],
      l: 5,
    });
  });

  it('mergeRemote on a new browser takes the server state and starts at the open stage', () => {
    const store = createStore(memoryStorage());
    const changed = store.mergeRemote('le', {
      u: 3,
      r: ['900,-1100', '800', '', ''],
      q: 42,
      e: [10, 8, 5],
      l: 1000,
    });
    expect(changed).toBe(true);
    const view = store.topic('le');
    expect(view.unlocked).toBe(3);
    expect(view.stage).toBe(3);
    expect(view.results[1]).toEqual([900, -1100]);
    expect(view.totals[1]).toEqual([900, 1100]);
    expect(view.seq).toBe(42);
    expect(view.endless).toEqual({ answers: 10, correct: 8, best: 5 });
    expect(store.practised()).toEqual(['le']);
  });

  it('mergeRemote never loses local progress', () => {
    const store = createStore(memoryStorage(), 'k', () => 9_000_000);
    practise(store, 'le', 5);
    store.setStage('le', 1);
    // Older server copy with a higher stage: the stage rises, the results stay.
    expect(
      store.mergeRemote('le', { u: 2, r: ['-5000', '', '', ''], q: 2, e: [0, 0, 0], l: 100 })
    ).toBe(true);
    let view = store.topic('le');
    expect(view.unlocked).toBe(2);
    expect(view.stage).toBe(1);
    expect(view.results[1]).toEqual([1200, 1200, 1200, 1200, 1200]);
    expect(view.seq).toBe(5);
    // Fresher server copy: its results replace the local ones, the stage does not drop.
    store.mergeRemote('le', { u: 1, r: ['700', '', '', ''], q: 9, e: [0, 0, 0], l: 9_999 });
    view = store.topic('le');
    expect(view.unlocked).toBe(2);
    expect(view.results[1]).toEqual([700]);
    expect(view.seq).toBe(9);
    // The same again changes nothing; rubbish is ignored and leaves no empty topic.
    expect(
      store.mergeRemote('le', { u: 1, r: ['700', '', '', ''], q: 9, e: [0, 0, 0], l: 9_999 })
    ).toBe(false);
    expect(store.mergeRemote('ba', null)).toBe(false);
    expect(store.mergeRemote('ba', { u: 1, r: ['', '', '', ''], q: 0, e: [0, 0, 0], l: 0 })).toBe(
      false
    );
    expect(Object.keys(store.dump().t)).toEqual(['le']);
  });
});

describe('sync: the round tally', () => {
  it('counts first answers per topic: right ones timed (capped), misses by sub-point', () => {
    const tally = createTally();
    tally.add('le', { ok: true, ms: 1200, sub: 'a' });
    tally.add('le', { ok: true, ms: 99000, sub: 'a' });
    tally.add('le', { ok: false, ms: 500, sub: 'a' });
    tally.add('le', { ok: false, ms: 500, sub: 'a' });
    tally.add('le', { ok: false, ms: 500, sub: '' });
    expect(tally.add('ba', { ok: true, ms: 0, sub: 'x' })).toBe(1);
    expect(tally.take()).toEqual([
      { topic: 'le', answers: 5, correct: 2, timed: 2, ms_sum: 31200, sub_misses: { a: 2 } },
      { topic: 'ba', answers: 1, correct: 1, timed: 0, ms_sum: 0, sub_misses: {} },
    ]);
    expect(tally.take()).toEqual([]);
  });
});

describe('sync: queue and send', () => {
  function setup(plan, opts = {}) {
    const storage = memoryStorage();
    const store = createStore(memoryStorage(), 'k', () => 7_000_000);
    const srv = server(plan);
    const make = () =>
      createSync({ store, storage, request: srv.request, now: () => 1_800_000_000_000, ...opts });
    return { storage, store, srv, make, sync: make() };
  }
  const queued = (storage) => JSON.parse(storage.getItem(QUEUE_KEY) || '[]');
  const counts = (answers = 3, correct = 2) => [
    { topic: 'le', answers, correct, timed: correct, ms_sum: 2400, sub_misses: { a: 1 } },
  ];

  it('sends a finished round with its key, the stage and the compact state', async () => {
    const { sync, store, srv, storage } = setup();
    practise(store, 'le', 3);
    const sent = await sync.queueRound('round', counts());
    expect(sent).toBe(1);
    const { url, body } = srv.posts()[0];
    expect(url).toBe('/api/grammar-drill/round');
    expect(body.round_key).toMatch(UUID);
    expect(body).toMatchObject({ language_id: 1, mode: 'round', played_at: 1_800_000_000 });
    expect(body.topics).toEqual([
      {
        topic: 'le',
        answers: 3,
        correct: 2,
        timed: 2,
        ms_sum: 2400,
        stage: 1,
        instant: false,
        sub_misses: { a: 1 },
        state: { u: 1, r: ['1200,1200,1200', '', '', ''], q: 3, e: [0, 0, 0], l: 7000 },
      },
    ]);
    expect(queued(storage)).toEqual([]);
    expect(sync.pending()).toBe(0);
  });

  it('sends nothing for an empty tally or an unknown topic', async () => {
    const { sync, srv } = setup({}, { known: (slug) => slug !== 'gone' });
    await sync.queueRound('round', []);
    await sync.queueRound('round', [{ topic: 'le', answers: 0 }]);
    await sync.queueRound('round', [{ topic: 'gone', answers: 3, correct: 3 }]);
    expect(srv.calls).toEqual([]);
  });

  it('keeps an unsent round and sends it again with the same key on the next visit', async () => {
    const { sync, srv, storage, make, store } = setup({
      post: { ok: false, status: 0, data: null },
    });
    practise(store, 'le', 3);
    await sync.queueRound('round', counts());
    expect(queued(storage)).toHaveLength(1);
    const key = queued(storage)[0].k;
    // The server said no: later rounds this visit only queue.
    await sync.queueRound('round', counts());
    expect(srv.posts()).toHaveLength(1);
    expect(queued(storage)).toHaveLength(2);

    // Next visit, server back: both go, oldest first, keys unchanged.
    const srv2 = server();
    const again = createSync({ store, storage, request: srv2.request });
    expect(await again.flush()).toBe(2);
    expect(srv2.posts()[0].body.round_key).toBe(key);
    expect(srv2.posts()[0].body.played_at).toBe(1_800_000_000);
    expect(queued(storage)).toEqual([]);
    expect(make).toBeTypeOf('function');
  });

  it('keeps the round on 503 (tracking not deployed), 429 and 500; drops it on 400', async () => {
    for (const status of [503, 429, 500, 401]) {
      const { sync, storage } = setup({ post: { ok: false, status, data: null } });
      await sync.queueRound('round', counts());
      expect(queued(storage), String(status)).toHaveLength(1);
    }
    const { sync, storage, srv } = setup({
      post: (body, calls) =>
        calls.filter((c) => c.method === 'POST').length === 1
          ? { ok: false, status: 400, data: { error: 'unknown topic' } }
          : { ok: true, status: 200, data: { recorded: 1 } },
    });
    await sync.queueRound('round', counts());
    expect(queued(storage)).toEqual([]);
    // A refusal for good does not stop the rounds behind it.
    await sync.queueRound('mixed', counts());
    expect(srv.posts()).toHaveLength(2);
    expect(queued(storage)).toEqual([]);
  });

  it('never keeps more than MAX_QUEUE unsent rounds and survives a broken queue value', async () => {
    const { sync, storage, make } = setup({ post: { ok: false, status: 0, data: null } });
    for (let i = 0; i < MAX_QUEUE + 5; i++) await sync.queueRound('round', counts());
    expect(queued(storage)).toHaveLength(MAX_QUEUE);
    storage.setItem(QUEUE_KEY, '{not json');
    expect(make().pending()).toBe(0);
    storage.setItem(QUEUE_KEY, '[1, null, {"k":"x"}]');
    expect(make().pending()).toBe(0);
  });

  it('works without storage and with a storage that throws', async () => {
    const store = createStore(memoryStorage());
    const srv = server({
      get: { ok: true, status: 200, data: { today: '2026-11-27', states: {}, daily: [] } },
    });
    const none = createSync({ store, storage: null, request: srv.request });
    expect(await none.queueRound('round', counts())).toBe(0);
    const broken = {
      getItem() {
        throw new Error('blocked');
      },
      setItem() {
        throw new Error('full');
      },
    };
    const sync = createSync({ store, storage: broken, request: srv.request });
    await expect(sync.queueRound('round', counts())).resolves.toBe(0);
    await expect(sync.pull()).resolves.not.toBeNull();
  });
});

describe('sync: pull and merge', () => {
  const progressData = (states = {}, daily = []) => ({
    ok: true,
    status: 200,
    data: { status: 'success', today: '2026-11-27', days: 180, states, daily },
  });

  it('merges the server state and returns the history', async () => {
    const store = createStore(memoryStorage());
    const srv = server({
      get: progressData({ le: { u: 3, r: ['900', '', '', ''], q: 40, e: [0, 0, 0], l: 50 } }, [
        row('le', '2026-11-26', 20, 15),
      ]),
    });
    const sync = createSync({ store, storage: memoryStorage(), request: srv.request });
    expect(sync.progress()).toBeNull();
    const progress = await sync.pull();
    expect(srv.calls[0].url).toBe('/api/grammar-drill/progress?language_id=1&days=180');
    expect(progress.today).toBe('2026-11-27');
    expect(progress.merged).toBe(1);
    expect(progress.daily).toHaveLength(1);
    expect(store.topic('le').unlocked).toBe(3);
    expect(sync.progress()).toBe(progress);
    expect(srv.posts()).toEqual([]);
  });

  it('first sync uploads local progress once, as state only', async () => {
    const store = createStore(memoryStorage(), 'k', () => 3_000_000);
    practise(store, 'le', 4);
    practise(store, 'ba', 2);
    practise(store, 'old-topic', 2);
    const srv = server({
      get: progressData({
        ba: { u: 1, r: ['1200,1200', '', '', ''], q: 2, e: [0, 0, 0], l: 3000 },
      }),
    });
    const storage = memoryStorage();
    const opts = { store, storage, request: srv.request, known: (s) => s !== 'old-topic' };
    await createSync(opts).pull();
    const posts = srv.posts();
    expect(posts).toHaveLength(1);
    expect(posts[0].body.mode).toBe('sync');
    expect(posts[0].body.topics).toEqual([
      {
        topic: 'le',
        answers: 0,
        correct: 0,
        timed: 0,
        ms_sum: 0,
        stage: 1,
        instant: false,
        sub_misses: {},
        state: { u: 1, r: ['1200,1200,1200,1200', '', '', ''], q: 4, e: [0, 0, 0], l: 3000 },
      },
    ]);
    // State only: no daily history is made up.
    expect(posts[0].body.topics.every((t) => t.answers === 0)).toBe(true);
  });

  it('splits a large first upload into calls of ten topics and does not queue it twice', async () => {
    const store = createStore(memoryStorage());
    for (let i = 0; i < 23; i++) practise(store, 't' + String(i).padStart(2, '0'), 1);
    const storage = memoryStorage();
    let fail = true;
    const taken = {};
    const srv = server({
      get: () => progressData(taken),
      post: (body) => {
        if (fail) return { ok: false, status: 500, data: null };
        body.topics.forEach((t) => (taken[t.topic] = t.state));
        return null;
      },
    });
    await createSync({ store, storage, request: srv.request }).pull();
    expect(JSON.parse(storage.getItem(QUEUE_KEY)).map((j) => j.t.length)).toEqual([10, 10, 3]);
    fail = false;
    await createSync({ store, storage, request: srv.request }).pull();
    expect(srv.posts().filter((c) => c.body.mode === 'sync')).toHaveLength(4); // 1 failed + 3 sent
    expect(JSON.parse(storage.getItem(QUEUE_KEY))).toEqual([]);
  });

  it('gives null and merges nothing when the server has no progress to give', async () => {
    for (const get of [
      { ok: false, status: 503, data: { error_code: 'GRAMMAR_TRACKING_UNAVAILABLE' } },
      { ok: false, status: 0, data: null },
      { ok: true, status: 200, data: { status: 'success' } },
    ]) {
      const store = createStore(memoryStorage());
      practise(store, 'le', 3);
      const srv = server({ get });
      const sync = createSync({ store, storage: memoryStorage(), request: srv.request });
      expect(await sync.pull()).toBeNull();
      expect(sync.progress()).toBeNull();
      expect(srv.posts()).toEqual([]);
      expect(store.topic('le').seq).toBe(3);
    }
  });

  it('adds a round the server has just taken to the cached history', async () => {
    const store = createStore(memoryStorage());
    practise(store, 'le', 3);
    const srv = server({
      get: progressData({ le: store.syncState('le') }, [row('le', '2026-11-27', 10, 5)]),
      post: { ok: true, status: 200, data: { recorded: 1, practice_day: '2026-11-27' } },
    });
    const sync = createSync({ store, storage: memoryStorage(), request: srv.request });
    await sync.pull();
    await sync.queueRound('round', [
      { topic: 'le', answers: 4, correct: 3, timed: 3, ms_sum: 3000, sub_misses: { a: 1 } },
    ]);
    expect(sync.progress().daily).toEqual([
      row('le', '2026-11-27', 14, 8, { ms_sum: 13000, sub_misses: { a: 1 } }),
    ]);
  });

  it('the default request makes no call without a token', async () => {
    const store = createStore(memoryStorage());
    practise(store, 'le', 1);
    const sync = createSync({ store, storage: memoryStorage() });
    expect(await sync.pull()).toBeNull();
    expect(await sync.queueRound('round', [{ topic: 'le', answers: 1, correct: 1 }])).toBe(0);
    expect(sync.pending()).toBe(1);
  });
});

describe('trends: shaping the daily summaries', () => {
  it('dayDiff and addDays work on ISO days', () => {
    expect(dayDiff('2026-11-20', '2026-11-27')).toBe(7);
    expect(dayDiff('2026-11-27', '2026-11-20')).toBe(-7);
    expect(dayDiff('2026-02-28', '2026-03-01')).toBe(1);
    expect(addDays('2026-11-27', -29)).toBe('2026-10-29');
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
    expect(addDays('nope', 1)).toBe('');
  });

  it('topicSeries gives one entry per practised day, oldest first, last 30 only', () => {
    const daily = [
      row('le', '2026-11-03', 20, 10),
      row('ba', '2026-11-03', 9, 9),
      row('le', '2026-11-01', 10, 9, { timed: 0, ms_sum: 0 }),
      row('le', '2026-11-03', 20, 20, { ms_sum: 20000 }),
      row('le', '2026-11-04', 0, 0),
    ];
    const series = topicSeries(daily, 'le');
    expect(series.map((d) => d.day)).toEqual(['2026-11-01', '2026-11-03']);
    expect(series[0]).toMatchObject({ answers: 10, acc: 90, secs: null });
    expect(series[1]).toMatchObject({ answers: 40, correct: 30, acc: 75, timed: 30 });
    expect(series[1].secs).toBeCloseTo(40000 / 30 / 1000);
    expect(topicSeries(daily, 'none')).toEqual([]);
    expect(topicSeries(null, 'le')).toEqual([]);
    const many = Array.from({ length: 45 }, (_, k) => row('le', addDays('2026-09-01', k), 5, 5));
    const last = topicSeries(many, 'le');
    expect(last).toHaveLength(30);
    expect(last[0].day).toBe(addDays('2026-09-01', 15));
    expect(topicSeries(many, 'le', { limit: 3 })).toHaveLength(3);
  });

  it('trendOf compares the latest day with the first week', () => {
    const series = topicSeries(
      [
        row('le', '2026-11-01', 10, 5), // first week: 5 + 15 of 30 = 66.7%
        row('le', '2026-11-05', 20, 15),
        row('le', '2026-11-12', 10, 8),
        row('le', '2026-11-20', 20, 19, { ms_sum: 19 * 1000 }),
      ],
      'le'
    );
    const acc = trendOf(series, 'acc');
    expect(acc.values).toHaveLength(4);
    expect(acc.latest).toBe(95);
    expect(acc.versus).toBe('week');
    expect(acc.base).toBeCloseTo(66.67, 1);
    expect(acc.delta).toBeCloseTo(28.33, 1);
    const secs = trendOf(series, 'secs');
    expect(secs.latest).toBe(1);
    expect(secs.base).toBe(2);
    expect(secs.delta).toBe(-1);
  });

  it('trendOf inside the first week compares with the first day; one day has no change', () => {
    const two = topicSeries([row('le', '2026-11-01', 10, 5), row('le', '2026-11-03', 10, 8)], 'le');
    expect(trendOf(two, 'acc')).toMatchObject({ latest: 80, base: 50, delta: 30, versus: 'day' });
    const one = topicSeries([row('le', '2026-11-01', 10, 5)], 'le');
    expect(trendOf(one, 'acc')).toMatchObject({ latest: 50, base: null, delta: null, versus: '' });
    expect(trendOf(one, 'acc').values).toEqual([{ day: '2026-11-01', value: 50 }]);
    expect(trendOf([], 'acc')).toBeNull();
    // No right answer on any day: there is no recall time to show.
    const untimed = topicSeries([row('le', '2026-11-01', 10, 0)], 'le');
    expect(trendOf(untimed, 'secs')).toBeNull();
    // A day without the measure is left out of that measure only.
    const mixed = topicSeries(
      [row('le', '2026-11-01', 10, 0), row('le', '2026-11-02', 10, 5)],
      'le'
    );
    expect(trendOf(mixed, 'secs').values).toHaveLength(1);
    expect(trendOf(mixed, 'acc').values).toHaveLength(2);
  });

  it('needsWork ranks the sub-points missed in the last 14 days', () => {
    const daily = [
      row('le', '2026-11-27', 20, 10, { sub_misses: { a: 2, b: 5 } }),
      row('le', '2026-11-20', 20, 10, { sub_misses: { a: 4, c: 1, d: 1 } }),
      row('le', '2026-11-14', 20, 10, { sub_misses: { c: 3 } }), // day 14: inside
      row('le', '2026-11-13', 20, 10, { sub_misses: { d: 50 } }), // outside
      row('ba', '2026-11-27', 20, 10, { sub_misses: { z: 9 } }),
      row('le', '2026-11-28', 20, 10, { sub_misses: { d: 50 } }), // after "today"
    ];
    expect(needsWork(daily, 'le', { today: '2026-11-27' })).toEqual([
      { key: 'a', misses: 6 },
      { key: 'b', misses: 5 },
      { key: 'c', misses: 4 },
    ]);
    expect(needsWork(daily, 'le', { today: '2026-11-27', top: 1 })).toEqual([
      { key: 'a', misses: 6 },
    ]);
    expect(needsWork([row('le', '2026-11-27', 5, 5)], 'le', { today: '2026-11-27' })).toEqual([]);
    expect(needsWork(null, 'le', { today: '2026-11-27' })).toEqual([]);
  });

  it('hubSummary counts practised days in the last 30, all answers, and builds the strip', () => {
    const daily = [
      row('le', '2026-11-27', 40, 30),
      row('ba', '2026-11-27', 10, 9),
      row('le', '2026-11-20', 10, 9),
      row('le', '2026-10-29', 5, 5), // first day of the window
      row('le', '2026-10-28', 100, 90), // before it: in the total only
    ];
    const sum = hubSummary(daily, { today: '2026-11-27' });
    expect(sum.days).toBe(3);
    expect(sum.answers).toBe(165);
    expect(sum.strip).toHaveLength(30);
    expect(sum.strip[0]).toEqual({ day: '2026-10-29', answers: 5, level: 1 });
    expect(sum.strip[29]).toEqual({ day: '2026-11-27', answers: 50, level: 4 });
    expect(sum.strip[22]).toMatchObject({ day: '2026-11-20', level: 1 });
    expect(sum.strip[28].level).toBe(0);
    expect(sum.max).toBe(50);
    const empty = hubSummary([], { today: '2026-11-27' });
    expect(empty).toMatchObject({ days: 0, answers: 0, max: 0 });
    expect(empty.strip.every((d) => d.level === 0)).toBe(true);
    expect(hubSummary([row('le', '2026-11-27', 3, 3)], {}).strip).toEqual([]);
  });

  it('linePoints places values in the box; one value sits in the middle', () => {
    const { points, d } = linePoints([50, 100, 75], { w: 100, h: 40, pad: 5, min: 50, max: 100 });
    expect(points).toEqual([
      { x: 5, y: 35 },
      { x: 50, y: 5 },
      { x: 95, y: 20 },
    ]);
    expect(d).toBe('M5 35 L50 5 L95 20');
    expect(linePoints([7], { w: 100, h: 40, pad: 5 }).points).toEqual([{ x: 50, y: 20 }]);
    expect(linePoints([3, 3], { w: 100, h: 40, pad: 5 }).points.map((p) => p.y)).toEqual([20, 20]);
    expect(
      linePoints([10, 200], { w: 100, h: 40, pad: 5, min: 50, max: 100 }).points.map((p) => p.y)
    ).toEqual([35, 5]);
    expect(linePoints([], { w: 100, h: 40 })).toEqual({ points: [], d: '' });
  });

  it('applyRound adds a round to its day without touching the original', () => {
    const before = { today: '2026-11-26', daily: [row('le', '2026-11-27', 10, 5)], states: {} };
    const after = applyRound(before, '2026-11-27', [
      {
        topic: 'le',
        answers: 2,
        correct: 1,
        timed: 1,
        ms_sum: 900,
        stage: 2,
        instant: false,
        sub_misses: { a: 1 },
        state: { u: 2 },
      },
      { topic: 'ba', answers: 3, correct: 3, timed: 3, ms_sum: 3000, stage: 1, sub_misses: {} },
      { topic: 'de', answers: 0, state: { u: 1 } },
    ]);
    expect(before.daily[0].answers).toBe(10);
    expect(after.today).toBe('2026-11-27');
    expect(after.daily).toHaveLength(2);
    expect(after.daily[0]).toMatchObject({
      answers: 12,
      correct: 6,
      stage: 2,
      sub_misses: { a: 1 },
    });
    expect(after.daily[1]).toMatchObject({ topic: 'ba', day: '2026-11-27', answers: 3 });
    expect(after.states).toEqual({ le: { u: 2 }, de: { u: 1 } });
    expect(applyRound(null, '2026-11-27', [])).toBeNull();
  });
});
