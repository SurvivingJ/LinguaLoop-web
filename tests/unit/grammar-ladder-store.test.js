/**
 * static/js/grammar/ladder.js + store.js: the four-stage ladder (unlock at 85%
 * over the last 30 answers of a stage, "instant" at stage 4 with 90% and a
 * median under 3 s), the speed countdown, and the localStorage progress store.
 */
import { describe, it, expect } from 'vitest';
import {
  SPEED_MIN_MS,
  SPEED_START_MS,
  STAGES,
  encodeResult,
  isInstant,
  levelCap,
  nextSpeedBase,
  speedLimit,
  stageDef,
  stageStats,
  topicStatus,
  unlocksNext,
} from '../../static/js/grammar/ladder.js';
import { KEY, createStore, itemKey } from '../../static/js/grammar/store.js';
import { memoryStorage, ORDER, CLOZE } from './fixtures/grammar.js';

const results = (right, wrong, ms = 2000) => [
  ...Array.from({ length: wrong }, () => encodeResult(false, ms)),
  ...Array.from({ length: right }, () => encodeResult(true, ms)),
];

function answer(store, slug, stage, n, ok, ms = 2000, from = 0) {
  let unlocked = 0;
  for (let k = 0; k < n; k++) {
    const id = `${slug}-01-${String(from + k + 1).padStart(3, '0')}`;
    unlocked = store.record(slug, { id, stage, ok, ms }).unlocked || unlocked;
  }
  return unlocked;
}

describe('ladder', () => {
  it('has four stages with the types each drills', () => {
    expect(STAGES.map((s) => s.key)).toEqual(['recognise', 'build', 'recall', 'speed']);
    expect(stageDef(1).types).toEqual(['cloze', 'judge']);
    expect(stageDef(2).types).toEqual(expect.arrayContaining(['order', 'rewrite']));
    expect(stageDef(3).recall).toBe(true);
    expect(stageDef(4).timed).toBe(true);
    expect(stageDef(9).n).toBe(4);
    expect(stageDef(0).n).toBe(1);
  });

  it('summarises encoded results', () => {
    const s = stageStats([encodeResult(true, 1000), encodeResult(false, 3000), 2000]);
    expect(s).toMatchObject({ n: 3, correct: 2, medianMs: 2000 });
    expect(s.acc).toBeCloseTo(2 / 3);
  });

  it('unlocks at 85% over a full window of 30', () => {
    expect(unlocksNext(results(29, 0))).toBe(false); // not 30 yet
    expect(unlocksNext(results(26, 4))).toBe(true); // 86.7%
    expect(unlocksNext(results(25, 5))).toBe(false); // 83.3%
    // Only the last 30 count.
    expect(unlocksNext([...results(0, 20), ...results(30, 0)])).toBe(true);
  });

  it('is instant only at stage 4 with 90% and a median under 3 s', () => {
    const topic = (unlocked, r4) => ({ unlocked, results: { 1: [], 2: [], 3: [], 4: r4 } });
    expect(isInstant(topic(4, results(27, 3, 2500)))).toBe(true);
    expect(isInstant(topic(4, results(26, 4, 2500)))).toBe(false);
    expect(isInstant(topic(4, results(30, 0, 3000)))).toBe(false);
    expect(isInstant(topic(4, results(20, 0, 1000)))).toBe(false);
    expect(isInstant(topic(3, results(30, 0, 1000)))).toBe(false);
  });

  it('opens higher item levels as accuracy holds', () => {
    const topic = (r1) => ({ results: { 1: r1, 2: [], 3: [], 4: [] } });
    expect(levelCap(topic([]))).toBe(1);
    expect(levelCap(topic(results(9, 0)))).toBe(1);
    expect(levelCap(topic(results(8, 2)))).toBe(2);
    expect(levelCap(topic(results(6, 4)))).toBe(1);
    expect(levelCap(topic(results(27, 3)))).toBe(3);
    expect(levelCap(topic(results(23, 7)))).toBe(2);
  });

  it('times tile items longer and tightens the countdown on a streak', () => {
    expect(speedLimit(8000, CLOZE)).toBe(8000);
    expect(speedLimit(8000, ORDER)).toBe(8000 + 6 * 1200);
    expect(speedLimit(0, CLOZE)).toBe(SPEED_START_MS);
    expect(nextSpeedBase(8000, true, 4)).toBe(8000);
    expect(nextSpeedBase(8000, true, 5)).toBe(7500);
    expect(nextSpeedBase(SPEED_MIN_MS, true, 10)).toBe(SPEED_MIN_MS);
    expect(nextSpeedBase(6000, false, 0)).toBe(6500);
    expect(nextSpeedBase(8000, false, 0)).toBe(8000);
  });
});

describe('store', () => {
  it('keys items by the id suffix and never stores generated items', () => {
    expect(itemKey('le', 'le-03-017')).toBe('03-017');
    expect(itemKey('word-order', 'word-order-01-020')).toBe('01-020');
    expect(itemKey('le', 'gen:clock')).toBe('');
  });

  it('starts empty, with pinyin and typing off', () => {
    const store = createStore(memoryStorage());
    expect(store.settings()).toEqual({ pinyin: false, typing: false });
    expect(store.topic('le')).toMatchObject({ stage: 1, unlocked: 1, seq: 0, answers: 0 });
    expect(topicStatus(store.topic('le'))).toBe('new');
    expect(store.practised()).toEqual([]);
  });

  it('persists settings and results under one key', () => {
    const storage = memoryStorage();
    const store = createStore(storage);
    store.setSetting('pinyin', true);
    store.record('le', { id: 'le-01-001', stage: 1, ok: true, ms: 1800 });
    store.record('le', { id: 'le-01-002', stage: 1, ok: false, ms: 4000 });
    const saved = JSON.parse(storage.data[KEY]);
    expect(saved.v).toBe(1);
    expect(saved.s.py).toBe(1);
    expect(saved.t.le.r[0]).toEqual([1800, -4000]);
    expect(saved.t.le.i).toEqual({ '01-001': [1, 1], '01-002': [0, 2] });

    const again = createStore(storage);
    expect(again.settings().pinyin).toBe(true);
    expect(again.topic('le').results[1]).toEqual([1800, -4000]);
    expect(topicStatus(again.topic('le'))).toBe('recognise');
  });

  it('keeps the total time beside the recall time', () => {
    const storage = memoryStorage();
    const store = createStore(storage);
    store.record('le', { id: 'le-01-001', stage: 3, ok: true, ms: 1200, totalMs: 2600 });
    store.record('le', { id: 'le-01-002', stage: 3, ok: false, ms: 900 });
    expect(store.topic('le').results[3]).toEqual([1200, -900]);
    expect(store.topic('le').totals[3]).toEqual([2600, 900]);
    // Progress saved before totals existed still loads.
    const old = JSON.parse(storage.data[KEY]);
    delete old.t.le.w;
    const again = createStore(memoryStorage({ [KEY]: JSON.stringify(old) }));
    expect(again.topic('le').totals[3]).toEqual([]);
    again.record('le', { id: 'le-01-003', stage: 3, ok: true, ms: 700, totalMs: 1500 });
    expect(again.topic('le').totals[3]).toEqual([1500]);
  });

  it('moves an item up a box when right and back to box 0 when missed', () => {
    const store = createStore(memoryStorage());
    const rec = (ok) => store.record('le', { id: 'le-01-001', stage: 1, ok, ms: 1000 });
    rec(true);
    rec(true);
    expect(store.topic('le').items['01-001'][0]).toBe(2);
    rec(false);
    expect(store.topic('le').items['01-001']).toEqual([0, 3]);
    for (let k = 0; k < 9; k++) rec(true);
    expect(store.topic('le').items['01-001'][0]).toBe(5);
  });

  it('keeps the last 30 results of a stage and unlocks the next at 85%', () => {
    const store = createStore(memoryStorage());
    expect(answer(store, 'le', 1, 4, false)).toBe(0);
    expect(answer(store, 'le', 1, 25, true, 2000, 4)).toBe(0); // 29 answers
    expect(answer(store, 'le', 1, 1, true, 2000, 29)).toBe(2); // 26 / 30
    const view = store.topic('le');
    expect(view.unlocked).toBe(2);
    expect(view.stage).toBe(1); // the learner chooses when to move up
    expect(view.results[1]).toHaveLength(30);
    answer(store, 'le', 1, 10, true, 2000, 30);
    expect(store.topic('le').results[1]).toHaveLength(30);
  });

  it('lets the learner pick any unlocked stage and no other', () => {
    const store = createStore(memoryStorage());
    expect(store.setStage('le', 3)).toBe(1);
    answer(store, 'le', 1, 30, true);
    expect(store.setStage('le', 2)).toBe(2);
    expect(store.setStage('le', 4)).toBe(2);
    expect(store.setStage('le', 1)).toBe(1);
  });

  it('does not unlock from an earlier stage or feed stage results in mixed review', () => {
    const store = createStore(memoryStorage());
    answer(store, 'le', 1, 30, true);
    answer(store, 'le', 1, 30, true); // already unlocked: still stage 2
    expect(store.topic('le').unlocked).toBe(2);
    store.record('le', { id: 'le-01-001', stage: null, ok: false, ms: 900 });
    expect(store.topic('le').results[1]).toHaveLength(30);
    expect(store.topic('le').items['01-001'][0]).toBe(0);
  });

  it('reaches instant through the four stages', () => {
    const store = createStore(memoryStorage());
    for (const stage of [1, 2, 3]) {
      expect(answer(store, 'le', stage, 30, true)).toBe(stage + 1);
      store.setStage('le', stage + 1);
    }
    answer(store, 'le', 4, 30, true, 2400);
    expect(topicStatus(store.topic('le'))).toBe('instant');
  });

  it('lists practised topics most recent first and tracks endless totals', () => {
    let clock = 1000000;
    const store = createStore(memoryStorage(), KEY, () => clock);
    store.record('le', { id: 'le-01-001', stage: 1, ok: true, ms: 1000 });
    clock += 60000;
    store.recordEndless('tone-sandhi', true, 1);
    store.recordEndless('tone-sandhi', false, 0);
    store.recordEndless('tone-sandhi', true, 1);
    expect(store.practised()).toEqual(['tone-sandhi', 'le']);
    expect(store.topic('tone-sandhi').endless).toEqual({ answers: 3, correct: 2, best: 1 });
    expect(topicStatus(store.topic('tone-sandhi'))).not.toBe('new');
  });

  it('survives broken or blocked storage', () => {
    const broken = createStore(memoryStorage({ [KEY]: '{not json' }));
    expect(broken.topic('le').stage).toBe(1);
    const blocked = createStore({
      getItem() {
        throw new Error('denied');
      },
      setItem() {
        throw new Error('denied');
      },
    });
    blocked.record('le', { id: 'le-01-001', stage: 1, ok: true, ms: 1000 });
    expect(blocked.topic('le').seq).toBe(1);
    const none = createStore(null);
    none.setSetting('typing', true);
    expect(none.settings().typing).toBe(true);
  });
});
