import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, it, expect, beforeAll } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
let W;

const T = (key, p) =>
  key === 'study_plan.studied.progress'
    ? `Studied this week: ${p.done} / ${p.target} min`
    : key === 'study_plan.studied.progress_no_target'
      ? `Studied this week: ${p.done} min`
      : key === 'study_plan.studied.minutes'
        ? `${p.n} min`
        : key;

const fixture = {
  week_start_date: '2026-10-12',
  studied_seconds: 2040,
  studied_minutes: 34,
  target_minutes: 210,
  by_kind: {
    test: { seconds: 900, minutes: 15 },
    practice: { seconds: 600, minutes: 10 },
    flashcard: { seconds: 300, minutes: 5 },
    dual_translation: { seconds: 240, minutes: 4 },
    drill: { seconds: 0, minutes: 0 },
  },
};

beforeAll(() => {
  // eslint-disable-next-line no-eval
  eval(readFileSync(join(here, '..', '..', 'static/js/weekly-study.js'), 'utf8'));
  W = window.WeeklyStudy;
});

describe('WeeklyStudy.buildModel', () => {
  it('builds progress and non-zero kinds', () => {
    const m = W.buildModel(fixture);
    expect(m.done).toBe(34);
    expect(m.target).toBe(210);
    expect(m.pct).toBe(16);
    expect(m.kinds.map((k) => k.kind)).toEqual(['test', 'practice', 'flashcard', 'dual_translation']);
  });
  it('handles null target, null/garbage input, caps pct at 100', () => {
    expect(W.buildModel({ ...fixture, target_minutes: null }).pct).toBeNull();
    expect(W.buildModel(null)).toBeNull();
    expect(W.buildModel('x')).toBeNull();
    expect(W.buildModel({ ...fixture, target_minutes: 10 }).pct).toBe(100);
    expect(W.buildModel({ studied_minutes: 'abc' }).done).toBe(0);
  });
});

describe('WeeklyStudy.render', () => {
  it('shows "Studied this week: 34 / 210 min" with breakdown', () => {
    const c = document.createElement('div');
    W.render(c, fixture, T);
    expect(c.hidden).toBe(false);
    expect(c.querySelector('#weeklyStudiedTitle').textContent).toBe('Studied this week: 34 / 210 min');
    expect(c.querySelectorAll('li').length).toBe(4);
    expect(c.querySelector('.progress-bar').style.width).toBe('16%');
  });
  it('renders without a target (no bar)', () => {
    const c = document.createElement('div');
    W.render(c, { ...fixture, target_minutes: null }, T);
    expect(c.querySelector('#weeklyStudiedTitle').textContent).toBe('Studied this week: 34 min');
    expect(c.querySelector('.progress-bar')).toBeNull();
  });
  it('hides when weekly_study is null and shows empty state when all zero', () => {
    const c = document.createElement('div');
    W.render(c, null, T);
    expect(c.hidden).toBe(true);
    expect(c.textContent).toBe('');
    W.render(c, { studied_minutes: 0, target_minutes: 60, by_kind: {} }, T);
    expect(c.hidden).toBe(false);
    expect(c.textContent).toContain('study_plan.studied.empty');
  });
  it('uses textContent (no HTML injection)', () => {
    const c = document.createElement('div');
    W.render(c, fixture, () => '<img src=x>');
    expect(c.querySelector('img')).toBeNull();
  });
});
