/**
 * Practice tells the learner how many exercises a round holds before it
 * starts: the start card loads the round (static/js/session/controller.js
 * showPracticeCount) and the practice player reuses that payload.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  mount,
  practiceSessionUrl,
  summarizePracticePayload,
  practiceCountText,
} from '../../static/js/session/players/practice.js';

const t = (key, params, fallback) => fallback;

describe('summarizePracticePayload', () => {
  it('counts items and adds their expected seconds', () => {
    const s = summarizePracticePayload({
      items: [{ expected_seconds: 30 }, { expected_seconds: 60 }, {}],
    });
    expect(s).toEqual({ exercises: 3, newWords: 0, drillReviews: 0, minutes: 2 }); // 30 + 60 + 30 s
  });

  it('counts drill words by stage and adds the drill estimate', () => {
    const s = summarizePracticePayload({
      items: [{ expected_seconds: 30 }],
      intro_drill: { words: [{ stage: 1 }, { stage: 1 }, { stage: 2 }, { stage: 4 }, {}], est_minutes: 5 },
    });
    expect(s).toEqual({ exercises: 1, newWords: 3, drillReviews: 2, minutes: 6 });
  });

  it('leaves DT error cards out when their renderer is not loaded', () => {
    const saved = window.DTErrorCard;
    delete window.DTErrorCard;
    try {
      const s = summarizePracticePayload({ items: [{ is_error_exercise: true }, {}] });
      expect(s.exercises).toBe(1);
      window.DTErrorCard = {};
      expect(summarizePracticePayload({ items: [{ is_error_exercise: true }, {}] }).exercises).toBe(2);
    } finally {
      window.DTErrorCard = saved;
    }
  });

  it('is empty for an empty round', () => {
    expect(summarizePracticePayload({ items: [] })).toEqual({ exercises: 0, newWords: 0, drillReviews: 0, minutes: 0 });
    expect(summarizePracticePayload(null)).toEqual({ exercises: 0, newWords: 0, drillReviews: 0, minutes: 0 });
  });
});

describe('practiceCountText', () => {
  it('says exercises and minutes', () => {
    expect(practiceCountText({ exercises: 12, newWords: 0, minutes: 6 }, 0, t)).toBe(
      '12 exercises · about 6 min'
    );
  });

  it('uses the singular forms', () => {
    expect(practiceCountText({ exercises: 1, newWords: 1, minutes: 1 }, 1, t)).toBe(
      '1 exercise · 1 new word to learn · about 1 min · then 1 more round'
    );
  });

  it('mentions the rounds that follow', () => {
    expect(practiceCountText({ exercises: 3, newWords: 4, drillReviews: 13, minutes: 8 }, 2, t)).toBe(
      '3 exercises · 4 new words to learn · 13 words to review · about 8 min · then 2 more rounds'
    );
    expect(practiceCountText({ exercises: 0, newWords: 0, drillReviews: 1, minutes: 1 }, 0, t)).toBe(
      '1 word to review · about 1 min'
    );
  });

  it('says when there is nothing to do', () => {
    expect(practiceCountText({ exercises: 0, newWords: 0, minutes: 0 }, 0, t)).toBe(
      'Nothing to practise right now'
    );
    expect(practiceCountText({ exercises: 0, newWords: 0, minutes: 0 }, 1, t)).toBe('');
  });
});

describe('practiceSessionUrl', () => {
  it('builds the chunk URL, tail flag included', () => {
    expect(practiceSessionUrl({ mode: 'maintenance', minutes: 3 }, 1)).toBe(
      '/api/practice/session?mode=maintenance&minutes=3&language_id=1'
    );
    expect(practiceSessionUrl({ mode: 'acquisition', minutes: 5, is_tail: true }, 3)).toBe(
      '/api/practice/session?mode=acquisition&minutes=5&language_id=3&tail=1'
    );
  });
});

describe('practice player and a prefetched round', () => {
  let realER;
  let fetchMock;
  const flush = () => new Promise((r) => setTimeout(r, 0));

  beforeEach(() => {
    realER = window.ExRenderers;
    window.ExRenderers = {
      init: () => {},
      dispatch: vi.fn(),
      escHtml: (s) => String(s),
      shuffleArr: (a) => a.slice(),
    };
    fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ items: [{ exercise_id: 'x' }] }) }));
    window.authFetch = fetchMock;
  });

  afterEach(() => {
    window.ExRenderers = realER;
    delete window.authFetch;
  });

  it('uses the prefetched payload once instead of loading again', async () => {
    const item = {
      kind: 'practice',
      mode: 'maintenance',
      minutes: 3,
      prefetch: Promise.resolve({ ok: true, data: { items: [{ exercise_id: 'pre' }] } }),
    };
    mount(document.createElement('div'), { item, languageId: 1 });
    await flush();
    await flush();
    expect(fetchMock.mock.calls.filter((c) => String(c[0]).startsWith('/api/practice/session'))).toEqual([]);
    expect(window.ExRenderers.dispatch.mock.calls[0][1].exercise_id).toBe('pre');
    expect('prefetch' in item).toBe(false);
  });

  it('loads normally when the prefetch failed', async () => {
    const item = { kind: 'practice', mode: 'maintenance', minutes: 3, prefetch: Promise.resolve({ ok: false, data: {} }) };
    mount(document.createElement('div'), { item, languageId: 1 });
    await flush();
    await flush();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/practice/session?mode=maintenance&minutes=3&language_id=1');
  });
});
