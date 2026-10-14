/**
 * Unit tests for static/js/session/tail.js — the optional end-of-session tail.
 * Imported directly (it is an ES module, unlike the classic-script helpers).
 */

import { describe, it, expect } from 'vitest';
import {
  tailCounts,
  hasTail,
  tailPromptKey,
  governorKey,
  countKey,
  normalizeTailItems,
  appendTailRound,
  requiredProgress,
} from '../../static/js/session/tail.js';

const tail = (reviews, words) => ({
  reviews_left_items: reviews,
  reviews_left_minutes: reviews / 3,
  new_words_left: words,
  new_words_left_minutes: words * 3,
});
const tq = [
  { kind: 'practice', id: 'tail_maint_0', mode: 'maintenance', minutes: 2 },
  { kind: 'practice', id: 'tail_acq_0', mode: 'acquisition', minutes: 10 },
];

describe('tailCounts / tailPromptKey', () => {
  it('reads reviews and words from the tail', () => {
    expect(tailCounts(tail(6, 4))).toEqual({ reviews: 6, words: 4 });
    expect(tailCounts(null)).toEqual({ reviews: 0, words: 0 });
    expect(tailCounts({ reviews_left_items: -2, new_words_left: 'x' })).toEqual({
      reviews: 0,
      words: 0,
    });
  });

  it('picks the prompt variant by which counts are non-zero', () => {
    expect(tailPromptKey(tail(6, 4))).toBe('session.tail.prompt');
    expect(tailPromptKey(tail(6, 0))).toBe('session.tail.prompt_reviews_only');
    expect(tailPromptKey(tail(0, 4))).toBe('session.tail.prompt_words_only');
    expect(tailPromptKey(tail(0, 0))).toBeNull();
    expect(tailPromptKey(null)).toBeNull();
  });
});

describe('hasTail', () => {
  it('needs counts AND runnable chunks', () => {
    expect(hasTail({ tail: tail(6, 4), tail_queue: tq })).toBe(true);
    expect(hasTail({ tail: tail(6, 4), tail_queue: [] })).toBe(false);
    expect(hasTail({ tail: tail(6, 4) })).toBe(false);
    expect(hasTail({ tail: tail(0, 0), tail_queue: tq })).toBe(false);
    expect(hasTail({ tail: null, tail_queue: [] })).toBe(false);
    expect(hasTail(null)).toBe(false);
  });
});

describe('governorKey / countKey', () => {
  it('maps governor levels', () => {
    expect(governorKey({ level: 'paused' })).toBe('session.governor.paused');
    expect(governorKey({ level: 'reduced' })).toBe('session.governor.reduced');
    expect(governorKey({ level: 'normal' })).toBeNull();
    expect(governorKey(undefined)).toBeNull();
  });

  it('uses the _one variant only for exactly 1', () => {
    expect(countKey('reviews', 1)).toBe('session.tail.reviews_count_one');
    expect(countKey('words', 1)).toBe('session.tail.words_count_one');
    expect(countKey('reviews', 0)).toBe('session.tail.reviews_count');
    expect(countKey('words', 24)).toBe('session.tail.words_count');
  });
});

describe('tail items never block completion', () => {
  it('normalizeTailItems marks every item optional and incomplete', () => {
    const items = normalizeTailItems([
      { id: 'tail_acq_0', mode: 'acquisition', is_completed: true },
    ]);
    expect(items[0]).toMatchObject({
      kind: 'practice',
      is_bonus: true,
      is_tail: true,
      is_completed: false,
    });
  });

  it('requiredProgress ignores tail items, complete or not', () => {
    const queue = [
      { id: 'a', kind: 'test', is_completed: true },
      { id: 'b', kind: 'practice', is_completed: true },
      { id: 'tail_maint_0', kind: 'practice', is_tail: true, is_completed: false },
      { id: 'tail_acq_0', kind: 'practice', is_tail: true, is_completed: true },
    ];
    expect(requiredProgress(queue)).toEqual({ done: 2, total: 2 });
  });

  it('requiredProgress copes with an empty queue', () => {
    expect(requiredProgress([])).toEqual({ done: 0, total: 0 });
    expect(requiredProgress(undefined)).toEqual({ done: 0, total: 0 });
  });
});

describe('appendTailRound', () => {
  const base = [
    { id: 'a', kind: 'test', is_completed: true },
    { id: 'b', kind: 'practice', is_completed: true },
  ];

  it('appends the round after the required items and points at its first item', () => {
    const { queue, firstIndex } = appendTailRound(base, tq);
    expect(queue.map((q) => q.id)).toEqual(['a', 'b', 'tail_maint_0', 'tail_acq_0']);
    expect(firstIndex).toBe(2);
    expect(queue.slice(2).every((q) => q.is_tail && !q.is_completed)).toBe(true);
  });

  it('keeps completed tail items as history and replaces skipped ones', () => {
    const afterRound = [
      ...base,
      { id: 'tail_maint_0', kind: 'practice', is_tail: true, is_completed: true },
      { id: 'tail_acq_0', kind: 'practice', is_tail: true, is_completed: false, skipped: true },
    ];
    const next = [{ kind: 'practice', id: 'tail_acq_0', mode: 'acquisition', minutes: 10 }];
    const { queue, firstIndex } = appendTailRound(afterRound, next);
    expect(queue.map((q) => q.id)).toEqual(['a', 'b', 'tail_maint_0', 'tail_acq_0']);
    expect(queue[3].skipped).toBeUndefined();
    expect(firstIndex).toBe(3);
  });

  it('does not mutate the input queue', () => {
    const copy = JSON.stringify(base);
    appendTailRound(base, tq);
    expect(JSON.stringify(base)).toBe(copy);
  });
});
