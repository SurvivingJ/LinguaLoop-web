/**
 * Shared Dual Translation error-card renderer (TASK-731).
 *
 * One renderer for the two remediation card types, used by all three surfaces
 * that can be handed an error card:
 *   1. static/js/session/players/dual_translation.js  (daily-session DT player)
 *   2. static/js/dual_translation.js                  (standalone DT page)
 *   3. static/js/session/players/practice.js          (Practice Engine, TASK-618)
 *
 * Exposed as a plain global (window.DTErrorCard) rather than an ES module for
 * the same reason ExRenderers is: the standalone page is a classic <script>
 * IIFE while the two session players are ES modules, and a global is the one
 * shape both can consume. Host pages load it with a <script> tag.
 *
 * Card payload shapes (built by services/dual_translation/cards.py):
 *   cloze                -> { prompt, answer, l1_context }
 *   isolate_retranslate  -> { l1_context, target_sentence, answer }
 *
 * `l1_context` on a cloze card is the L1 reference sentence for the blank --
 * without it a blanked L2 sentence under-determines the answer whenever more
 * than one plausible word fits the gap (word-choice errors chief among them).
 * It may be `""` on cards built before this field existed; render it only
 * when present so those older cards still degrade to the prompt alone.
 *
 * INVARIANT - the answer is ALWAYS prompt_payload.answer, which the backend
 * builds from `corrected_form`. `learner_form` is never present in the payload
 * at all (see the dt_card.prompt_payload column comment in
 * migrations/dt_cards.sql: "MUST NOT contain learner_form as the answer
 * target (pedagogically critical)"). Showing the learner's own error back to
 * them as the target would train the mistake. Do not derive the answer from
 * anything else here.
 *
 * Grading goes to POST /api/dual-translation/cards/<card_id>/review, NOT to
 * /api/practice/attempt - FSRS state for these cards lives on dt_card, and the
 * practice attempt table is sense-keyed while error cards are subtype-keyed.
 */
/* global LinguaI18n */
const DTErrorCard = (function () {
  'use strict';

  const CARD_TYPE_CLOZE = 'cloze';
  const CARD_TYPE_ISOLATE = 'isolate_retranslate';

  // FSRS grades, mirroring services/vocabulary/fsrs.py and the rating CHECK
  // constraint on dt_card_review.
  const RATING_AGAIN = 1;
  const RATING_HARD = 2;
  const RATING_GOOD = 3;
  const RATING_EASY = 4;

  function t(key, fallback) {
    if (typeof window !== 'undefined' && window.LinguaI18n && typeof LinguaI18n.t === 'function') {
      return LinguaI18n.t(key) || fallback || key;
    }
    return fallback || key;
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : s;
    return d.innerHTML;
  }

  /**
   * The answer target for a card. Always `prompt_payload.answer`.
   * Kept as a named function so the invariant has one place to be tested.
   */
  function answerOf(card) {
    const p = (card && card.prompt_payload) || {};
    return p.answer == null ? '' : String(p.answer);
  }

  function cardIdOf(card) {
    // GET /next and GET /cards/due both emit `card_id`; the Practice Engine
    // item (cards.py::_to_practice_item) carries `card_id` too, alongside a
    // synthetic string `id` ("dt-error-<n>") that is NOT the card id.
    return card && card.card_id;
  }

  function reviewUrl(cardId) {
    return '/api/dual-translation/cards/' + encodeURIComponent(cardId) + '/review';
  }

  // Quote/bracket characters stripped from the edges before comparing, Latin
  // and CJK alike. Built from code points so this file stays ASCII-safe.
  const LEAD_TRIM = new RegExp('^[\\s"\'“”‘’(（[【「『]+');
  const TAIL_TRIM = new RegExp('[\\s"\'“”‘’)）\\]】」』.,!?。，！？…]+$');

  /**
   * Loose equality for the objective correctness check: trim, case-fold, drop
   * surrounding punctuation and collapse inner whitespace. Deliberately mild -
   * it decides `was_correct` (the recurrence-reduction metric), never the FSRS
   * rating, which stays the learner's own judgement.
   */
  function normalizeAnswer(s) {
    return String(s == null ? '' : s)
      .trim()
      .toLowerCase()
      .replace(LEAD_TRIM, '')
      .replace(TAIL_TRIM, '')
      .replace(/\s+/g, ' ');
  }

  /**
   * `was_correct` for the review POST, or null to let the server default it
   * to `rating !== AGAIN`.
   *
   * Only cloze gets an objective value: its answer is a single atom the
   * learner types verbatim, so a normalized match really is delayed re-test
   * accuracy. An isolate_retranslate response is a whole sentence, and
   * matching it against the corrected fragment would be meaningless - there we
   * defer to the server's rating-derived default rather than record a number
   * we cannot stand behind.
   */
  function wasCorrectFor(card, typed) {
    if (!card || card.card_type !== CARD_TYPE_CLOZE) return null;
    return normalizeAnswer(typed) === normalizeAnswer(answerOf(card));
  }

  // --------------------------------------------------------------------
  // Markup
  // --------------------------------------------------------------------

  function promptHTML(card) {
    const p = (card && card.prompt_payload) || {};
    const subtype = card && card.subtype;
    const badge = subtype
      ? '<div class="dtec-subtype small text-muted mb-2">' +
        esc(t('dt_card.subtype_label', 'Focus')) +
        ': ' +
        esc(String(subtype).replace(/_/g, ' ')) +
        '</div>'
      : '';

    if (card && card.card_type === CARD_TYPE_ISOLATE) {
      return (
        badge +
        '<p class="dtec-instructions text-muted small mb-3">' +
        esc(
          t('dt_card.isolate_instructions', 'Translate this into the language you are studying.')
        ) +
        '</p>' +
        '<div class="dtec-label small fw-semibold mb-1">' +
        esc(t('dt_card.reference_label', 'Reference (in your language)')) +
        '</div>' +
        '<blockquote class="dtec-prompt border-start border-3 ps-3 mb-3">' +
        esc(p.l1_context || '') +
        '</blockquote>'
      );
    }

    // cloze (also the fallback for an unknown card_type: showing the prompt
    // with the blank is the safe degradation, and never leaks the answer).
    // The L1 reference is what makes the blank solvable rather than a guess
    // (e.g. a word-choice error usually has more than one word that fits the
    // blank's shape) -- shown only when present, for older cards built before
    // this field existed.
    const referenceHTML = p.l1_context
      ? '<div class="dtec-label small fw-semibold mb-1">' +
        esc(t('dt_card.reference_label', 'Reference (in your language)')) +
        '</div>' +
        '<blockquote class="dtec-prompt border-start border-3 ps-3 mb-3">' +
        esc(p.l1_context) +
        '</blockquote>'
      : '';
    return (
      badge +
      '<p class="dtec-instructions text-muted small mb-3">' +
      esc(t('dt_card.cloze_instructions', 'Fill in the missing part.')) +
      '</p>' +
      referenceHTML +
      '<blockquote class="dtec-prompt border-start border-3 ps-3 mb-3">' +
      esc(p.prompt || '') +
      '</blockquote>'
    );
  }

  function revealHTML(card, verdict) {
    const p = (card && card.prompt_payload) || {};
    let html = '';

    if (verdict !== null && verdict !== undefined) {
      html +=
        '<div class="dtec-verdict alert ' +
        (verdict ? 'alert-success' : 'alert-danger') +
        ' py-2">' +
        esc(verdict ? t('dt_card.correct', 'Correct') : t('dt_card.incorrect', 'Not quite')) +
        '</div>';
    }

    html +=
      '<div class="dtec-label small fw-semibold mb-1">' +
      esc(t('dt_card.answer_label', 'Answer')) +
      '</div>' +
      '<p class="dtec-answer fs-5 mb-3">' +
      esc(answerOf(card)) +
      '</p>';

    if (card && card.card_type === CARD_TYPE_ISOLATE && p.target_sentence) {
      html +=
        '<div class="dtec-label small fw-semibold mb-1">' +
        esc(t('dt_card.full_sentence_label', 'Full sentence')) +
        '</div>' +
        '<blockquote class="dtec-target border-start border-3 ps-3 mb-3">' +
        esc(p.target_sentence) +
        '</blockquote>';
    }
    return html;
  }

  function ratingHTML() {
    const buttons = [
      [RATING_AGAIN, 'dt_card.rating_again', 'Again', 'btn-outline-danger'],
      [RATING_HARD, 'dt_card.rating_hard', 'Hard', 'btn-outline-warning'],
      [RATING_GOOD, 'dt_card.rating_good', 'Good', 'btn-outline-primary'],
      [RATING_EASY, 'dt_card.rating_easy', 'Easy', 'btn-outline-success'],
    ]
      .map(
        (row) =>
          '<button type="button" class="btn ' +
          row[3] +
          '" data-dtec-rating="' +
          row[0] +
          '">' +
          esc(t(row[1], row[2])) +
          '</button>'
      )
      .join('');

    return (
      '<div class="dtec-rate">' +
      '<div class="dtec-label small fw-semibold mb-2">' +
      esc(t('dt_card.rate_prompt', 'How well did you know it?')) +
      '</div>' +
      '<div class="d-flex gap-2 flex-wrap">' +
      buttons +
      '</div></div>'
    );
  }

  // --------------------------------------------------------------------
  // Mount
  // --------------------------------------------------------------------

  /**
   * Render an interactive error card into `el`.
   *
   * @param {HTMLElement} el   container (innerHTML is replaced)
   * @param {object} card      {card_id, card_type, subtype, prompt_payload, ...}
   * @param {object} [opts]
   *   onDone(result)  called after a rating is submitted (or after a failed
   *                   submit the learner chose to move past). `result` is
   *                   {card_id, rating, was_correct, saved, next_due}.
   *   authFetch       injectable fetch (defaults to window.authFetch)
   * @returns {{destroy: function}}
   */
  function mount(el, card, opts) {
    const options = opts || {};
    const doFetch = options.authFetch || (typeof window !== 'undefined' && window.authFetch);
    const state = { destroyed: false, submitting: false, typed: '' };

    renderPrompt();

    return {
      destroy() {
        state.destroyed = true;
      },
    };

    function renderPrompt() {
      el.innerHTML =
        '<div class="dtec">' +
        '<h2 class="h5 mb-2">' +
        esc(t('dt_card.heading', 'Review card')) +
        '</h2>' +
        promptHTML(card) +
        '<label class="form-label" for="dtecInput">' +
        esc(t('dt_card.your_answer_label', 'Your answer')) +
        '</label>' +
        '<textarea id="dtecInput" class="form-control mb-3" rows="3"></textarea>' +
        '<button class="btn btn-primary" type="button" data-dtec-check>' +
        esc(t('dt_card.check', 'Show answer')) +
        '</button>' +
        '</div>';
      el.querySelector('[data-dtec-check]').onclick = reveal;
    }

    function reveal() {
      if (state.destroyed) return;
      const input = el.querySelector('#dtecInput');
      state.typed = (input && input.value) || '';
      const verdict = wasCorrectFor(card, state.typed);

      el.innerHTML =
        '<div class="dtec">' +
        '<h2 class="h5 mb-2">' +
        esc(t('dt_card.heading', 'Review card')) +
        '</h2>' +
        promptHTML(card) +
        revealHTML(card, verdict) +
        ratingHTML() +
        '</div>';

      el.querySelectorAll('[data-dtec-rating]').forEach(function (btn) {
        btn.onclick = function () {
          grade(parseInt(btn.getAttribute('data-dtec-rating'), 10));
        };
      });
    }

    async function grade(rating) {
      if (state.destroyed || state.submitting) return;
      state.submitting = true;
      el.querySelectorAll('[data-dtec-rating]').forEach(function (b) {
        b.disabled = true;
      });

      const wasCorrect = wasCorrectFor(card, state.typed);
      const body = { rating: rating };
      if (wasCorrect !== null) body.was_correct = wasCorrect;

      let saved = false;
      let nextDue = null;
      try {
        const res = await doFetch(reviewUrl(cardIdOf(card)), {
          method: 'POST',
          body: JSON.stringify(body),
        });
        if (res && res.ok) {
          const payload = await res.json();
          const data = (payload && payload.data) || payload || {};
          nextDue = data.next_due || null;
          saved = true;
        }
      } catch (e) {
        console.error('dt-error-card: review submit failed', e);
      }

      if (!saved && typeof window !== 'undefined' && typeof window.showToast === 'function') {
        window.showToast(
          t('dt_card.save_failed', 'Could not save your review - check your connection.')
        );
      }

      state.submitting = false;
      if (state.destroyed) return;
      if (options.onDone) {
        options.onDone({
          card_id: cardIdOf(card),
          rating: rating,
          was_correct: wasCorrect,
          saved: saved,
          next_due: nextDue,
        });
      }
    }
  }

  return {
    CARD_TYPE_CLOZE,
    CARD_TYPE_ISOLATE,
    RATING_AGAIN,
    RATING_HARD,
    RATING_GOOD,
    RATING_EASY,
    answerOf,
    cardIdOf,
    reviewUrl,
    normalizeAnswer,
    wasCorrectFor,
    promptHTML,
    revealHTML,
    ratingHTML,
    mount,
  };
})();

// Assigned for the same reason ExRenderers is: host pages load this with a
// plain <script> tag, and tests/unit/setup.js evals it into happy-dom.
window.DTErrorCard = DTErrorCard;
