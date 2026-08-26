/**
 * Unit tests for static/js/dt-error-card.js (TASK-731).
 *
 * DTErrorCard is an IIFE that exposes its API via window.DTErrorCard;
 * tests/unit/setup.js evals it into happy-dom, same as ExRenderers.
 *
 * The two things that would silently corrupt data if wrong, and so are pinned
 * hardest here:
 *   1. The answer target is always `prompt_payload.answer` (built from
 *      corrected_form). Rendering `learner_form` would drill the mistake.
 *   2. Grading goes to POST /api/dual-translation/cards/<id>/review — never to
 *      /api/practice/attempt, which is sense-keyed and would corrupt the
 *      recurrence metric this feature exists to measure.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

const D = () => window.DTErrorCard;

const CLOZE = {
  card_id: 101,
  card_type: 'cloze',
  subtype: 'article_omission',
  prompt_payload: { prompt: 'The ____ sat on the mat.', answer: 'the cat' },
  state: 'new',
  due_date: null,
};

const ISOLATE = {
  card_id: 102,
  card_type: 'isolate_retranslate',
  subtype: 'tense',
  prompt_payload: {
    l1_context: 'El gato se sentó en la alfombra.',
    target_sentence: 'The cat sat on the mat.',
    answer: 'the cat',
  },
  state: 'new',
  due_date: null,
};

let el;

beforeEach(() => {
  document.body.innerHTML = '<div id="host"></div>';
  el = document.getElementById('host');
  delete window.showToast;
});

// ---------------------------------------------------------------------------
// Answer target — the pedagogically critical invariant
// ---------------------------------------------------------------------------

describe('answer target', () => {
  it('reads the answer from prompt_payload.answer for cloze', () => {
    expect(D().answerOf(CLOZE)).toBe('the cat');
  });

  it('reads the answer from prompt_payload.answer for isolate_retranslate', () => {
    expect(D().answerOf(ISOLATE)).toBe('the cat');
  });

  it('never surfaces learner_form even when a payload smuggles one in', () => {
    // The backend guarantees learner_form is absent; if a future payload ever
    // carried it, the renderer must still answer with `answer`.
    const contaminated = {
      ...CLOZE,
      prompt_payload: { ...CLOZE.prompt_payload, learner_form: 'cat' },
    };
    expect(D().answerOf(contaminated)).toBe('the cat');
    expect(D().revealHTML(contaminated, null)).not.toContain('learner_form');
  });

  it('degrades to an empty string rather than undefined', () => {
    expect(D().answerOf({ prompt_payload: {} })).toBe('');
    expect(D().answerOf(null)).toBe('');
  });

  it('does not leak the answer into the prompt phase', () => {
    // The whole point of a recall card: the answer must not be on screen
    // before the learner asks for it.
    D().mount(el, CLOZE, {});
    expect(el.innerHTML).toContain('The ____ sat on the mat.');
    expect(el.textContent).not.toContain('the cat');
  });

  it('does not leak the target sentence for isolate cards before reveal', () => {
    D().mount(el, ISOLATE, {});
    expect(el.textContent).toContain('El gato se sentó en la alfombra.');
    expect(el.textContent).not.toContain('The cat sat on the mat.');
  });
});

// ---------------------------------------------------------------------------
// Grade submission target
// ---------------------------------------------------------------------------

describe('grade submission target', () => {
  it('builds the dual-translation review URL', () => {
    expect(D().reviewUrl(101)).toBe('/api/dual-translation/cards/101/review');
  });

  it('never targets the practice attempt endpoint', () => {
    expect(D().reviewUrl(101)).not.toContain('/api/practice');
  });

  it('POSTs the rating to the review endpoint, not to practice/attempt', async () => {
    const authFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'success', next_due: '2026-08-25', new_state: 'review' }),
    });
    const onDone = vi.fn();

    D().mount(el, CLOZE, { authFetch, onDone });
    el.querySelector('[data-dtec-check]').click();
    el.querySelector('[data-dtec-rating="3"]').click();
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());

    expect(authFetch).toHaveBeenCalledTimes(1);
    const [url, opts] = authFetch.mock.calls[0];
    expect(url).toBe('/api/dual-translation/cards/101/review');
    expect(url).not.toContain('practice');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body).rating).toBe(3);
    expect(onDone.mock.calls[0][0]).toMatchObject({
      card_id: 101,
      rating: 3,
      saved: true,
      next_due: '2026-08-25',
    });
  });

  it('uses card_id, not the synthetic practice item id', async () => {
    // cards.py::_to_practice_item emits id "dt-error-101" alongside card_id 101.
    const practiceItem = { ...CLOZE, id: 'dt-error-101', is_error_exercise: true };
    const authFetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    const onDone = vi.fn();

    D().mount(el, practiceItem, { authFetch, onDone });
    el.querySelector('[data-dtec-check]').click();
    el.querySelector('[data-dtec-rating="4"]').click();
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());

    expect(authFetch.mock.calls[0][0]).toBe('/api/dual-translation/cards/101/review');
    expect(authFetch.mock.calls[0][0]).not.toContain('dt-error');
  });
});

// ---------------------------------------------------------------------------
// was_correct policy
// ---------------------------------------------------------------------------

describe('was_correct', () => {
  it('is an objective match for cloze cards', () => {
    expect(D().wasCorrectFor(CLOZE, 'the cat')).toBe(true);
    expect(D().wasCorrectFor(CLOZE, 'a cat')).toBe(false);
  });

  it('tolerates case, edge whitespace and edge punctuation', () => {
    expect(D().wasCorrectFor(CLOZE, '  The Cat.  ')).toBe(true);
    expect(D().wasCorrectFor(CLOZE, '"the cat"')).toBe(true);
  });

  it('is null for isolate_retranslate, deferring to the server default', () => {
    // Matching a whole back-translated sentence against a corrected fragment
    // would be meaningless, so we record nothing rather than a bad number.
    expect(D().wasCorrectFor(ISOLATE, 'The cat sat on the mat.')).toBeNull();
  });

  it('sends was_correct for cloze but omits it for isolate', async () => {
    const authFetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });

    const doneCloze = vi.fn();
    D().mount(el, CLOZE, { authFetch, onDone: doneCloze });
    el.querySelector('#dtecInput').value = 'a cat';
    el.querySelector('[data-dtec-check]').click();
    el.querySelector('[data-dtec-rating="1"]').click();
    await vi.waitFor(() => expect(doneCloze).toHaveBeenCalled());
    expect(JSON.parse(authFetch.mock.calls[0][1].body)).toEqual({
      rating: 1,
      was_correct: false,
    });

    document.body.innerHTML = '<div id="host2"></div>';
    const el2 = document.getElementById('host2');
    const doneIso = vi.fn();
    D().mount(el2, ISOLATE, { authFetch, onDone: doneIso });
    el2.querySelector('[data-dtec-check]').click();
    el2.querySelector('[data-dtec-rating="3"]').click();
    await vi.waitFor(() => expect(doneIso).toHaveBeenCalled());
    expect(JSON.parse(authFetch.mock.calls[1][1].body)).toEqual({ rating: 3 });
  });
});

// ---------------------------------------------------------------------------
// Payload handling per card type
// ---------------------------------------------------------------------------

describe('payload rendering', () => {
  it('renders the cloze prompt with its blank intact', () => {
    const html = D().promptHTML(CLOZE);
    expect(html).toContain('The ____ sat on the mat.');
    expect(html).not.toContain('the cat');
  });

  it('renders the L1 context as the isolate prompt', () => {
    const html = D().promptHTML(ISOLATE);
    expect(html).toContain('El gato se sentó en la alfombra.');
    expect(html).not.toContain('The cat sat on the mat.');
  });

  it('reveals the full sentence only for isolate cards', () => {
    expect(D().revealHTML(ISOLATE, null)).toContain('The cat sat on the mat.');
    expect(D().revealHTML(CLOZE, null)).not.toContain('sat on the mat');
  });

  it('escapes payload text rather than injecting it as markup', () => {
    const nasty = {
      card_id: 9,
      card_type: 'cloze',
      subtype: 'x',
      prompt_payload: { prompt: '<img src=x onerror=alert(1)>', answer: '<b>bold</b>' },
    };
    expect(D().promptHTML(nasty)).not.toContain('<img');
    expect(D().revealHTML(nasty, null)).not.toContain('<b>bold</b>');
  });

  it('renders l1_context as the reference for a cloze card when present', () => {
    // Regression: a "word choice" cloze card blanked the L2 element but gave
    // no English/L1 reference, so the learner couldn't know what was meant.
    const clozeWithReference = {
      ...CLOZE,
      prompt_payload: { ...CLOZE.prompt_payload, l1_context: 'The dog sat on the mat.' },
    };
    const html = D().promptHTML(clozeWithReference);
    expect(html).toContain('The dog sat on the mat.');
    expect(html).toContain('The ____ sat on the mat.');
  });

  it('omits the reference block for a cloze card with no l1_context (older cards)', () => {
    const html = D().promptHTML(CLOZE);
    expect(html).not.toContain('Reference (in your language)');
  });

  it('falls back to the cloze shape for an unknown card_type without leaking the answer', () => {
    const unknown = { ...CLOZE, card_type: 'something_new' };
    const html = D().promptHTML(unknown);
    expect(html).toContain('The ____ sat on the mat.');
    expect(html).not.toContain('the cat');
  });

  it('renders all four FSRS ratings', () => {
    const html = D().ratingHTML();
    [1, 2, 3, 4].forEach((r) => expect(html).toContain(`data-dtec-rating="${r}"`));
  });
});

// ---------------------------------------------------------------------------
// Failure handling — the guard's negative case
// ---------------------------------------------------------------------------

describe('failed submission', () => {
  it('reports saved:false and toasts instead of silently dropping the review', async () => {
    const authFetch = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    const toast = vi.fn();
    window.showToast = toast;
    const onDone = vi.fn();

    D().mount(el, CLOZE, { authFetch, onDone });
    el.querySelector('[data-dtec-check]').click();
    el.querySelector('[data-dtec-rating="2"]').click();
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());

    expect(onDone.mock.calls[0][0].saved).toBe(false);
    expect(toast).toHaveBeenCalled();
  });

  it('survives a thrown fetch', async () => {
    const authFetch = vi.fn().mockRejectedValue(new Error('offline'));
    const onDone = vi.fn();

    D().mount(el, CLOZE, { authFetch, onDone });
    el.querySelector('[data-dtec-check]').click();
    el.querySelector('[data-dtec-rating="1"]').click();
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());

    expect(onDone.mock.calls[0][0].saved).toBe(false);
  });

  it('does not double-submit when a rating is clicked twice', async () => {
    let resolve;
    const authFetch = vi.fn().mockReturnValue(
      new Promise((r) => {
        resolve = r;
      })
    );
    const onDone = vi.fn();

    D().mount(el, CLOZE, { authFetch, onDone });
    el.querySelector('[data-dtec-check]').click();
    const btn = el.querySelector('[data-dtec-rating="3"]');
    btn.click();
    btn.click();
    resolve({ ok: true, json: async () => ({}) });
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());

    expect(authFetch).toHaveBeenCalledTimes(1);
  });

  it('does not fire onDone after destroy()', async () => {
    const authFetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    const onDone = vi.fn();

    const handle = D().mount(el, CLOZE, { authFetch, onDone });
    el.querySelector('[data-dtec-check]').click();
    el.querySelector('[data-dtec-rating="3"]').click();
    handle.destroy();
    await vi.waitFor(() => expect(authFetch).toHaveBeenCalled());

    expect(onDone).not.toHaveBeenCalled();
  });
});
