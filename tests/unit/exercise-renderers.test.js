/**
 * Unit tests for static/js/exercise-renderers.js
 *
 * ExRenderers is an IIFE that exposes its public API via window.ExRenderers
 * (set at the end of the file).  The setup.js file evals it into jsdom.
 *
 * Covered: escHtml, shuffleArr, fmtType — the pure utilities.
 * dispatch routing is covered with a minimal card stub.
 * DOM-heavy renderers (mcq, cloze, etc.) are not individually unit-tested;
 * they are exercise-level integration concerns covered by Playwright E2E.
 */

import { describe, it, expect, beforeEach } from 'vitest';

const R = () => window.ExRenderers;

// ---------------------------------------------------------------------------
// escHtml — delegates to LinguaUtils.escapeHtml when available
// ---------------------------------------------------------------------------

describe('escHtml', () => {
  it('escapes angle brackets', () => {
    expect(R().escHtml('<b>bold</b>')).toBe('&lt;b&gt;bold&lt;/b&gt;');
  });

  it('escapes & character', () => {
    expect(R().escHtml('a & b')).toBe('a &amp; b');
  });

  it('returns empty string for falsy input', () => {
    expect(R().escHtml('')).toBe('');
    expect(R().escHtml(null)).toBe('');
    expect(R().escHtml(undefined)).toBe('');
  });

  it('delegates to window.LinguaUtils.escapeHtml (same result as canonical impl)', () => {
    const payload = '<script>alert("xss")</script>';
    expect(R().escHtml(payload)).toBe(window.LinguaUtils.escapeHtml(payload));
  });
});

// ---------------------------------------------------------------------------
// shuffleArr — returns a permutation; does not mutate the input
// ---------------------------------------------------------------------------

describe('shuffleArr', () => {
  it('returns an array of the same length', () => {
    const arr = [1, 2, 3, 4, 5];
    expect(R().shuffleArr(arr)).toHaveLength(arr.length);
  });

  it('contains exactly the same elements', () => {
    const arr = ['a', 'b', 'c', 'd'];
    const result = R().shuffleArr(arr);
    expect(result.sort()).toEqual([...arr].sort());
  });

  it('does not mutate the original array', () => {
    const arr = [10, 20, 30];
    const copy = [...arr];
    R().shuffleArr(arr);
    expect(arr).toEqual(copy);
  });

  it('handles an empty array', () => {
    expect(R().shuffleArr([])).toEqual([]);
  });

  it('handles a single-element array', () => {
    expect(R().shuffleArr(['only'])).toEqual(['only']);
  });
});

// ---------------------------------------------------------------------------
// fmtType — converts snake_case exercise type to Title Case
// (LinguaI18n is not available in tests, so the fallback path runs)
// ---------------------------------------------------------------------------

describe('fmtType', () => {
  it.each([
    ['cloze_completion', 'Cloze Completion'],
    ['odd_one_out', 'Odd One Out'],
    ['tl_nl_translation', 'Tl Nl Translation'],
    ['collocation_gap_fill', 'Collocation Gap Fill'],
    ['jumbled_sentence', 'Jumbled Sentence'],
  ])('formats %s → %s', (type, expected) => {
    expect(R().fmtType(type)).toBe(expected);
  });

  it('leaves a single word unchanged except capitalisation', () => {
    expect(R().fmtType('cloze')).toBe('Cloze');
  });
});

// ---------------------------------------------------------------------------
// dispatch — routes to correct renderer based on exercise type
// ---------------------------------------------------------------------------

describe('dispatch routing', () => {
  let card;

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);

    // Minimal stubs — dispatch requires init() to be called first
    R().init({
      cardEl: card,
      isAnswered: () => false,
      setAnswered: () => {},
      showFeedback: () => {},
      submitAttempt: () => {},
      nextExercise: () => {},
    });
  });

  afterEach(() => {
    card.remove();
  });

  it('renders something into the card for a cloze_completion exercise', () => {
    R().dispatch(
      'cloze_completion',
      {},
      {
        sentence_with_blank: 'I ___ to the store.',
        options: ['went', 'go', 'gone'],
        correct_answer: 'went',
        explanation: 'Past tense.',
      },
      ''
    );
    expect(card.innerHTML).not.toBe('');
    expect(card.innerHTML).toContain('option');
  });

  it('renders something for odd_one_out', () => {
    // renderOddOneOut reads c.items (array) and c.odd_index (number)
    R().dispatch(
      'odd_one_out',
      {},
      {
        items: ['apple', 'banana', 'car', 'orange'],
        odd_index: 2,
        explanation: 'Not a fruit.',
      },
      ''
    );
    expect(card.innerHTML).not.toBe('');
    expect(card.innerHTML).toContain('apple');
  });

  it('falls back to generic renderer for unknown exercise type', () => {
    // renderGeneric reads ex.exercise_type — pass it to avoid a crash
    expect(() => {
      R().dispatch('nonexistent_type', { exercise_type: 'nonexistent_type' }, {}, '');
    }).not.toThrow();
  });
});
