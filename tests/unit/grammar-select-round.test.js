/**
 * static/js/grammar/select.js + round.js: which items a round holds (unseen
 * first, missed ones kept a share, then least recently seen; sub-points
 * balanced; the stage's types; levels), the topic to
 * continue with, and the round queue that brings a missed item back until it
 * is answered right.
 */
import { describe, it, expect } from 'vitest';
import {
  itemClass,
  mixedTopics,
  pickMixed,
  pickRound,
  recommendTopic,
} from '../../static/js/grammar/select.js';
import { createRound } from '../../static/js/grammar/round.js';
import { createStore } from '../../static/js/grammar/store.js';
import { makeItems, memoryStorage, seeded } from './fixtures/grammar.js';

const fresh = () => createStore(memoryStorage());

describe('pickRound', () => {
  it('gives 20 items of the stage types, level 1 first, sub-points balanced', () => {
    const items = makeItems('le', 240);
    const store = fresh();
    const round = pickRound({
      items,
      slug: 'le',
      topic: store.topic('le'),
      stage: 1,
      rng: seeded(3),
    });
    expect(round).toHaveLength(20);
    expect(new Set(round.map((i) => i.id)).size).toBe(20);
    expect(round.every((i) => i.type === 'cloze' || i.type === 'judge')).toBe(true);
    // makeItems ties lvl to sub (k % 3): level 1 only means sub 'a' only here.
    expect(round.every((i) => i.lvl === 1)).toBe(true);
  });

  it('balances sub-points when the level allows', () => {
    const items = makeItems('le', 240).map((it) => ({ ...it, lvl: 1 }));
    const round = pickRound({
      items,
      slug: 'le',
      topic: fresh().topic('le'),
      stage: 1,
      rng: seeded(5),
    });
    const bySub = { a: 0, b: 0, c: 0 };
    round.forEach((i) => (bySub[i.sub] += 1));
    expect(
      Math.max(...Object.values(bySub)) - Math.min(...Object.values(bySub))
    ).toBeLessThanOrEqual(1);
  });

  it('falls back to higher levels rather than a short round', () => {
    const items = makeItems('le', 30, ['cloze']);
    const round = pickRound({
      items,
      slug: 'le',
      topic: fresh().topic('le'),
      stage: 1,
      rng: seeded(1),
    });
    expect(round).toHaveLength(20);
    expect(round.filter((i) => i.lvl === 1)).toHaveLength(10);
  });

  it('fills half a Build round with order / rewrite and most of Recall with cloze', () => {
    const items = makeItems('le', 400).map((it) => ({ ...it, lvl: 1 }));
    const topic = fresh().topic('le');
    const build = pickRound({ items, slug: 'le', topic, stage: 2, rng: seeded(2) });
    const tiles = build.filter((i) => i.type === 'order' || i.type === 'rewrite').length;
    expect(tiles).toBeGreaterThanOrEqual(10);
    expect(tiles).toBeLessThan(20);
    const recall = pickRound({ items, slug: 'le', topic, stage: 3, rng: seeded(2) });
    expect(recall.filter((i) => i.type === 'cloze').length).toBeGreaterThanOrEqual(12);
  });

  it('prefers unseen items, keeps a share for missed ones, then the least recently seen', () => {
    const items = makeItems('le', 60, ['cloze']).map((it) => ({ ...it, lvl: 1 }));
    const store = fresh();
    // 30 seen: the first 8 missed, the next 22 right.
    items.slice(0, 30).forEach((it, k) => {
      store.record('le', { id: it.id, stage: 1, ok: k >= 8, ms: 1000 });
    });
    const topic = store.topic('le');
    expect(itemClass(items[0], 'le', topic, 3)).toBe(1);
    expect(itemClass(items[40], 'le', topic, 3)).toBe(0);
    const round = pickRound({ items, slug: 'le', topic, stage: 1, rng: seeded(7) });
    const ids = new Set(round.map((i) => i.id));
    const missed = items.slice(0, 8).filter((i) => ids.has(i.id)).length;
    const unseen = items.slice(30).filter((i) => ids.has(i.id)).length;
    expect(missed).toBe(6); // 30% of 20
    expect(unseen).toBe(14);

    // Everything seen and right: the round is the least recently seen items.
    const all = fresh();
    items.forEach((it) => all.record('le', { id: it.id, stage: 1, ok: true, ms: 1000 }));
    const oldest = pickRound({
      items,
      slug: 'le',
      topic: all.topic('le'),
      stage: 1,
      rng: seeded(7),
    });
    // Sub-points take turns, so the cut is within one turn of the 20 oldest.
    const rank = (i) => items.findIndex((x) => x.id === i.id);
    expect(Math.max(...oldest.map(rank))).toBeLessThanOrEqual(21);
  });

  it('returns what there is when the topic is small, and nothing for no items', () => {
    const items = makeItems('le', 6, ['cloze']);
    expect(pickRound({ items, slug: 'le', topic: fresh().topic('le'), stage: 1 })).toHaveLength(6);
    expect(pickRound({ items: [], slug: 'le', topic: fresh().topic('le'), stage: 1 })).toEqual([]);
  });
});

describe('hub choices', () => {
  const topics = [
    { slug: 'le', count: 100 },
    { slug: 'guo', count: 100 },
    { slug: 'tone-sandhi', count: 0 },
  ];

  it('recommends the first topic with items, then the most recent one', () => {
    let clock = 1000;
    const store = createStore(memoryStorage(), undefined, () => clock);
    expect(recommendTopic(topics, store).slug).toBe('le');
    expect(recommendTopic([topics[2], topics[1]], store).slug).toBe('guo');
    store.record('le', { id: 'le-01-001', stage: 1, ok: true, ms: 1000 });
    clock += 5000;
    store.record('guo', { id: 'guo-01-001', stage: 1, ok: true, ms: 1000 });
    expect(recommendTopic(topics, store).slug).toBe('guo');
    expect(recommendTopic([], store)).toBeNull();
  });

  it('mixes only practised topics that have items', () => {
    const store = fresh();
    expect(mixedTopics(topics, store)).toEqual([]);
    store.record('guo', { id: 'guo-01-001', stage: 1, ok: true, ms: 1000 });
    store.recordEndless('tone-sandhi', true, 1);
    expect(mixedTopics(topics, store).map((t) => t.slug)).toEqual(['guo']);
  });

  it('spreads a mixed round over its topics', () => {
    const store = fresh();
    const parts = ['le', 'guo', 'zhe'].map((slug) => ({
      slug,
      items: makeItems(slug, 60).map((it) => ({ ...it, lvl: 1 })),
      topic: store.topic(slug),
    }));
    const round = pickMixed(parts, 20, seeded(4));
    expect(round).toHaveLength(20);
    const count = (slug) => round.filter((e) => e.slug === slug).length;
    expect([count('le'), count('guo'), count('zhe')].sort()).toEqual([6, 7, 7]);
    expect(round.every((e) => e.item.id.startsWith(e.slug + '-'))).toBe(true);
  });
});

describe('createRound', () => {
  it('brings a missed item back three items later until it is answered right', () => {
    const round = createRound(['a', 'b', 'c', 'd', 'e', 'f']);
    const seen = [];
    const play = (ok) => {
      seen.push(round.current().entry + (round.current().retry ? '*' : ''));
      round.answer(ok, 1000);
      round.next();
    };
    play(false); // a missed
    play(true); // b
    play(true); // c
    play(true); // d
    play(false); // a* missed again
    play(true); // e
    play(true); // f
    play(true); // a* (end of queue)
    expect(seen).toEqual(['a', 'b', 'c', 'd', 'a*', 'e', 'f', 'a*']);
    expect(round.current()).toBeNull();
    const sum = round.summary();
    expect(sum).toMatchObject({ answers: 6, correct: 5, missed: ['a'] });
    expect(sum.accuracy).toBeCloseTo(5 / 6);
  });

  it('returns a miss at the end when fewer than three items are left', () => {
    const round = createRound(['a', 'b']);
    round.answer(false, 500);
    expect(round.next().entry).toBe('b');
    round.answer(true, 500);
    expect(round.next()).toMatchObject({ entry: 'a', retry: true });
    round.answer(true, 500);
    expect(round.next()).toBeNull();
  });

  it('counts only first answers, ignores a second answer and tracks progress', () => {
    const round = createRound(['a', 'b', 'c']);
    expect(round.progress()).toEqual({ done: 0, total: 3 });
    expect(round.answer(true, 1000)).toEqual({ first: true });
    expect(round.answer(false, 1)).toEqual({ first: false }); // already answered
    expect(round.isAnswered()).toBe(true);
    expect(round.progress()).toEqual({ done: 1, total: 3 });
    round.next();
    round.answer(false, 3000);
    expect(round.progress()).toEqual({ done: 1, total: 3 });
    round.next();
    round.answer(true, 2000);
    round.next();
    expect(round.answer(true, 9000)).toEqual({ first: false }); // b again: a retry
    expect(round.next()).toBeNull();
    expect(round.summary()).toMatchObject({ answers: 3, correct: 2, medianMs: 2000 });
    expect(round.progress()).toEqual({ done: 3, total: 3 });
  });

  it('does not move on before an answer', () => {
    const round = createRound(['a', 'b']);
    expect(round.next().entry).toBe('a');
  });

  it('spaces a miss in endless mode too', () => {
    let n = 0;
    const round = createRound([], { more: () => 'g' + ++n });
    const seen = [];
    for (let k = 0; k < 6; k++) {
      seen.push(round.current().entry + (round.current().retry ? '*' : ''));
      round.answer(k !== 0, 1000);
      round.next();
    }
    expect(seen).toEqual(['g1', 'g2', 'g3', 'g4', 'g1*', 'g5']);
  });

  it('never ends in endless mode and keeps the streak', () => {
    let n = 0;
    const round = createRound([], { more: () => 'g' + ++n });
    expect(round.isEndless()).toBe(true);
    for (let k = 0; k < 7; k++) {
      expect(round.current()).not.toBeNull();
      round.answer(k !== 3, 1000);
      round.next();
    }
    expect(round.streak()).toBe(3);
    expect(round.summary()).toMatchObject({ answers: 7, correct: 6, best: 3 });
  });
});
