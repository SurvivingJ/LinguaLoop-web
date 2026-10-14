/**
 * Unit tests for static/js/study-plan-settings.js (TASK-868).
 *
 * The helper is a classic <script> that assigns window.StudyPlanSettings, so it
 * is eval'd here (same approach as tests/unit/setup.js) rather than imported.
 * It mirrors services/study_plan_service.py (new_words_for_day,
 * new_words_week_target, effective_new_words): the .5-tie rows below are the
 * same grid the Python/SQL side is pinned on.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, it, expect, beforeAll } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
let S;

beforeAll(() => {
  eval(readFileSync(join(here, '..', '..', 'static/js/study-plan-settings.js'), 'utf8'));
  S = window.StudyPlanSettings;
});

describe('newWordsForDay (mirror of new_words_for_day)', () => {
  it('is 0 for a zero/negative weight or a zero quota', () => {
    expect(S.newWordsForDay(5, 0)).toBe(0);
    expect(S.newWordsForDay(5, -1)).toBe(0);
    expect(S.newWordsForDay(0, 1.4)).toBe(0);
    expect(S.newWordsForDay(5, null)).toBe(0);
  });

  it('rounds half up, not to even', () => {
    expect(S.newWordsForDay(5, 1)).toBe(5);
    expect(S.newWordsForDay(5, 0.5)).toBe(3); // 2.5 -> 3 (banker's would give 2)
    expect(S.newWordsForDay(1, 0.5)).toBe(1); // 0.5 -> 1 (banker's would give 0)
    expect(S.newWordsForDay(5, 1.5)).toBe(8); // 7.5 -> 8
    expect(S.newWordsForDay(5, 1.4)).toBe(7);
  });
});

describe('newWordsWeekTarget', () => {
  it('is 7 x per-day for the default (all-ones) shape', () => {
    expect(S.newWordsWeekTarget(5, [1, 1, 1, 1, 1, 1, 1])).toBe(35);
    expect(S.newWordsWeekTarget(5, undefined)).toBe(35);
    expect(S.newWordsWeekTarget(5, [])).toBe(35);
  });

  it('gives rest days 0 and active days a scaled quota', () => {
    const fiveDay = [1.4, 1.4, 1.4, 1.4, 1.4, 0, 0];
    expect(S.newWordsWeekTarget(5, fiveDay)).toBe(35); // 5 x round(7.0)
    expect(S.newWordsWeekTarget(0, fiveDay)).toBe(0);
  });
});

describe('effectiveNewWords (governor)', () => {
  it('normal / reduced / paused', () => {
    expect(S.effectiveNewWords(5, 'normal')).toBe(5);
    expect(S.effectiveNewWords(5, 'reduced')).toBe(2);
    expect(S.effectiveNewWords(1, 'reduced')).toBe(0);
    expect(S.effectiveNewWords(5, 'paused')).toBe(0);
    expect(S.effectiveNewWords(5, undefined)).toBe(5);
  });
});

describe('forecastMinutes', () => {
  const forecast = { reviews_per_new_word_30d: 7, item_seconds: 20 };

  it('5 words a day at 20 s each -> about 12 min/day (11.67)', () => {
    expect(S.forecastMinutes(5, [1, 1, 1, 1, 1, 1, 1], forecast)).toBe(12);
  });

  it('uses the server constants, never hard-coded ones', () => {
    expect(
      S.forecastMinutes(5, undefined, { reviews_per_new_word_30d: 14, item_seconds: 30 })
    ).toBe(35);
  });

  it('is 0 with no forecast payload or no new words', () => {
    expect(S.forecastMinutes(5, undefined, null)).toBe(0);
    expect(S.forecastMinutes(0, undefined, forecast)).toBe(0);
  });
});

describe('clampNewWords', () => {
  it('clamps to 0..50 and falls back on NaN', () => {
    expect(S.clampNewWords('7')).toBe(7);
    expect(S.clampNewWords(-3)).toBe(0);
    expect(S.clampNewWords(99)).toBe(50);
    expect(S.clampNewWords('abc')).toBe(0);
    expect(S.clampNewWords('abc', 5)).toBe(5);
    expect(S.clampNewWords('', null)).toBeNull();
  });
});

describe('moduleState (last-toggle lock)', () => {
  const available = ['reading', 'listening', 'flashcards', 'practice'];

  it('locks the only checked module while new words are 0', () => {
    const { locks } = S.moduleState(available, new Set(['reading']), 0, 'tests_and_review');
    expect(locks.reading).toBe('last_one');
    expect(locks.listening).toBeNull();
  });

  it('new words > 0 count as an included module: nothing is locked', () => {
    const { locks } = S.moduleState(available, new Set(['reading']), 5, 'tests_and_review');
    expect(Object.values(locks).every((v) => v === null)).toBe(true);
  });

  it('locks the last NON-review module under tests_only (API would 400)', () => {
    const { locks } = S.moduleState(available, new Set(['reading', 'practice']), 5, 'tests_only');
    expect(locks.reading).toBe('last_test');
    expect(locks.practice).toBeNull();
  });

  it('flashcards-only hint', () => {
    expect(
      S.moduleState(available, new Set(['flashcards']), 0, 'tests_and_review').flashcardsOnly
    ).toBe(true);
    expect(
      S.moduleState(available, new Set(['flashcards']), 3, 'tests_and_review').flashcardsOnly
    ).toBe(false);
    expect(
      S.moduleState(available, new Set(['flashcards', 'reading']), 0, 'tests_and_review')
        .flashcardsOnly
    ).toBe(false);
  });
});

describe('testsOnlyDisabled / includedSet', () => {
  it('is disabled only when no test or surface module is on', () => {
    expect(S.testsOnlyDisabled(new Set(['practice']))).toBe(true);
    expect(S.testsOnlyDisabled(new Set())).toBe(true);
    expect(S.testsOnlyDisabled(new Set(['practice', 'flashcards']))).toBe(false);
  });

  it('includedSet is available minus excluded', () => {
    expect([...S.includedSet(['a', 'b', 'c'], ['b'])]).toEqual(['a', 'c']);
    expect([...S.includedSet(['a'], null)]).toEqual(['a']);
  });
});

describe('computeCard', () => {
  const base = {
    daily: 30,
    scope: 'tests_and_review',
    practiceIncluded: true,
    newWordsPerDay: 5,
    shape: [1, 1, 1, 1, 1, 1, 1],
    minutesPerNewWord: 3,
    typicalDay: { practice_room_min_per_day: 7, review_min_per_day: 4 },
    governor: { level: 'normal' },
    forecast: { reviews_per_new_word_30d: 7, item_seconds: 20 },
  };

  it('splits the quota into in-session words and an optional tail', () => {
    const c = S.computeCard(base); // room 7 min / 3 min = 2 words
    expect(c.mode).toBe('in_budget');
    expect(c.inBudgetWords).toBe(2);
    expect(c.tailWords).toBe(3);
    expect(c.tailMinutes).toBe(9);
    expect(c.fit).toBe(2);
    expect(c.after).toBe(3);
    expect(c.estimate).toBe('split');
    expect(c.forecastMin).toBe(12);
  });

  it('never fits more than the quota', () => {
    const c = S.computeCard({ ...base, newWordsPerDay: 1 });
    expect(c.inBudgetWords).toBe(1);
    expect(c.tailWords).toBe(0);
  });

  it('tests_only puts every new word in the tail', () => {
    const c = S.computeCard({ ...base, scope: 'tests_only' });
    expect(c.mode).toBe('tail_only');
    expect(c.inBudgetWords).toBe(0);
    expect(c.tailWords).toBe(5);
    expect(c.fit).toBe(0);
    expect(c.after).toBe(5);
  });

  it('Vocabulary review off also puts every new word in the tail and warns', () => {
    const c = S.computeCard({ ...base, practiceIncluded: false });
    expect(c.mode).toBe('tail_only');
    expect(c.tailWords).toBe(5);
    expect(c.noReviewWarning).toBe(true);
  });

  it('warns only when review is off AND new words > 0', () => {
    expect(
      S.computeCard({ ...base, practiceIncluded: false, newWordsPerDay: 0 }).noReviewWarning
    ).toBe(false);
    expect(S.computeCard({ ...base, scope: 'tests_only' }).noReviewWarning).toBe(false);
    expect(S.computeCard(base).noReviewWarning).toBe(false);
  });

  it('applies the governor to the estimate line but not to the typical-day split', () => {
    const reduced = S.computeCard({ ...base, governor: { level: 'reduced' } });
    expect(reduced.effective).toBe(2);
    expect(reduced.fit).toBe(2);
    expect(reduced.after).toBe(0);
    expect(reduced.governorKey).toBe('reduced');
    expect(reduced.inBudgetWords).toBe(2);

    const paused = S.computeCard({ ...base, governor: { level: 'paused' } });
    expect(paused.estimate).toBe('paused');
    expect(paused.governorKey).toBe('paused');
  });

  it('0 new words reads as off, whatever the governor says', () => {
    const c = S.computeCard({ ...base, newWordsPerDay: 0, governor: { level: 'paused' } });
    expect(c.estimate).toBe('off');
    expect(c.forecastMin).toBe(0);
  });

  it('no current week: no typical-day summary and no in-session words', () => {
    const c = S.computeCard({ ...base, typicalDay: null });
    expect(c.hasTypicalDay).toBe(false);
    expect(c.inBudgetWords).toBe(0);
    expect(S.typicalDaySummary(c, 30, true)).toBeNull();
  });
});

describe('typicalDaySummary / hintDescriptor', () => {
  const base = {
    daily: 30,
    scope: 'tests_and_review',
    practiceIncluded: true,
    newWordsPerDay: 5,
    shape: undefined,
    minutesPerNewWord: 3,
    typicalDay: { practice_room_min_per_day: 7, review_min_per_day: 4 },
    governor: { level: 'normal' },
    forecast: { reviews_per_new_word_30d: 7, item_seconds: 20 },
  };

  it('tests_and_review: in-session sentence plus the optional-round sentence', () => {
    const s = S.typicalDaySummary(S.computeCard(base), 30, true);
    expect(s.key).toBe('typical_day');
    expect(s.params).toEqual({ daily: 30, words: 2, review: 4 });
    expect(s.tail).toEqual({ key: 'typical_day_tail', params: { words: 3, minutes: 9 } });
  });

  it('omits the optional-round sentence when everything fits', () => {
    const s = S.typicalDaySummary(S.computeCard({ ...base, newWordsPerDay: 2 }), 30, true);
    expect(s.tail).toBeNull();
  });

  it('tests_only: review and new words are both optional', () => {
    const s = S.typicalDaySummary(S.computeCard({ ...base, scope: 'tests_only' }), 30, true);
    expect(s.key).toBe('typical_day_tests_only');
    expect(s.params).toEqual({ daily: 30, review: 4, words: 5, minutes: 15 });
  });

  it('review excluded: the review clause is omitted', () => {
    const c = S.computeCard({ ...base, practiceIncluded: false });
    expect(S.typicalDaySummary(c, 30, false).key).toBe('typical_day_tests_only_no_review');
  });

  it('tests_only with 0 new words keeps just the review clause (or nothing)', () => {
    const c = S.computeCard({ ...base, scope: 'tests_only', newWordsPerDay: 0 });
    expect(S.typicalDaySummary(c, 30, true).key).toBe('typical_day_tests_only_no_words');
    const none = S.computeCard({ ...base, practiceIncluded: false, newWordsPerDay: 0 });
    expect(S.typicalDaySummary(none, 30, false).key).toBe('typical_day_tests_only_none');
  });

  it('hint: in-budget count vs tail-only', () => {
    expect(S.hintDescriptor(S.computeCard(base), 30)).toEqual({
      key: 'hint_in_budget',
      params: { words: 2, daily: 30 },
    });
    expect(S.hintDescriptor(S.computeCard({ ...base, scope: 'tests_only' }), 30).key).toBe(
      'hint_tail_only'
    );
  });
});

describe('governorMessageKey', () => {
  it('maps levels, null for normal', () => {
    expect(S.governorMessageKey({ level: 'paused' })).toBe('paused');
    expect(S.governorMessageKey({ level: 'reduced' })).toBe('reduced');
    expect(S.governorMessageKey({ level: 'normal' })).toBeNull();
    expect(S.governorMessageKey(null)).toBeNull();
  });
});
